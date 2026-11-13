"""Tests for structured project-input validation and preview overlays."""

from __future__ import annotations

from pathlib import Path

import yaml

from aquasolar.validation import validate_project


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _make_project(root: Path, *, include_conditional: bool = True) -> None:
    _write_yaml(
        root / "inputs" / "input_index.yaml",
        {
            "parameters": [
                {
                    "file": "demo",
                    "id": "demo.mode",
                    "kind": "categorical",
                    "required_when": "always",
                    "allowed": ["off", "on"],
                },
                {
                    "file": "demo",
                    "id": "demo.limit",
                    "kind": "fraction",
                    "required_when": "always",
                    "allowed": None,
                },
                {
                    "file": "demo",
                    "id": "demo.threshold",
                    "kind": "fraction",
                    "required_when": "demo.mode == on",
                    "allowed": None,
                },
            ]
        },
    )
    parameters = [
        {
            "id": "demo.mode",
            "value": "on",
            "unit": None,
            "source_type": "assumption",
            "source_ref": "test fixture",
            "status": "confirmed",
        },
        {
            "id": "demo.limit",
            "value": 0.8,
            "unit": "1",
            "source_type": "assumption",
            "source_ref": "test fixture",
            "status": "confirmed",
            "valid_range": {"min": 0.0, "max": 1.0},
        },
    ]
    if include_conditional:
        parameters.append(
            {
                "id": "demo.threshold",
                "value": 0.4,
                "unit": "1",
                "source_type": "assumption",
                "source_ref": "test fixture",
                "status": "confirmed",
            }
        )
    _write_yaml(root / "inputs" / "parameters" / "demo.yaml", {"parameters": parameters})

    tables = root / "inputs" / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    _write_yaml(
        tables / "sample.meta.yaml",
        {
            "file": "sample.csv",
            "delimiter": "comma",
            "decimal_separator": "period",
            "header_row": True,
            "columns": [
                {"name": "sample_id", "required": True, "quantity_kind": None},
                {
                    "name": "low",
                    "required": True,
                    "quantity_kind": "fraction",
                    "unit": "1",
                },
                {
                    "name": "high",
                    "required": True,
                    "quantity_kind": "fraction",
                    "unit": "1",
                },
            ],
            "unique_columns": ["sample_id"],
            "cross_field_rules": [
                {"left": "low", "operator": "lte", "right": "high"}
            ],
        },
    )
    (tables / "sample.csv").write_text(
        "sample_id,low,high\nA,0.2,0.9\nB,0.1,0.8\n",
        encoding="utf-8",
    )

    timeseries = root / "inputs" / "timeseries"
    timeseries.mkdir(parents=True, exist_ok=True)
    _write_yaml(
        timeseries / "weather.meta.yaml",
        {
            "file": "weather.csv",
            "delimiter": "comma",
            "decimal_separator": "period",
            "header_row": True,
            "interval": "1 hour",
            "columns": [
                {
                    "name": "timestamp",
                    "required": True,
                    "quantity_kind": "timestamp",
                },
                {
                    "name": "ghi",
                    "required": True,
                    "quantity_kind": "irradiance",
                    "unit": "W/m2",
                    "valid_range": {"min": 0.0, "max": 1500.0},
                },
            ],
        },
    )
    (timeseries / "weather.csv").write_text(
        "timestamp,ghi\n"
        "2025-01-01T00:00:00+00:00,0\n"
        "2025-01-01T01:00:00+00:00,12.5\n",
        encoding="utf-8",
    )


def test_valid_project_has_no_findings(tmp_path):
    _make_project(tmp_path)

    report = validate_project(tmp_path)

    assert report.ok
    assert report.issues == ()


def test_parameter_preview_reports_range_error_without_writing(tmp_path):
    _make_project(tmp_path)
    parameter_file = tmp_path / "inputs" / "parameters" / "demo.yaml"
    before = parameter_file.read_text(encoding="utf-8")

    report = validate_project(
        tmp_path,
        parameter_overrides={"demo.limit": {"value": 1.2}},
    )

    assert not report.ok
    assert any(issue.code == "parameter.value.above_range" for issue in report.issues)
    assert parameter_file.read_text(encoding="utf-8") == before


def test_conditional_required_parameter_is_reported_when_missing(tmp_path):
    _make_project(tmp_path, include_conditional=False)

    report = validate_project(tmp_path)

    finding = next(
        issue
        for issue in report.issues
        if issue.code == "parameter.required.missing"
    )
    assert finding.location == "demo.threshold"


def test_timeseries_checks_timezone_order_and_declared_range(tmp_path):
    _make_project(tmp_path)

    report = validate_project(
        tmp_path,
        file_overrides={
            "inputs/timeseries/weather.csv": (
                "timestamp,ghi\n"
                "2025-01-01T01:00:00+00:00,1600\n"
                "2025-01-01T00:00:00+00:00,not-a-number\n"
            )
        },
    )

    codes = {issue.code for issue in report.issues}
    assert "timeseries.timestamp.order" in codes
    assert "data.csv.numeric_invalid" in codes
    assert "data.csv.value_above_range" in codes


def test_declared_table_key_and_cross_field_rules_are_enforced(tmp_path):
    _make_project(tmp_path)
    table_path = tmp_path / "inputs" / "tables" / "sample.csv"
    table_path.write_text(
        "sample_id,low,high\nA,0.9,0.2\nA,0.1,0.5\n",
        encoding="utf-8",
    )

    report = validate_project(tmp_path)

    codes = {issue.code for issue in report.issues}
    assert "data.csv.unique_key_duplicate" in codes
    assert "data.csv.cross_field_rule_failed" in codes
