"""Local browser workbench for AquaSolar project inputs and PVT runs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import threading
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StrictBool
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from aquasolar.design import DesignInputs, run_design_screening
from aquasolar.pvt.runner import load_pvt_parameters, load_pvt_weather
from aquasolar.pvt.trace import calculation_trace
from aquasolar.module_registry import load_module_registry, module_is_enabled
from aquasolar.validation import validate_project


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
_SCENARIO_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
_WEATHER_STEM_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,99}")
_MEBIBYTE = int("1024") * int("1024")
_MAX_UPLOAD_BYTES = int("8") * _MEBIBYTE
_SAMPLE_PREVIEW_LIMIT = int("5")
_METRIC_COLUMNS = (
    "Metric ID",
    "Name",
    "Definition",
    "Numerator",
    "Denominator",
    "Time Basis",
    "Unit Kind",
    "Scenarios",
    "Status",
)
_EDITABLE_PARAMETER_FIELDS = {
    "value",
    "unit",
    "status",
    "source_type",
    "source_ref",
    "uncertainty.kind",
    "uncertainty.value",
    "uncertainty.distribution",
    "valid_range.min",
    "valid_range.max",
    "entered_by",
    "entered_on",
    "notes",
}
_PVT_OUTPUT_COLUMNS = (
    "POA_W_m2",
    "GHI_W_m2",
    "T_ambient_K",
    "T_f_out_K",
    "T_cell_K",
    "P_el_W",
    "Q_u_W",
    "E_el_Wh",
    "E_heat_Wh",
)


class ValidationRequest(BaseModel):
    parameter_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    file_overrides: dict[str, str] = Field(default_factory=dict)
    module_overrides: dict[str, StrictBool] = Field(default_factory=dict)


class ApplyRequest(ValidationRequest):
    confirmed: bool = False
    preview_token: str | None = None


class RunRequest(BaseModel):
    scenario_id: str
    weather: str


class DesignRequest(BaseModel):
    weather: str
    changes: dict[str, Any] = Field(default_factory=dict)


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def _relative_key(path: Path) -> str:
    return path.as_posix()


def _parameter_files(root: Path) -> dict[str, Path]:
    index = _read_yaml(root / "inputs" / "input_index.yaml") or {}
    return {
        row["id"]: Path("inputs/parameters") / f"{row['file']}.yaml"
        for row in index.get("parameters", [])
        if isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and isinstance(row.get("file"), str)
    }


def _allowed_data_files(root: Path) -> set[str]:
    allowed: set[str] = set()
    for folder in ("tables", "timeseries"):
        for meta_path in (root / "inputs" / folder).glob("*.meta.yaml"):
            relative_meta = meta_path.relative_to(root)
            csv_name = meta_path.name.removesuffix(".meta.yaml") + ".csv"
            allowed.add(_relative_key(relative_meta))
            allowed.add(_relative_key(relative_meta.with_name(csv_name)))
    return allowed


def _catalog(root: Path) -> dict[str, Any]:
    index = _read_yaml(root / "inputs" / "input_index.yaml") or {}
    definitions = {row["id"]: row for row in index.get("parameters", [])}
    parameters = []
    catalog_errors = []
    for path in sorted((root / "inputs" / "parameters").glob("*.yaml")):
        try:
            data = _read_yaml(path) or {}
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            catalog_errors.append(
                {"file": path.relative_to(root).as_posix(), "error": str(exc)}
            )
            continue
        group = data.get("title", path.stem)
        for parameter in data.get("parameters", []):
            definition = definitions.get(parameter.get("id"), {})
            parameters.append(
                {
                    **parameter,
                    "file": _relative_key(path.relative_to(root)),
                    "group": group,
                    "phase": definition.get("phase", parameter.get("needed_by_phase")),
                    "required_when": definition.get(
                        "required_when", parameter.get("required_when", "always")
                    ),
                    "allowed": parameter.get(
                        "allowed_values", definition.get("allowed")
                    ),
                    "kind": definition.get("kind"),
                }
            )

    data_files = []
    for folder in ("tables", "timeseries"):
        directory = root / "inputs" / folder
        for meta_path in sorted(directory.glob("*.meta.yaml")):
            relative_meta = meta_path.relative_to(root)
            csv_path = meta_path.with_name(
                meta_path.name.removesuffix(".meta.yaml") + ".csv"
            )
            try:
                meta = _read_yaml(meta_path) or {}
                metadata_error = None
            except (OSError, UnicodeError, yaml.YAMLError) as exc:
                meta = {}
                metadata_error = str(exc)
            try:
                with csv_path.open(encoding="utf-8", newline="") as stream:
                    reader = csv.DictReader(stream)
                    sample_rows = []
                    row_count = 0
                    for row in reader:
                        if len(sample_rows) < _SAMPLE_PREVIEW_LIMIT:
                            sample_rows.append(row)
                        row_count += 1
                csv_error = None
            except FileNotFoundError:
                row_count = 0
                sample_rows = []
                csv_error = "CSV file is missing"
            except (OSError, UnicodeError, csv.Error) as exc:
                row_count = 0
                sample_rows = []
                csv_error = str(exc)
            data_files.append(
                {
                    "kind": folder,
                    "file": _relative_key(csv_path.relative_to(root)),
                    "metadata_file": _relative_key(relative_meta),
                    "description": meta.get("description", ""),
                    "rows": row_count,
                    "sample_rows": sample_rows,
                    "columns": meta.get("columns", []),
                    "csv_error": csv_error,
                    "metadata_error": metadata_error,
                }
            )

    metrics_path = root / "docs" / "metric_definitions.md"
    metrics = []
    if metrics_path.exists():
        for line in metrics_path.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            fields = dict(zip(_METRIC_COLUMNS, cells))
            if len(cells) == len(_METRIC_COLUMNS) and re.fullmatch(
                r"M-[A-Z]+-\d+", fields.get("Metric ID", "")
            ):
                metrics.append(
                    {
                        "id": fields["Metric ID"],
                        "name": fields["Name"],
                        "description": fields["Definition"],
                        "unit": fields["Unit Kind"],
                        "file": "docs/metric_definitions.md",
                    }
                )
    outputs = [
        {
            "id": name,
            "name": name.replace("_", " "),
            "description": f"Saved PVT output column ({unit})",
            "unit": unit,
            "file": "src/aquasolar/pvt/runner.py",
        }
        for name, unit in (
            ("P_el_W", "W"),
            ("Q_u_W", "W"),
            ("T_f_out_K", "K"),
            ("T_cell_K", "K"),
            ("POA_W_m2", "W/m2"),
            ("E_el_Wh", "Wh"),
            ("E_heat_Wh", "Wh"),
        )
    ]
    return {
        "parameters": parameters,
        "data_files": data_files,
        "metrics": metrics,
        "outputs": outputs,
        "catalog_errors": catalog_errors,
    }


def _set_nested(entry: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    current = entry
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _parameter_yaml_overrides(
    root: Path, changes: dict[str, dict[str, Any]]
) -> dict[str, str]:
    file_by_id = _parameter_files(root)
    by_file: dict[str, dict[str, dict[str, Any]]] = {}
    for parameter_id, updates in changes.items():
        relative = file_by_id.get(parameter_id)
        if relative is None:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Unknown parameter id: {parameter_id}",
            )
        unknown = set(updates) - _EDITABLE_PARAMETER_FIELDS
        if unknown:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Unsupported fields for {parameter_id}: {', '.join(sorted(unknown))}",
            )
        by_file.setdefault(relative.as_posix(), {})[parameter_id] = updates

    replacements: dict[str, str] = {}
    round_trip = YAML()
    round_trip.preserve_quotes = True
    for relative, file_changes in by_file.items():
        path = root / Path(relative)
        try:
            with path.open(encoding="utf-8") as stream:
                data = round_trip.load(stream)
        except (OSError, YAMLError, TypeError, AttributeError) as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Could not read parameter file {relative}: {exc}",
            ) from exc
        if not isinstance(data, dict) or not isinstance(data.get("parameters"), list):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Parameter file {relative} must contain a parameters list.",
            )
        rows = data["parameters"]
        found: set[str] = set()
        for entry in rows:
            if not isinstance(entry, dict):
                raise HTTPException(
                    status_code=HTTPStatus.BAD_REQUEST,
                    detail=f"Parameter file {relative} contains a malformed entry.",
                )
            parameter_id = entry.get("id")
            if parameter_id not in file_changes:
                continue
            found.add(parameter_id)
            for key, value in file_changes[parameter_id].items():
                _set_nested(entry, key, value)
        missing = set(file_changes) - found
        if missing:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Parameter entries missing from {relative}: {', '.join(sorted(missing))}",
            )
        output = io.StringIO()
        round_trip.dump(data, output)
        replacements[relative] = output.getvalue()
    return replacements


def _module_yaml_overrides(
    root: Path, changes: dict[str, bool]
) -> dict[str, str]:
    if not changes:
        return {}
    try:
        modules = load_module_registry(root)
    except ValueError as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    by_id = {module["id"]: module for module in modules}
    unknown = set(changes) - set(by_id)
    if unknown:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Unknown module IDs: {', '.join(sorted(unknown))}",
        )
    relative = Path("inputs/module_registry.yaml")
    round_trip = YAML()
    round_trip.preserve_quotes = True
    try:
        with (root / relative).open(encoding="utf-8") as stream:
            data = round_trip.load(stream)
    except (OSError, YAMLError) as exc:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Could not load module registry: {exc}",
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("modules"), list):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Module registry must contain a modules list.",
        )
    for module in data["modules"]:
        if isinstance(module, dict) and module.get("id") in changes:
            module["enabled"] = changes[module["id"]]
    output = io.StringIO()
    round_trip.dump(data, output)
    return {_relative_key(relative): output.getvalue()}


def _check_file_overrides(root: Path, files: dict[str, str]) -> set[str]:
    allowed = _allowed_data_files(root)
    if any(not isinstance(contents, str) for contents in files.values()):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="File contents must be UTF-8 text.",
        )
    total = sum(len(contents.encode("utf-8")) for contents in files.values())
    if total > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            detail=f"Staged data exceeds the {_MAX_UPLOAD_BYTES // _MEBIBYTE} MiB limit.",
        )
    new_weather_files: set[str] = set()
    new_weather_stems: set[str] = set()
    for relative, contents in files.items():
        candidate = Path(relative)
        normalized = candidate.as_posix()
        if candidate.is_absolute() or ".." in candidate.parts:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"File path is outside the input directories: {relative}",
            )
        if normalized in allowed:
            continue
        is_csv = candidate.suffix == ".csv"
        is_metadata = candidate.name.endswith(".meta.yaml")
        if (
            candidate.parts[:2] != ("inputs", "timeseries")
            or len(candidate.parts) != int("3")
            or not (is_csv or is_metadata)
        ):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"File is not a registered input or new weather file: {relative}",
            )
        stem = (
            candidate.stem
            if is_csv
            else candidate.name.removesuffix(".meta.yaml")
        )
        if not _WEATHER_STEM_PATTERN.fullmatch(stem):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=f"Weather filename must use letters, digits, dot, underscore, or hyphen: {relative}",
            )
        csv_relative = f"inputs/timeseries/{stem}.csv"
        metadata_relative = f"inputs/timeseries/{stem}.meta.yaml"
        if (
            (root / csv_relative).exists()
            or (root / metadata_relative).exists()
        ):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail=f"Weather dataset already exists; choose a unique filename: {stem}",
            )
        new_weather_stems.add(stem)
        new_weather_files.add(normalized)
    if new_weather_files:
        expected_paths = {
            path
            for stem in new_weather_stems
            for path in (
                f"inputs/timeseries/{stem}.csv",
                f"inputs/timeseries/{stem}.meta.yaml",
            )
        }
        if new_weather_files != expected_paths:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Add a new weather dataset as a matching CSV and .meta.yaml pair.",
            )
    return new_weather_files


def _atomic_write_set(
    root: Path,
    replacements: dict[str, str],
    create_only: set[str] | None = None,
) -> None:
    originals: dict[Path, bytes | None] = {}
    temporary: dict[Path, Path] = {}
    committed: list[Path] = []
    create_only = create_only or set()
    try:
        for relative, contents in replacements.items():
            target = (root / Path(relative)).resolve()
            if not target.is_relative_to(root):
                raise ValueError(f"Refusing to write outside project root: {relative}")
            if relative in create_only and target.exists():
                raise FileExistsError(f"Refusing to overwrite new weather input: {relative}")
            originals[target] = target.read_bytes() if target.exists() else None
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as stream:
                stream.write(contents)
                temporary[target] = Path(stream.name)
        for target, temp_path in temporary.items():
            os.replace(temp_path, target)
            committed.append(target)
    except (OSError, ValueError) as exc:
        restore_errors = []
        for target in reversed(committed):
            original = originals[target]
            try:
                if original is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(original)
            except OSError as restore_exc:
                restore_errors.append(f"{target}: {restore_exc}")
        details = f"Could not apply staged input files: {exc}"
        if restore_errors:
            details += "; rollback errors: " + "; ".join(restore_errors)
        raise RuntimeError(details) from exc
    finally:
        for temp_path in temporary.values():
            temp_path.unlink(missing_ok=True)


def _pvt_preflight(root: Path, weather: str) -> dict[str, Any]:
    issues = []
    try:
        if not module_is_enabled(root, "pvt_runner"):
            issues.append(
                {
                    "severity": "error",
                    "code": "module.pvt_runner.disabled",
                    "file": "inputs/module_registry.yaml",
                    "location": "pvt_runner",
                    "message": "Enable the operational PVT module before starting this run.",
                }
            )
    except ValueError as exc:
        issues.append(
            {
                "severity": "error",
                "code": "module.registry.invalid",
                "file": "inputs/module_registry.yaml",
                "location": "modules",
                "message": str(exc),
            }
        )
    try:
        load_pvt_parameters(root / "inputs" / "parameters")
    except (OSError, ImportError, TypeError, ValueError, RuntimeError) as exc:
        issues.append(
            {
                "severity": "error",
                "code": "pvt.parameters.not_ready",
                "file": "inputs/parameters/",
                "location": "PVT run inputs",
                "message": str(exc),
            }
        )
    relative = Path(weather)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.parts[:2] != ("inputs", "timeseries")
    ):
        issues.append(
            {
                "severity": "error",
                "code": "pvt.weather.path_invalid",
                "file": weather,
                "location": "",
                "message": "Select a weather file inside inputs/timeseries.",
            }
        )
    else:
        try:
            load_pvt_weather(root / relative)
        except (OSError, ValueError) as exc:
            issues.append(
                {
                    "severity": "error",
                    "code": "pvt.weather.not_ready",
                    "file": relative.as_posix(),
                    "location": "",
                    "message": str(exc),
                }
            )
        meta = relative.with_name(relative.stem + ".meta.yaml")
        input_report = validate_project(root)
        for issue in input_report.issues:
            if (
                issue.severity == "error"
                and issue.file in {relative.as_posix(), meta.as_posix()}
            ):
                issues.append(
                    {
                        "severity": issue.severity,
                        "code": issue.code,
                        "file": issue.file,
                        "location": issue.location,
                        "message": issue.message,
                    }
                )
    return {"ok": not issues, "issues": issues}


def _output_runs(root: Path) -> list[dict[str, Any]]:
    result_dir = root / "outputs" / "pvt_only"
    summaries = (
        sorted(
            result_dir.glob("*.summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if result_dir.exists()
        else []
    )
    runs = []
    for summary_path in summaries:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            runs.append(
                {
                    "scenario_id": summary_path.name.removesuffix(".summary.json"),
                    "file": summary_path.relative_to(root).as_posix(),
                    "valid": False,
                    "validation_error": str(exc),
                }
            )
            continue
        scenario_id = summary.get("scenario_id")
        csv_path = result_dir / f"{scenario_id}.csv" if scenario_id else None
        validation = _validate_result_csv(csv_path) if csv_path else {
            "valid": False,
            "validation_error": "summary has no scenario_id",
            "rows": 0,
        }
        runs.append(
            {
                **summary,
                "file": summary_path.relative_to(root).as_posix(),
                "valid": validation["valid"],
                "validation_error": validation.get("validation_error"),
                "rows": validation["rows"],
            }
        )
    return runs


def _validate_result_csv(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "valid": False,
            "validation_error": "result CSV is missing",
            "rows": 0,
        }
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            missing = set(_PVT_OUTPUT_COLUMNS) - set(reader.fieldnames or [])
            if missing:
                return {
                    "valid": False,
                    "validation_error": "missing result columns: "
                    + ", ".join(sorted(missing)),
                    "rows": 0,
                }
            count = 0
            previous = None
            for line_number, row in enumerate(reader, start=2):
                timestamp = datetime.fromisoformat(row["timestamp"])
                if timestamp.utcoffset() is None:
                    raise ValueError(f"line {line_number}: timestamp has no UTC offset")
                if previous is not None and timestamp <= previous:
                    raise ValueError(
                        f"line {line_number}: timestamps are not increasing"
                    )
                previous = timestamp
                for column in _PVT_OUTPUT_COLUMNS:
                    value = float(row[column])
                    if not math.isfinite(value):
                        raise ValueError(f"line {line_number}: {column} is not finite")
                count += 1
            return {"valid": count > 0, "validation_error": None, "rows": count}
    except (OSError, UnicodeError, csv.Error, TypeError, ValueError) as exc:
        return {"valid": False, "validation_error": str(exc), "rows": 0}


def _run_worker(
    root: Path,
    job_id: str,
    scenario_id: str,
    weather: str,
    jobs: dict[str, dict[str, Any]],
    lock: threading.Lock,
) -> None:
    command = [
        sys.executable,
        "-m",
        "aquasolar",
        "run",
        scenario_id,
        "--weather",
        weather,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(root / "src")},
            check=False,
        )
        with lock:
            jobs[job_id].update(
                {
                    "state": "completed" if completed.returncode == 0 else "failed",
                    "returncode": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            )
    except OSError as exc:
        with lock:
            jobs[job_id].update(
                {"state": "failed", "returncode": None, "stderr": str(exc)}
            )


def create_app(
    project_root: Path = PROJECT_ROOT, *, read_only: bool | None = None
) -> FastAPI:
    """Create the browser app; ``project_root`` is injectable for tests."""
    root = project_root.resolve()
    is_read_only = read_only
    if is_read_only is None:
        is_read_only = os.environ.get("AQUASOLAR_READ_ONLY", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aquasolar-run")
    jobs: dict[str, dict[str, Any]] = {}
    jobs_lock = threading.Lock()
    preview_state: tuple[str, str, frozenset[str]] | None = None
    preview_state_lock = threading.Lock()

    def override_digest(payload: ValidationRequest) -> str:
        normalized = json.dumps(
            {
                "parameter_overrides": payload.parameter_overrides,
                "file_overrides": payload.file_overrides,
                "module_overrides": payload.module_overrides,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        executor.shutdown(wait=False)

    app = FastAPI(
        title="AquaSolar Input Workbench",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def verify_browser_origin(request, call_next):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if is_read_only:
                return JSONResponse(
                    status_code=HTTPStatus.FORBIDDEN,
                    content={
                        "detail": "This public showcase is read-only; edits and runs are disabled."
                    },
                )
            origin = request.headers.get("origin")
            if origin:
                if urlparse(origin).hostname not in {
                    "localhost",
                    "127.0.0.1",
                    "::1",
                    "testserver",
                }:
                    return JSONResponse(
                        status_code=HTTPStatus.FORBIDDEN,
                        content={"detail": "Only local browser requests are allowed."},
                    )
        return await call_next(request)

    @app.get("/api/config")
    def get_config() -> dict[str, bool]:
        return {"read_only": is_read_only}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/catalog")
    def get_catalog() -> dict[str, Any]:
        try:
            return _catalog(root)
        except (OSError, yaml.YAMLError, KeyError, TypeError) as exc:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=f"Could not load project catalog: {exc}",
            ) from exc

    @app.get("/api/validation")
    def get_validation() -> dict[str, Any]:
        return validate_project(root).to_dict()

    @app.get("/api/model/trace")
    def get_model_trace() -> dict[str, Any]:
        return calculation_trace()

    @app.get("/api/modules")
    def get_modules() -> list[dict[str, Any]]:
        try:
            modules = load_module_registry(root)
            report = validate_project(root)
        except (OSError, ValueError) as exc:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=f"Could not load module readiness: {exc}",
            ) from exc
        parameter_issues = [issue for issue in report.issues]
        weather_paths = sorted((root / "inputs" / "timeseries").glob("*.csv"))
        usable_weather = None
        for path in weather_paths:
            try:
                load_pvt_weather(path)
                usable_weather = path.relative_to(root).as_posix()
                break
            except (OSError, ValueError):
                continue
        selected_weather = usable_weather or (
            weather_paths[0].relative_to(root).as_posix()
            if weather_paths
            else "inputs/timeseries/weather.csv"
        )
        response = []
        for module in modules:
            parameter_paths = {
                f"inputs/parameters/{filename}.yaml"
                for filename in module.get("parameter_files", [])
            }
            if module["id"] == "pvt_runner":
                issues = _pvt_preflight(root, selected_weather)["issues"]
            else:
                issues = [
                    asdict(issue)
                    for issue in parameter_issues
                    if issue.file in parameter_paths
                    and (
                        not module.get("parameter_ids")
                        or issue.location in module["parameter_ids"]
                    )
                ]
            has_errors = any(issue["severity"] == "error" for issue in issues)
            response.append(
                {
                    **module,
                    "readiness": (
                        ("requirements_missing" if has_errors else "ready")
                        if module["operational_status"] == "operational"
                        else "not_operational"
                    ),
                    "requirements_complete": not has_errors,
                    "issues": issues,
                }
            )
        return response

    @app.get("/api/reference")
    def get_reference() -> FileResponse:
        path = root / "coolpv_technical_data_sheet.md"
        if not path.is_file():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Corrected collector reference is missing.",
            )
        return FileResponse(path, media_type="text/markdown")

    @app.post("/api/validation/preview")
    def preview_validation(payload: ValidationRequest) -> dict[str, Any]:
        nonlocal preview_state
        new_weather_files = _check_file_overrides(root, payload.file_overrides)
        _parameter_yaml_overrides(root, payload.parameter_overrides)
        _module_yaml_overrides(root, payload.module_overrides)
        report = validate_project(
            root,
            parameter_overrides=payload.parameter_overrides,
            file_overrides=payload.file_overrides,
        )
        token = uuid.uuid4().hex
        with preview_state_lock:
            preview_state = (
                token,
                override_digest(payload),
                frozenset(new_weather_files),
            )
        return {**report.to_dict(), "preview_token": token}

    @app.post("/api/validation/apply")
    def apply_validation(payload: ApplyRequest) -> dict[str, Any]:
        nonlocal preview_state
        if not payload.confirmed:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Explicit confirmation is required before writing files.",
            )
        new_weather_files = _check_file_overrides(root, payload.file_overrides)
        parameter_files = _parameter_yaml_overrides(
            root, payload.parameter_overrides
        )
        module_files = _module_yaml_overrides(root, payload.module_overrides)
        preview = validate_project(
            root,
            parameter_overrides=payload.parameter_overrides,
            file_overrides=payload.file_overrides,
        )
        invalid_new_weather_issues = [
            issue
            for issue in preview.issues
            if issue.severity == "error" and issue.file in new_weather_files
        ]
        if invalid_new_weather_issues:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Correct validation errors in the new weather pair before applying it.",
                    "issues": [asdict(issue) for issue in invalid_new_weather_issues],
                },
            )
        with preview_state_lock:
            if (
                preview_state is None
                or payload.preview_token != preview_state[0]
                or override_digest(payload) != preview_state[1]
                or frozenset(new_weather_files) != preview_state[2]
            ):
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="Preview these exact changes before applying them.",
                )
            preview_state = None
        replacements = {
            **parameter_files,
            **module_files,
            **payload.file_overrides,
        }
        try:
            _atomic_write_set(root, replacements, new_weather_files)
        except RuntimeError as exc:
            if isinstance(exc.__cause__, FileExistsError):
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="A weather file with that name was created after preview; choose another filename.",
                ) from exc
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(exc)
            ) from exc
        return validate_project(root).to_dict()

    @app.get("/api/weather")
    def list_weather() -> list[dict[str, Any]]:
        weather_paths = sorted((root / "inputs" / "timeseries").glob("*.csv"))
        result = []
        for path in weather_paths:
            relative = path.relative_to(root)
            try:
                rows, interval_seconds = load_pvt_weather(path)
                result.append(
                    {
                        "file": relative.as_posix(),
                        "valid": True,
                        "rows": len(rows),
                        "interval_seconds": interval_seconds,
                        "error": None,
                    }
                )
            except (OSError, ValueError) as exc:
                result.append(
                    {
                        "file": relative.as_posix(),
                        "valid": False,
                        "rows": 0,
                        "interval_seconds": None,
                        "error": str(exc),
                    }
                )
        return result

    @app.get("/api/run-readiness")
    def get_run_readiness(weather: str) -> dict[str, Any]:
        return _pvt_preflight(root, weather)

    @app.get("/api/design/defaults")
    def get_design_defaults() -> dict[str, Any]:
        payload = asdict(DesignInputs())
        return {
            "defaults": payload,
            "limitations": [
                "Screening calculator: not the validated transient model or TRNSYS cross-check.",
                "Tank is a single well-mixed node; RO contaminants and pipe losses are not modelled.",
                "Results are not design, safety, or potable-water evidence.",
            ],
        }

    @app.post("/api/design/simulate")
    def simulate_design(payload: DesignRequest) -> dict[str, Any]:
        weather_path = Path(payload.weather)
        if (
            weather_path.is_absolute()
            or ".." in weather_path.parts
            or weather_path.parts[:2] != ("inputs", "timeseries")
            or not (root / weather_path).is_file()
        ):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Choose a registered project weather CSV for design screening.",
            )
        try:
            result = run_design_screening(
                root,
                root / weather_path,
                payload.changes,
            )
        except (OSError, ImportError, TypeError, ValueError, RuntimeError) as exc:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail=str(exc)
            ) from exc
        return {
            "scope": "Interactive whole-system screening",
            "weather": weather_path.as_posix(),
            **asdict(result),
        }

    @app.get("/api/runs")
    def list_runs() -> list[dict[str, Any]]:
        return _output_runs(root)

    @app.get("/api/runs/{scenario_id}/series")
    def get_run_series(scenario_id: str) -> dict[str, Any]:
        if not _SCENARIO_PATTERN.fullmatch(scenario_id) or scenario_id in {".", ".."}:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST, detail="Invalid scenario id."
            )
        path = root / "outputs" / "pvt_only" / f"{scenario_id}.csv"
        if not path.is_file():
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail="Run result CSV was not found.",
            )
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
        return {"columns": reader.fieldnames or [], "rows": rows}

    @app.post("/api/runs")
    def start_run(payload: RunRequest) -> dict[str, Any]:
        scenario_id = payload.scenario_id.strip()
        if (
            not _SCENARIO_PATTERN.fullmatch(scenario_id)
            or scenario_id in {".", ".."}
        ):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Scenario ID may contain only letters, digits, dot, underscore, and hyphen.",
            )
        weather_path = Path(payload.weather)
        if (
            weather_path.is_absolute()
            or ".." in weather_path.parts
            or weather_path.parts[:2] != ("inputs", "timeseries")
            or not weather_path.is_file()
            or not (root / weather_path).resolve().is_relative_to(root)
        ):
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail="Choose a registered project weather CSV.",
            )
        readiness = _pvt_preflight(root, weather_path.as_posix())
        if not readiness["ok"]:
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail={
                    "message": "PVT run is blocked by preflight validation.",
                    "run_readiness": readiness,
                    "validation": validate_project(root).to_dict(),
                },
            )

        output_dir = root / "outputs" / "pvt_only"
        if (
            (output_dir / f"{scenario_id}.csv").exists()
            or (output_dir / f"{scenario_id}.summary.json").exists()
        ):
            raise HTTPException(
                status_code=HTTPStatus.CONFLICT,
                detail="Scenario ID already exists; choose a unique ID.",
            )
        with jobs_lock:
            if any(job["state"] == "running" for job in jobs.values()):
                raise HTTPException(
                    status_code=HTTPStatus.CONFLICT,
                    detail="A PVT scenario is already running.",
                )
            job_id = uuid.uuid4().hex
            jobs[job_id] = {
                "id": job_id,
                "scenario_id": scenario_id,
                "weather": weather_path.as_posix(),
                "state": "running",
            }
            executor.submit(
                _run_worker,
                root,
                job_id,
                scenario_id,
                weather_path.as_posix(),
                jobs,
                jobs_lock,
            )
        return dict(jobs[job_id])

    @app.get("/api/runs/jobs/{job_id}")
    def get_run_job(job_id: str) -> dict[str, Any]:
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None:
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail="Run job was not found."
                )
            return dict(job)

    return app


app = create_app()
