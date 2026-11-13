"""Load and validate module lifecycle settings for the local workbench."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


_MODULE_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*")
_OPERATIONAL_STATES = {"operational", "prototype", "not_integrated"}
_DATA_KINDS = {"tables", "timeseries"}


def load_module_registry(root: Path) -> list[dict[str, Any]]:
    """Load module settings and reject malformed or ambiguous configuration."""
    config_path = root / "inputs" / "module_registry.yaml"
    try:
        with config_path.open(encoding="utf-8") as stream:
            config = yaml.safe_load(stream)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not load module registry {config_path}: {exc}") from exc
    if not isinstance(config, dict) or not isinstance(config.get("modules"), list):
        raise ValueError("Module registry must contain a modules list.")

    modules: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(config["modules"]):
        if not isinstance(value, dict):
            raise ValueError(f"Module registry entry {index + 1} must be a mapping.")
        module_id = value.get("id")
        if not isinstance(module_id, str) or not _MODULE_ID_PATTERN.fullmatch(module_id):
            raise ValueError(f"Module registry entry {index + 1} has an invalid id.")
        if module_id in seen:
            raise ValueError(f"Module registry contains duplicate id {module_id!r}.")
        seen.add(module_id)

        status = value.get("operational_status")
        if not isinstance(status, str) or status not in _OPERATIONAL_STATES:
            raise ValueError(
                f"Module {module_id!r} has unsupported operational_status {status!r}."
            )
        if type(value.get("enabled")) is not bool:
            raise ValueError(f"Module {module_id!r} must have a boolean enabled field.")
        for field in ("parameter_files", "parameter_ids", "data_kinds", "requirements"):
            field_value = value.get(field, [])
            if not isinstance(field_value, list) or not all(
                isinstance(item, str) for item in field_value
            ):
                raise ValueError(f"Module {module_id!r} field {field!r} must be a string list.")
        unknown_kinds = set(value.get("data_kinds", [])) - _DATA_KINDS
        if unknown_kinds:
            raise ValueError(
                f"Module {module_id!r} has unknown data kinds: {', '.join(sorted(unknown_kinds))}."
            )
        if not isinstance(value.get("name"), str) or not value.get("name").strip():
            raise ValueError(f"Module {module_id!r} must have a display name.")
        if not isinstance(value.get("description"), str):
            raise ValueError(f"Module {module_id!r} must have a description.")
        modules.append(value)

    pvt_modules = [module for module in modules if module["id"] == "pvt_runner"]
    if len(pvt_modules) != 1 or pvt_modules[0]["operational_status"] != "operational":
        raise ValueError("The module registry must mark pvt_runner as operational.")
    return modules


def module_is_enabled(root: Path, module_id: str) -> bool:
    """Return whether a configured module is enabled."""
    for module in load_module_registry(root):
        if module["id"] == module_id:
            return module["enabled"]
    raise ValueError(f"Module {module_id!r} is not registered.")
