"""Load and serve all user-supplied inputs from the registry."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .conditions import evaluate_required_when
from .errors import (
    DraftInputError,
    InputError,
    InvalidInputError,
    MissingInputError,
)
from .schema import ParameterEntry


_INPUT_INDEX_PATH = Path("inputs/input_index.yaml")
_PARAMETERS_DIR = Path("inputs/parameters")
_TABLES_DIR = Path("inputs/tables")
_TIMESERIES_DIR = Path("inputs/timeseries")
_STATUS_PATH = Path("inputs/STATUS.md")


class Registry:
    """Read-only view of all validated inputs."""

    def __init__(
        self,
        params: Dict[str, ParameterEntry],
        tables: Dict[str, Any],
        timeseries: Dict[str, Any],
        file_hashes: Dict[str, str],
    ):
        self._params = params
        self._tables = tables
        self._timeseries = timeseries
        self._hashes = file_hashes

    def get(self, id_: str) -> Any:
        """Return the value of a parameter by its fully-qualified id."""
        entry = self._params.get(id_)
        if entry is None:
            raise KeyError(f"Registry id '{id_}' not found")
        if entry.status == "draft":
            raise DraftInputError(
                f"parameters/{self._find_param_file(id_)}",
                id_,
                "status=confirmed",
                "draft",
            )
        return entry.value

    def require(self, ids: List[str]) -> Dict[str, Any]:
        """Return values for a list of ids, raising on any missing/draft."""
        result = {}
        for id_ in ids:
            result[id_] = self.get(id_)
        return result

    def status_report(self) -> str:
        """Human-readable status of all known parameters."""
        lines = ["# Registry Status Report"]
        for id_, entry in sorted(self._params.items()):
            lines.append(f"- `{id_}`: value={entry.value!r}, "
                         f"unit={entry.unit!r}, status={entry.status!r}, "
                         f"source={entry.source_type!r}")
        return "\n".join(lines)

    def file_hashes(self) -> Dict[str, str]:
        return dict(self._hashes)

    def _find_param_file(self, id_: str) -> str:
        """Reverse-lookup which parameter file an id belongs to."""
        for fpath in _PARAMETERS_DIR.glob("*.yaml"):
            with open(fpath, encoding="utf-8") as f:
                data = yaml.safe_load(f) or []
            for item in data:
                if item.get("id") == id_:
                    return fpath.name
        return "<unknown>"


def _hash_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_registry() -> Registry:
    """Load every input file, validate, and return a Registry.

    Reads:
    - inputs/input_index.yaml (master list of all legal ids)
    - inputs/parameters/*.yaml (single values)
    - inputs/tables/*.csv + *.meta.yaml (tables)
    - inputs/timeseries/*.csv + *.meta.yaml (time series)

    Raises InputError on any blocking issue.
    """
    params: Dict[str, ParameterEntry] = {}
    tables: Dict[str, Any] = {}
    timeseries: Dict[str, Any] = {}
    file_hashes: Dict[str, str] = {}

    # Load input index
    if not _INPUT_INDEX_PATH.exists():
        raise InputError(f"input index not found: {_INPUT_INDEX_PATH}")
    with open(_INPUT_INDEX_PATH, encoding="utf-8") as f:
        input_index = yaml.safe_load(f)

    known_ids = {item["id"] for item in input_index.get("parameters", [])}

    # Load parameter files
    for fpath in sorted(_PARAMETERS_DIR.glob("*.yaml")):
        file_hashes[str(fpath)] = _hash_file(fpath)
        with open(fpath, encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
        if not isinstance(data, list):
            raise InputError(f"Parameter file {fpath} is not a list")
        for item in data:
            if not isinstance(item, dict):
                raise InputError(f"Parameter entry in {fpath} is not a dict")
            entry = ParameterEntry(**item)
            key = entry.id
            if key not in known_ids:
                # Unregistered id — flag but do not block
                pass
            params[key] = entry

    # Validate required_when conditions and draft status
    # Build a partial registry for condition evaluation
    full_registry: Dict[str, Any] = {}
    for id_, entry in params.items():
        if entry.status == "confirmed":
            full_registry[id_] = entry.value

    # Second pass: check required_when
    for item_def in input_index.get("parameters", []):
        id_ = item_def["id"]
        req_when = item_def.get("required_when", "always")
        is_required = evaluate_required_when(req_when, full_registry)

        if id_ not in params:
            if is_required:
                raise MissingInputError(
                    f"parameters/{_guess_file(id_, input_index)}",
                    id_,
                    "status=confirmed",
                )
            continue

        entry = params[id_]
        if is_required and entry.status != "confirmed":
            raise DraftInputError(
                f"parameters/{_guess_file(id_, input_index)}",
                id_,
                "status=confirmed",
                entry.status,
            )

    # Load table files
    for meta_fpath in sorted(_TABLES_DIR.glob("*.meta.yaml")):
        csv_fpath = meta_fpath.with_suffix(".csv")
        file_hashes[str(meta_fpath)] = _hash_file(meta_fpath)
        file_hashes[str(csv_fpath)] = _hash_file(csv_fpath)

        with open(meta_fpath, encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        name = meta_fpath.stem.replace(".meta", "")
        tables[name] = {"meta": meta, "data": _read_csv(csv_fpath, name)}

    # Load time-series files
    for meta_fpath in sorted(_TIMESERIES_DIR.glob("*.meta.yaml")):
        csv_fpath = meta_fpath.with_suffix(".csv")
        file_hashes[str(meta_fpath)] = _hash_file(meta_fpath)
        file_hashes[str(csv_fpath)] = _hash_file(csv_fpath)

        with open(meta_fpath, encoding="utf-8") as f:
            meta = yaml.safe_load(f)
        name = meta_fpath.stem.replace(".meta", "")
        timeseries[name] = {"meta": meta, "data": _read_csv(csv_fpath, name)}

    return Registry(params, tables, timeseries, file_hashes)


def _guess_file(id_: str, input_index: dict) -> str:
    """Guess which parameter file an id belongs to."""
    for item in input_index.get("parameters", []):
        if item["id"] == id_:
            return f"{item['file']}.yaml"
    return "unknown.yaml"


def _read_csv(path: Path, name: str) -> Any:
    """Read a CSV file using pandas. Returns a DataFrame."""
    try:
        import pandas as pd
    except ImportError:
        # Fallback: read as list of dicts
        import csv
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    df = pd.read_csv(path)
    return df
