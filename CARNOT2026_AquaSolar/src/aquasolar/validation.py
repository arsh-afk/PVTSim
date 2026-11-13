"""Structured, non-mutating validation for AquaSolar project inputs."""

from __future__ import annotations

import csv
import io
import math
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import ValidationError

from aquasolar.registry.conditions import evaluate_required_when
from aquasolar.registry.schema import ParameterEntry


_NUMERIC_KINDS = {
    "activation_energy",
    "angle",
    "area",
    "area_thermal_resistance",
    "areal_heat_capacity",
    "concentration",
    "count",
    "currency",
    "currency_per_energy",
    "currency_per_time",
    "currency_per_volume",
    "density",
    "dimensionless",
    "emission_per_energy",
    "emission_per_volume",
    "energy",
    "energy_per_volume",
    "flow_mass",
    "flow_volumetric",
    "fraction",
    "heat_transfer_coefficient",
    "irradiance",
    "length",
    "loading_capacity",
    "mass",
    "permeability",
    "power",
    "pressure",
    "rate_per_temperature",
    "rate_per_time",
    "rate_per_volume",
    "specific_heat",
    "temperature",
    "temperature_difference",
    "thermal_conductance",
    "thermal_conductivity",
    "time",
    "uv_dose",
    "uv_intensity",
    "volume",
}


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    file: str
    location: str
    message: str
    expected: str = ""
    found: str = ""
    suggestion: str = ""


@dataclass(frozen=True)
class ValidationReport:
    issues: tuple[ValidationIssue, ...]

    @property
    def error_count(self) -> int:
        return sum(issue.severity == "error" for issue in self.issues)

    @property
    def warning_count(self) -> int:
        return sum(issue.severity == "warning" for issue in self.issues)

    @property
    def ok(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "issues": [asdict(issue) for issue in self.issues],
        }


def validate_project(
    root: Path,
    *,
    parameter_overrides: Mapping[str, Mapping[str, Any]] | None = None,
    file_overrides: Mapping[str, str] | None = None,
) -> ValidationReport:
    """Validate registered parameters and every metadata/CSV input pair.

    Overrides are in-memory only. Keys in ``file_overrides`` are project-relative
    paths and are read in place of disk files; this supports preview-before-save.
    """
    root = root.resolve()
    parameter_overrides = parameter_overrides or {}
    file_overrides = file_overrides or {}
    issues: list[ValidationIssue] = []
    index_path = Path("inputs/input_index.yaml")
    index = _load_yaml(root, index_path, file_overrides, issues)
    if not isinstance(index, dict):
        return ValidationReport(tuple(issues))

    definitions = index.get("parameters", [])
    if not isinstance(definitions, list):
        issues.append(
            _issue(
                "error",
                "parameters.index.invalid",
                index_path.as_posix(),
                "parameters",
                "The parameter index must contain a list.",
                "YAML list of parameter definitions",
                type(definitions).__name__,
            )
        )
        return ValidationReport(tuple(issues))

    entries, entry_files = _load_parameters(
        root, definitions, file_overrides, issues
    )
    for parameter_id, updates in parameter_overrides.items():
        if parameter_id not in entries:
            issues.append(
                _issue(
                    "error",
                    "parameter.override.unknown",
                    index_path.as_posix(),
                    parameter_id,
                    "Cannot preview an unregistered parameter.",
                    "registered parameter id",
                    parameter_id,
                )
            )
            continue
        merged = deepcopy(entries[parameter_id])
        merged.update(deepcopy(dict(updates)))
        entries[parameter_id] = merged

    _validate_parameters(definitions, entries, entry_files, issues)
    for kind in ("tables", "timeseries"):
        _validate_data_directory(root, kind, file_overrides, issues)
    return ValidationReport(tuple(issues))


def _issue(
    severity: str,
    code: str,
    file: str,
    location: str,
    message: str,
    expected: str = "",
    found: str = "",
    suggestion: str = "",
) -> ValidationIssue:
    return ValidationIssue(
        severity, code, file, location, message, expected, found, suggestion
    )


def _read_text(
    root: Path, relative_path: Path, file_overrides: Mapping[str, str]
) -> str:
    key = relative_path.as_posix()
    if key in file_overrides:
        return file_overrides[key]
    return (root / relative_path).read_text(encoding="utf-8")


def _load_yaml(
    root: Path,
    relative_path: Path,
    file_overrides: Mapping[str, str],
    issues: list[ValidationIssue],
) -> Any:
    try:
        return yaml.safe_load(_read_text(root, relative_path, file_overrides))
    except FileNotFoundError:
        issues.append(
            _issue(
                "error",
                "file.missing",
                relative_path.as_posix(),
                "",
                "Required project input file is missing.",
                "existing YAML file",
                "not found",
                "Restore the file or provide it through the input editor.",
            )
        )
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        issues.append(
            _issue(
                "error",
                "yaml.invalid",
                relative_path.as_posix(),
                "",
                "Could not read or parse YAML.",
                "valid UTF-8 YAML",
                str(exc),
                "Correct the YAML syntax and validate again.",
            )
        )
    return None


def _load_parameters(
    root: Path,
    definitions: list[Any],
    file_overrides: Mapping[str, str],
    issues: list[ValidationIssue],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    entries: dict[str, dict[str, Any]] = {}
    entry_files: dict[str, str] = {}
    file_ids: dict[str, list[dict[str, Any]]] = {}
    for definition in definitions:
        if not isinstance(definition, dict):
            issues.append(
                _issue(
                    "error",
                    "parameter.index.entry_invalid",
                    "inputs/input_index.yaml",
                    "parameters",
                    "Parameter definition must be a mapping.",
                    "mapping with id and file",
                    type(definition).__name__,
                )
            )
            continue
        parameter_id = definition.get("id")
        filename = definition.get("file")
        if not isinstance(parameter_id, str) or not parameter_id:
            issues.append(
                _issue(
                    "error",
                    "parameter.index.id_missing",
                    "inputs/input_index.yaml",
                    "parameters",
                    "Parameter definition is missing its id.",
                    "non-empty parameter id",
                    repr(parameter_id),
                )
            )
            continue
        if not isinstance(filename, str) or Path(filename).name != filename:
            issues.append(
                _issue(
                    "error",
                    "parameter.index.file_invalid",
                    "inputs/input_index.yaml",
                    parameter_id,
                    "Parameter definition has an invalid file name.",
                    "parameter YAML file stem",
                    repr(filename),
                )
            )
            continue
        file_ids.setdefault(filename, []).append(definition)

    for filename, file_definitions in file_ids.items():
        relative_path = Path("inputs/parameters") / f"{filename}.yaml"
        data = _load_yaml(root, relative_path, file_overrides, issues)
        if not isinstance(data, dict) or not isinstance(data.get("parameters"), list):
            if data is not None:
                issues.append(
                    _issue(
                        "error",
                        "parameter.file.shape",
                        relative_path.as_posix(),
                        "parameters",
                        "Parameter file must contain a parameters list.",
                        "mapping with parameters list",
                        type(data).__name__,
                    )
                )
            continue
        file_entries: dict[str, dict[str, Any]] = {}
        for row_number, entry in enumerate(data["parameters"], start=1):
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                issues.append(
                    _issue(
                        "error",
                        "parameter.entry.invalid",
                        relative_path.as_posix(),
                        f"parameters[{row_number}]",
                        "Parameter entry must be a mapping with an id.",
                        "mapping with string id",
                        repr(entry),
                    )
                )
                continue
            parameter_id = entry["id"]
            if parameter_id in file_entries:
                issues.append(
                    _issue(
                        "error",
                        "parameter.id.duplicate",
                        relative_path.as_posix(),
                        parameter_id,
                        "Parameter id is duplicated in this file.",
                        "unique id",
                        parameter_id,
                    )
                )
            file_entries[parameter_id] = entry

        known_ids = {row["id"] for row in file_definitions}
        for parameter_id in file_entries.keys() - known_ids:
            issues.append(
                _issue(
                    "warning",
                    "parameter.id.unregistered",
                    relative_path.as_posix(),
                    parameter_id,
                    "Parameter file contains an id absent from the master index.",
                    "registered parameter id",
                    parameter_id,
                    "Register the parameter or remove the stale entry.",
                )
            )
        for definition in file_definitions:
            parameter_id = definition["id"]
            if parameter_id in entries:
                issues.append(
                    _issue(
                        "error",
                        "parameter.id.duplicate",
                        relative_path.as_posix(),
                        parameter_id,
                        "Parameter id occurs in more than one parameter file.",
                        "one entry per id",
                        parameter_id,
                    )
                )
                continue
            if parameter_id not in file_entries:
                continue
            entry = file_entries[parameter_id]
            try:
                ParameterEntry.model_validate(entry)
            except ValidationError as exc:
                for error in exc.errors():
                    location = ".".join(str(part) for part in error["loc"])
                    issues.append(
                        _issue(
                            "error",
                            "parameter.schema.invalid",
                            relative_path.as_posix(),
                            f"{parameter_id}.{location}".rstrip("."),
                            error["msg"],
                            error["type"],
                            repr(entry.get(location)),
                        )
                    )
            entries[parameter_id] = entry
            entry_files[parameter_id] = relative_path.as_posix()
    return entries, entry_files


def _validate_parameters(
    definitions: list[Any],
    entries: dict[str, dict[str, Any]],
    entry_files: dict[str, str],
    issues: list[ValidationIssue],
) -> None:
    index_ids = {
        definition["id"]: definition
        for definition in definitions
        if isinstance(definition, dict) and isinstance(definition.get("id"), str)
    }
    active_values = {
        parameter_id: entry.get("value")
        for parameter_id, entry in entries.items()
        if entry.get("status") == "confirmed" and entry.get("value") is not None
    }
    required: dict[str, bool] = {}
    for parameter_id, definition in index_ids.items():
        expression = definition.get("required_when", "always")
        try:
            required[parameter_id] = evaluate_required_when(
                str(expression), active_values
            )
        except ValueError as exc:
            required[parameter_id] = False
            issues.append(
                _issue(
                    "error",
                    "parameter.requirement.invalid",
                    "inputs/input_index.yaml",
                    parameter_id,
                    "Could not evaluate the conditional requirement.",
                    "supported required_when expression",
                    str(expression),
                    str(exc),
                )
            )

    for parameter_id, definition in index_ids.items():
        entry = entries.get(parameter_id)
        is_required = required.get(parameter_id, False)
        filename = entry_files.get(
            parameter_id,
            f"inputs/parameters/{definition.get('file', 'unknown')}.yaml",
        )
        if entry is None:
            if is_required:
                issues.append(
                    _issue(
                        "error",
                        "parameter.required.missing",
                        filename,
                        parameter_id,
                        "Required parameter has no entry.",
                        "confirmed value",
                        "missing",
                        "Add the parameter entry with a supported value and unit.",
                    )
                )
            continue

        value = entry.get("value")
        status = entry.get("status", "draft")
        if is_required and status != "confirmed":
            issues.append(
                _issue(
                    "error",
                    "parameter.required.not_confirmed",
                    filename,
                    parameter_id,
                    "Required parameter is not confirmed.",
                    "status=confirmed",
                    str(status),
                    "Verify the value and mark it confirmed with its source.",
                )
            )
        elif status == "draft":
            issues.append(
                _issue(
                    "warning",
                    "parameter.draft",
                    filename,
                    parameter_id,
                    "Parameter is still marked as a draft.",
                    "confirmed or not_applicable when appropriate",
                    "draft",
                )
            )
        if status == "confirmed" and value is None:
            issues.append(
                _issue(
                    "error",
                    "parameter.value.missing",
                    filename,
                    parameter_id,
                    "Confirmed parameter has no value.",
                    "non-empty value",
                    "null",
                )
            )
        if value is None:
            continue

        kind = definition.get("kind")
        allowed = entry.get("allowed_values", definition.get("allowed"))
        if allowed and value not in allowed:
            issues.append(
                _issue(
                    "error",
                    "parameter.value.not_allowed",
                    filename,
                    parameter_id,
                    "Value is not one of the registered options.",
                    ", ".join(map(str, allowed)),
                    repr(value),
                )
            )
        if kind in _NUMERIC_KINDS:
            numeric_value = _finite_number(
                value, filename, parameter_id, "parameter.value.numeric", issues
            )
            unit = entry.get("unit")
            if not unit:
                issues.append(
                    _issue(
                        "warning",
                        "parameter.unit.missing",
                        filename,
                        parameter_id,
                        "Numeric parameter has no unit.",
                        f"unit for quantity kind {kind}",
                        repr(unit),
                    )
                )
            valid_range = entry.get("valid_range") or {}
            if not isinstance(valid_range, dict):
                issues.append(
                    _issue(
                        "error",
                        "parameter.range.invalid",
                        filename,
                        f"{parameter_id}.valid_range",
                        "Valid range must be a mapping.",
                        "mapping with numeric min/max",
                        repr(valid_range),
                    )
                )
                valid_range = {}
            minimum = _optional_finite_bound(
                valid_range.get("min"),
                filename,
                f"{parameter_id}.valid_range.min",
                issues,
            )
            maximum = _optional_finite_bound(
                valid_range.get("max"),
                filename,
                f"{parameter_id}.valid_range.max",
                issues,
            )
            if numeric_value is not None:
                if minimum is not None and numeric_value < minimum:
                    issues.append(
                        _issue(
                            "error",
                            "parameter.value.below_range",
                            filename,
                            parameter_id,
                            "Value is below the configured valid range.",
                            f">= {minimum}",
                            str(numeric_value),
                        )
                    )
                if maximum is not None and numeric_value > maximum:
                    issues.append(
                        _issue(
                            "error",
                            "parameter.value.above_range",
                            filename,
                            parameter_id,
                            "Value is above the configured valid range.",
                            f"<= {maximum}",
                            str(numeric_value),
                        )
                    )
                if (
                    minimum is not None
                    and maximum is not None
                    and minimum > maximum
                ):
                    issues.append(
                        _issue(
                            "error",
                            "parameter.range.invalid",
                            filename,
                            f"{parameter_id}.valid_range",
                            "Configured minimum exceeds maximum.",
                            "min <= max",
                            f"{minimum} > {maximum}",
                        )
                    )
        elif kind == "boolean" and not isinstance(value, bool):
            issues.append(
                _issue(
                    "error",
                    "parameter.value.boolean",
                    filename,
                    parameter_id,
                    "Value must be a YAML boolean.",
                    "true or false",
                    repr(value),
                )
            )
        elif kind == "text" and not isinstance(value, str):
            issues.append(
                _issue(
                    "error",
                    "parameter.value.text",
                    filename,
                    parameter_id,
                    "Value must be text.",
                    "string",
                    type(value).__name__,
                )
            )
        elif kind == "timestamp":
            if not isinstance(value, str):
                issues.append(
                    _issue(
                        "error",
                        "parameter.value.timestamp",
                        filename,
                        parameter_id,
                        "Timestamp parameter must be ISO 8601 text.",
                        "ISO 8601 timestamp with explicit UTC offset",
                        repr(value),
                    )
                )
            else:
                try:
                    parsed_timestamp = datetime.fromisoformat(value)
                except ValueError:
                    parsed_timestamp = None
                if (
                    parsed_timestamp is None
                    or parsed_timestamp.utcoffset() is None
                ):
                    issues.append(
                        _issue(
                            "error",
                            "parameter.value.timestamp",
                            filename,
                            parameter_id,
                            "Timestamp must be valid ISO 8601 with an explicit UTC offset.",
                            "timezone-aware ISO 8601 timestamp",
                            value,
                        )
                    )
        elif kind == "categorical" and not isinstance(value, str):
            issues.append(
                _issue(
                    "error",
                    "parameter.value.categorical",
                    filename,
                    parameter_id,
                    "Categorical value must be text.",
                    "string",
                    type(value).__name__,
                )
            )

        source_type = str(entry.get("source_type") or "").strip().casefold()
        source_ref = str(entry.get("source_ref") or "").strip().casefold()
        missing_source = source_type in {
            "",
            "none",
            "null",
            "unknown",
            "unassigned",
        } or source_ref in {
            "",
            "none",
            "null",
            "unknown",
            "no source recorded",
            "not provided",
        }
        if status == "confirmed" and missing_source:
            issues.append(
                _issue(
                    "error" if is_required else "warning",
                    "parameter.provenance.incomplete",
                    filename,
                    parameter_id,
                    "Confirmed value has incomplete source provenance.",
                    "source_type and source_ref",
                    f"{entry.get('source_type')!r}, {entry.get('source_ref')!r}",
                    "Record the evidence source for this value.",
                )
            )


def _finite_number(
    value: Any,
    file: str,
    location: str,
    code: str,
    issues: list[ValidationIssue],
) -> float | None:
    if isinstance(value, bool):
        number = None
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = None
    if number is None or not math.isfinite(number):
        issues.append(
            _issue(
                "error",
                code,
                file,
                location,
                "Expected a finite numeric value.",
                "finite number",
                repr(value),
            )
        )
        return None
    return number


def _optional_finite_bound(
    value: Any, file: str, location: str, issues: list[ValidationIssue]
) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float("nan")
    if not math.isfinite(numeric):
        issues.append(
            _issue(
                "error",
                "parameter.range.bound_invalid",
                file,
                location,
                "Range bound must be a finite number or null.",
                "finite number or null",
                repr(value),
            )
        )
        return None
    return numeric


def _validate_data_directory(
    root: Path,
    kind: str,
    file_overrides: Mapping[str, str],
    issues: list[ValidationIssue],
) -> None:
    directory = Path("inputs") / kind
    absolute_directory = root / directory
    if not absolute_directory.exists():
        issues.append(
            _issue(
                "error",
                "directory.missing",
                directory.as_posix(),
                "",
                f"Input {kind} directory is missing.",
                "existing directory",
                "not found",
            )
        )
        return
    metadata_paths = {
        path.relative_to(root)
        for path in absolute_directory.glob("*.meta.yaml")
    }
    metadata_paths.update(
        relative_path
        for key in file_overrides
        if (relative_path := Path(key)).parent == directory
        and relative_path.name.endswith(".meta.yaml")
    )
    for relative_meta in sorted(metadata_paths):
        metadata = _load_yaml(root, relative_meta, file_overrides, issues)
        if not isinstance(metadata, dict):
            continue
        filename = metadata.get("file")
        if not isinstance(filename, str) or Path(filename).name != filename:
            issues.append(
                _issue(
                    "error",
                    "data.metadata.file_invalid",
                    relative_meta.as_posix(),
                    "file",
                    "Metadata must name a file in its own input directory.",
                    "CSV basename",
                    repr(filename),
                )
            )
            continue
        relative_csv = directory / filename
        if relative_csv.name != relative_meta.name.removesuffix(".meta.yaml") + ".csv":
            issues.append(
                _issue(
                    "error",
                    "data.metadata.file_mismatch",
                    relative_meta.as_posix(),
                    "file",
                    "Metadata filename does not match its paired CSV.",
                    relative_meta.name.removesuffix(".meta.yaml") + ".csv",
                    filename,
                )
            )
        _validate_csv_pair(
            root, kind, relative_meta, relative_csv, metadata, file_overrides, issues
        )
    metadata_names = {
        path.name.removesuffix(".meta.yaml") + ".csv"
        for path in metadata_paths
    }
    for csv_path in sorted(absolute_directory.glob("*.csv")):
        if csv_path.name not in metadata_names:
            issues.append(
                _issue(
                    "warning",
                    "data.metadata.missing",
                    csv_path.relative_to(root).as_posix(),
                    "",
                    "CSV file has no paired metadata contract.",
                    f"{csv_path.stem}.meta.yaml",
                    "missing",
                    "Add metadata describing columns, units, and provenance.",
                )
            )


def _validate_csv_pair(
    root: Path,
    kind: str,
    relative_meta: Path,
    relative_csv: Path,
    metadata: dict[str, Any],
    file_overrides: Mapping[str, str],
    issues: list[ValidationIssue],
) -> None:
    try:
        content = _read_text(root, relative_csv, file_overrides)
    except FileNotFoundError:
        issues.append(
            _issue(
                "error",
                "data.csv.missing",
                relative_csv.as_posix(),
                "",
                "Metadata has no paired CSV file.",
                "existing CSV",
                "not found",
                "Add the CSV file or correct the metadata filename.",
            )
        )
        return
    except (OSError, UnicodeError) as exc:
        issues.append(
            _issue(
                "error",
                "data.csv.read_error",
                relative_csv.as_posix(),
                "",
                "Could not read the CSV file.",
                str(metadata.get("encoding", "UTF-8")),
                str(exc),
            )
        )
        return

    columns = metadata.get("columns")
    if not isinstance(columns, list):
        issues.append(
            _issue(
                "error",
                "data.metadata.columns_invalid",
                relative_meta.as_posix(),
                "columns",
                "Metadata must define a columns list.",
                "list of column definitions",
                type(columns).__name__,
            )
        )
        return
    column_specs = [column for column in columns if isinstance(column, dict)]
    invalid_columns = len(columns) - len(column_specs)
    if invalid_columns:
        issues.append(
            _issue(
                "error",
                "data.metadata.column_invalid",
                relative_meta.as_posix(),
                "columns",
                "Column definitions must be mappings.",
                "mapping with a name field",
                f"{invalid_columns} invalid entries",
            )
        )
    declared_names = [column.get("name") for column in column_specs]
    if any(not isinstance(name, str) or not name for name in declared_names):
        issues.append(
            _issue(
                "error",
                "data.metadata.column_name_missing",
                relative_meta.as_posix(),
                "columns",
                "Each column definition must have a non-empty name.",
                "unique string column names",
                repr(declared_names),
            )
        )
    duplicates = sorted(
        {name for name in declared_names if isinstance(name, str) and declared_names.count(name) > 1}
    )
    for name in duplicates:
        issues.append(
            _issue(
                "error",
                "data.metadata.column_duplicate",
                relative_meta.as_posix(),
                f"columns.{name}",
                "Column name is duplicated in metadata.",
                "unique column name",
                name,
            )
        )

    delimiter = _separator(metadata.get("delimiter", ","))
    if delimiter is None:
        issues.append(
            _issue(
                "error",
                "data.metadata.delimiter_invalid",
                relative_meta.as_posix(),
                "delimiter",
                "CSV delimiter must be a single character.",
                "one character or a supported separator name",
                repr(metadata.get("delimiter")),
            )
        )
        return
    try:
        reader = csv.reader(io.StringIO(content), delimiter=delimiter)
        rows = list(reader)
    except csv.Error as exc:
        issues.append(
            _issue(
                "error",
                "data.csv.parse_error",
                relative_csv.as_posix(),
                "",
                "CSV syntax is invalid.",
                "well-formed delimited rows",
                str(exc),
            )
        )
        return
    if not rows:
        issues.append(
            _issue(
                "warning",
                "data.csv.empty",
                relative_csv.as_posix(),
                "",
                "CSV file is empty.",
                "header row and data rows",
                "no rows",
            )
        )
        return

    headers = rows[0]
    if metadata.get("header_row", True) is not True:
        issues.append(
            _issue(
                "warning",
                "data.csv.headerless",
                relative_csv.as_posix(),
                "",
                "Headerless files are not supported by the registered input reader.",
                "header_row: true",
                str(metadata.get("header_row")),
            )
        )
    if len(set(headers)) != len(headers):
        issues.append(
            _issue(
                "error",
                "data.csv.header_duplicate",
                relative_csv.as_posix(),
                "header",
                "CSV header contains duplicate column names.",
                "unique column names",
                repr(headers),
            )
        )
    missing_columns = [
        column.get("name")
        for column in column_specs
        if column.get("required") is True and column.get("name") not in headers
    ]
    for name in missing_columns:
        issues.append(
            _issue(
                "error",
                "data.csv.required_column_missing",
                relative_csv.as_posix(),
                str(name),
                "Required metadata column is absent from the CSV header.",
                str(name),
                "missing",
            )
        )
    undeclared = [name for name in headers if name not in declared_names]
    if undeclared:
        issues.append(
            _issue(
                "warning",
                "data.csv.undeclared_columns",
                relative_csv.as_posix(),
                "header",
                "CSV has columns not described in metadata.",
                "columns documented in metadata",
                ", ".join(undeclared),
            )
        )
    if len(headers) != len(set(headers)):
        return

    body = rows[1:]
    if not body:
        issues.append(
            _issue(
                "warning",
                "data.csv.no_records",
                relative_csv.as_posix(),
                "",
                "CSV contains a header but no data records.",
                "one or more data records",
                "0 records",
            )
        )
    spec_by_name = {
        column.get("name"): column
        for column in column_specs
        if isinstance(column.get("name"), str)
    }
    timestamps: list[tuple[int, datetime]] = []
    row_dicts: list[dict[str, str]] = []
    decimal = _decimal_symbol(metadata.get("decimal_separator", "."))
    if decimal is None:
        issues.append(
            _issue(
                "error",
                "data.metadata.decimal_invalid",
                relative_meta.as_posix(),
                "decimal_separator",
                "Unsupported decimal separator.",
                "period, comma, or a single character",
                repr(metadata.get("decimal_separator")),
            )
        )
        decimal = "."
    for name, spec in spec_by_name.items():
        if spec.get("required") is not None and not isinstance(
            spec.get("required"), bool
        ):
            issues.append(
                _issue(
                    "error",
                    "data.metadata.required_invalid",
                    relative_meta.as_posix(),
                    f"columns.{name}.required",
                    "Column required flag must be boolean.",
                    "true or false",
                    repr(spec.get("required")),
                )
            )
        if (
            spec.get("quantity_kind") in _NUMERIC_KINDS
            and not spec.get("unit")
        ):
            issues.append(
                _issue(
                    "warning",
                    "data.metadata.unit_missing",
                    relative_meta.as_posix(),
                    f"columns.{name}.unit",
                    "Numeric data column has no unit in metadata.",
                    "unit string",
                    "null or empty",
                )
            )
    for row_number, values in enumerate(body, start=2):
        if len(values) != len(headers):
            issues.append(
                _issue(
                    "error",
                    "data.csv.row_width",
                    relative_csv.as_posix(),
                    f"row {row_number}",
                    "Row has a different number of fields than the header.",
                    f"{len(headers)} fields",
                    f"{len(values)} fields",
                )
            )
            continue
        record = dict(zip(headers, values))
        row_dicts.append(record)
        for name, spec in spec_by_name.items():
            if name not in headers:
                continue
            value = record[name].strip()
            if not value:
                if spec.get("required") is True:
                    issues.append(
                        _issue(
                            "error",
                            "data.csv.required_value_missing",
                            relative_csv.as_posix(),
                            f"row {row_number}.{name}",
                            "Required cell is empty.",
                            "non-empty value",
                            "blank",
                        )
                    )
                continue
            quantity_kind = spec.get("quantity_kind")
            if quantity_kind == "timestamp" or name.lower() == "timestamp":
                try:
                    timestamp = datetime.fromisoformat(value)
                except ValueError:
                    issues.append(
                        _issue(
                            "error",
                            "data.csv.timestamp_invalid",
                            relative_csv.as_posix(),
                            f"row {row_number}.{name}",
                            "Timestamp is not valid ISO 8601.",
                            "ISO 8601 timestamp with explicit UTC offset",
                            value,
                        )
                    )
                    continue
                if timestamp.utcoffset() is None:
                    issues.append(
                        _issue(
                            "error",
                            "data.csv.timestamp_timezone_missing",
                            relative_csv.as_posix(),
                            f"row {row_number}.{name}",
                            "Timestamp has no explicit UTC offset.",
                            "timezone-aware ISO 8601 timestamp",
                            value,
                        )
                    )
                    continue
                timestamps.append((row_number, timestamp))
                continue
            if quantity_kind in _NUMERIC_KINDS:
                numeric_text = value
                if decimal != ".":
                    numeric_text = numeric_text.replace(decimal, ".")
                try:
                    numeric = float(numeric_text)
                except ValueError:
                    issues.append(
                        _issue(
                            "error",
                            "data.csv.numeric_invalid",
                            relative_csv.as_posix(),
                            f"row {row_number}.{name}",
                            "Expected a numeric cell for this quantity kind.",
                            f"finite number ({quantity_kind})",
                            value,
                        )
                    )
                    continue
                if not math.isfinite(numeric):
                    issues.append(
                        _issue(
                            "error",
                            "data.csv.numeric_nonfinite",
                            relative_csv.as_posix(),
                            f"row {row_number}.{name}",
                            "Numeric value must be finite.",
                            "finite number",
                            value,
                        )
                    )
                valid_range = spec.get("valid_range")
                if isinstance(valid_range, dict):
                    minimum = _optional_data_bound(
                        valid_range.get("min"),
                        relative_meta,
                        f"columns.{name}.valid_range.min",
                        issues,
                    )
                    maximum = _optional_data_bound(
                        valid_range.get("max"),
                        relative_meta,
                        f"columns.{name}.valid_range.max",
                        issues,
                    )
                    if minimum is not None and numeric < minimum:
                        issues.append(
                            _issue(
                                "warning",
                                "data.csv.value_below_range",
                                relative_csv.as_posix(),
                                f"row {row_number}.{name}",
                                "Value is below the metadata-declared range.",
                                f">= {minimum}",
                                value,
                            )
                        )
                    if maximum is not None and numeric > maximum:
                        issues.append(
                            _issue(
                                "warning",
                                "data.csv.value_above_range",
                                relative_csv.as_posix(),
                                f"row {row_number}.{name}",
                                "Value is above the metadata-declared range.",
                                f"<= {maximum}",
                                value,
                            )
                        )

    _validate_timestamps(
        relative_csv, metadata, timestamps, issues
    )
    _validate_unique_columns(
        relative_csv, metadata, headers, row_dicts, issues
    )
    _validate_cross_field_rules(
        relative_csv, metadata, headers, row_dicts, issues
    )
    _validate_qc_codes(
        relative_csv, metadata, headers, row_dicts, issues
    )
    if kind == "timeseries" and not any(
        spec.get("quantity_kind") == "timestamp"
        or str(spec.get("name", "")).lower() == "timestamp"
        for spec in column_specs
    ):
        issues.append(
            _issue(
                "warning",
                "timeseries.timestamp_undeclared",
                relative_meta.as_posix(),
                "columns",
                "Time-series metadata does not declare a timestamp column.",
                "one required timestamp column",
                "none",
            )
        )


def _optional_data_bound(
    value: Any,
    relative_meta: Path,
    location: str,
    issues: list[ValidationIssue],
) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = float("nan")
    if not math.isfinite(numeric):
        issues.append(
            _issue(
                "error",
                "data.metadata.range_bound_invalid",
                relative_meta.as_posix(),
                location,
                "Metadata range bound must be finite or null.",
                "finite number or null",
                repr(value),
            )
        )
        return None
    return numeric


def _validate_qc_codes(
    relative_csv: Path,
    metadata: dict[str, Any],
    headers: list[str],
    records: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    allowed = metadata.get("qc_flag_codes", metadata.get("valid_qc_codes"))
    if allowed is None:
        return
    if not isinstance(allowed, list):
        issues.append(
            _issue(
                "error",
                "data.metadata.qc_codes_invalid",
                relative_csv.as_posix(),
                "qc_flag_codes",
                "QC flag codes must be a list.",
                "list of valid codes or null",
                repr(allowed),
            )
        )
        return
    if "qc_flag" not in headers:
        if allowed:
            issues.append(
                _issue(
                    "warning",
                    "data.csv.qc_column_missing",
                    relative_csv.as_posix(),
                    "qc_flag",
                    "Metadata defines QC codes but CSV has no qc_flag column.",
                    "qc_flag column",
                    "missing",
                )
            )
        return
    allowed_text = {str(code) for code in allowed}
    for row_number, record in enumerate(records, start=2):
        value = record["qc_flag"].strip()
        if value and value not in allowed_text:
            issues.append(
                _issue(
                    "warning",
                    "data.csv.qc_code_invalid",
                    relative_csv.as_posix(),
                    f"row {row_number}.qc_flag",
                    "QC flag is not declared in metadata.",
                    ", ".join(sorted(allowed_text)),
                    value,
                )
            )


def _validate_timestamps(
    relative_csv: Path,
    metadata: dict[str, Any],
    timestamps: list[tuple[int, datetime]],
    issues: list[ValidationIssue],
) -> None:
    if not timestamps:
        return
    values = [timestamp for _row, timestamp in timestamps]
    if any(later <= earlier for earlier, later in zip(values, values[1:])):
        issues.append(
            _issue(
                "error",
                "timeseries.timestamp.order",
                relative_csv.as_posix(),
                "timestamp",
                "Timestamps must be strictly increasing and unique.",
                "strictly increasing timestamps",
                "out-of-order or duplicate timestamp",
            )
        )
    expected_interval = metadata.get("interval")
    if expected_interval and len(values) > 1:
        try:
            import pandas as pd

            expected_seconds = pd.Timedelta(expected_interval).total_seconds()
        except (ImportError, TypeError, ValueError):
            issues.append(
                _issue(
                    "warning",
                    "timeseries.interval.invalid",
                    relative_csv.as_posix(),
                    "interval",
                    "Could not interpret the declared sampling interval.",
                    "duration such as '1 hour'",
                    str(expected_interval),
                )
            )
            return
        for (row_before, earlier), (row_after, later) in zip(timestamps, timestamps[1:]):
            seconds = (later - earlier).total_seconds()
            if seconds > expected_seconds * float("1.5"):
                issues.append(
                    _issue(
                        "warning",
                        "timeseries.gap",
                        relative_csv.as_posix(),
                        f"rows {row_before}-{row_after}",
                        "Time-series interval contains a gap.",
                        f"about {expected_interval}",
                        f"{seconds:g} seconds",
                    )
                )


def _separator(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    names = {
        "comma": ",",
        "tab": "\t",
        "semicolon": ";",
        "pipe": "|",
    }
    separator = names.get(value.lower(), value)
    return separator if len(separator) == 1 else None


def _decimal_symbol(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    names = {"period": ".", "comma": ","}
    symbol = names.get(value.lower(), value)
    return symbol if len(symbol) == 1 else None


def _validate_unique_columns(
    relative_csv: Path,
    metadata: dict[str, Any],
    headers: list[str],
    records: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    unique_columns = metadata.get("unique_columns", [])
    if not unique_columns:
        return
    if isinstance(unique_columns, str):
        unique_columns = [unique_columns]
    if not isinstance(unique_columns, list):
        issues.append(
            _issue(
                "error",
                "data.metadata.unique_columns_invalid",
                relative_csv.as_posix(),
                "unique_columns",
                "unique_columns must be a list of column names.",
                "list of existing columns",
                repr(unique_columns),
            )
        )
        return
    missing = [column for column in unique_columns if column not in headers]
    if missing:
        issues.append(
            _issue(
                "error",
                "data.metadata.unique_column_missing",
                relative_csv.as_posix(),
                "unique_columns",
                "Declared unique-key columns are missing.",
                ", ".join(unique_columns),
                ", ".join(missing),
            )
        )
        return
    seen: set[tuple[str, ...]] = set()
    for row_number, record in enumerate(records, start=2):
        key = tuple(record[column] for column in unique_columns)
        if key in seen:
            issues.append(
                _issue(
                    "error",
                    "data.csv.unique_key_duplicate",
                    relative_csv.as_posix(),
                    f"row {row_number}",
                    "Row duplicates a declared unique key.",
                    "unique values for " + ", ".join(unique_columns),
                    repr(key),
                )
            )
        seen.add(key)


def _validate_cross_field_rules(
    relative_csv: Path,
    metadata: dict[str, Any],
    headers: list[str],
    records: list[dict[str, str]],
    issues: list[ValidationIssue],
) -> None:
    rules = metadata.get("cross_field_rules", [])
    if not rules:
        return
    if not isinstance(rules, list):
        issues.append(
            _issue(
                "error",
                "data.metadata.cross_field_rules_invalid",
                relative_csv.as_posix(),
                "cross_field_rules",
                "Cross-field rules must be a list.",
                "list of rule mappings",
                repr(rules),
            )
        )
        return
    operators = {
        "lt": lambda left, right: left < right,
        "lte": lambda left, right: left <= right,
        "gt": lambda left, right: left > right,
        "gte": lambda left, right: left >= right,
        "eq": lambda left, right: left == right,
    }
    for rule_number, rule in enumerate(rules, start=1):
        if not isinstance(rule, dict):
            issues.append(
                _issue(
                    "error",
                    "data.metadata.cross_field_rule_invalid",
                    relative_csv.as_posix(),
                    f"cross_field_rules[{rule_number}]",
                    "Cross-field rule must be a mapping.",
                    "left, operator, right",
                    repr(rule),
                )
            )
            continue
        left = rule.get("left")
        right = rule.get("right")
        operator = rule.get("operator")
        if left not in headers or right not in headers or operator not in operators:
            issues.append(
                _issue(
                    "error",
                    "data.metadata.cross_field_rule_invalid",
                    relative_csv.as_posix(),
                    f"cross_field_rules[{rule_number}]",
                    "Cross-field rule references an unknown column or operator.",
                    "known columns and lt/lte/gt/gte/eq",
                    repr(rule),
                )
            )
            continue
        for row_number, record in enumerate(records, start=2):
            try:
                left_value = float(record[left])
                right_value = float(record[right])
                satisfied = operators[operator](left_value, right_value)
            except (TypeError, ValueError):
                continue
            if not satisfied:
                issues.append(
                    _issue(
                        "error",
                        "data.csv.cross_field_rule_failed",
                        relative_csv.as_posix(),
                        f"row {row_number}.{left}/{right}",
                        rule.get("message", "Cross-field constraint failed."),
                        f"{left} {operator} {right}",
                        f"{record[left]} vs {record[right]}",
                    )
                )
