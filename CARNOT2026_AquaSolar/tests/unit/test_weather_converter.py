"""Tests for the unified weather conversion command."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
import yaml

from aquasolar.io.weather_converter import convert_weather_file
from aquasolar.validation import _validate_csv_pair


def _write_nasa_json(path: Path) -> None:
    parameter_data = {
        "ALLSKY_SFC_SW_DWN": ("Wh/m^2", 100.0),
        "ALLSKY_SFC_SW_DNI": ("Wh/m^2", 200.0),
        "ALLSKY_SFC_SW_DIFF": ("Wh/m^2", 30.0),
        "T2M": ("C", 21.0),
        "WS10M": ("m/s", 2.5),
        "RH2M": ("%", 55.0),
    }
    payload = {
        "header": {"time_standard": "UTC", "fill_value": -999.0},
        "parameters": {
            name: {"units": units}
            for name, (units, _value) in parameter_data.items()
        },
        "properties": {
            "parameter": {
                name: {"2025010100": value}
                for name, (_units, value) in parameter_data.items()
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_nasa_conversion_writes_webui_ready_csv_and_metadata(
    tmp_path: Path,
) -> None:
    source = tmp_path / "weather.json"
    output = tmp_path / "inputs" / "timeseries" / "weather.csv"
    _write_nasa_json(source)

    record_count, metadata_path = convert_weather_file(
        source,
        output,
        source_format="nasa-power",
        site_timezone="Asia/Dubai",
    )

    with output.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert record_count == 1
    assert rows[0]["timestamp"] == "2025-01-01T00:00:00+00:00"
    assert rows[0]["dni"] == "200.0"
    assert metadata["file"] == output.name
    assert metadata["site_timezone"] == "Asia/Dubai"
    assert {
        column["name"]
        for column in metadata["columns"]
        if column["required"]
    } == {"timestamp", "ghi", "dni", "dhi", "t_ambient", "wind_speed"}
    issues = []
    _validate_csv_pair(
        tmp_path,
        "timeseries",
        Path("inputs/timeseries/weather.meta.yaml"),
        Path("inputs/timeseries/weather.csv"),
        metadata,
        {},
        issues,
    )
    assert not [issue for issue in issues if issue.severity == "error"]


def test_epw_conversion_requires_calendar_year_before_creating_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "weather.csv"

    with pytest.raises(ValueError, match="requires --calendar-year"):
        convert_weather_file(
            tmp_path / "source.epw",
            output,
            source_format="epw",
            site_timezone="Asia/Dubai",
        )

    assert not output.exists()


def test_converter_refuses_existing_metadata_without_creating_csv(
    tmp_path: Path,
) -> None:
    source = tmp_path / "weather.json"
    output = tmp_path / "weather.csv"
    _write_nasa_json(source)
    metadata = tmp_path / "weather.meta.yaml"
    metadata.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Metadata output already exists"):
        convert_weather_file(
            source,
            output,
            source_format="nasa-power",
            site_timezone="Asia/Dubai",
        )

    assert not output.exists()
    assert metadata.read_text(encoding="utf-8") == "keep"


def test_converter_rejects_unknown_site_timezone(tmp_path: Path) -> None:
    source = tmp_path / "weather.json"
    output = tmp_path / "weather.csv"
    _write_nasa_json(source)

    with pytest.raises(ValueError, match="Unknown IANA site timezone"):
        convert_weather_file(
            source,
            output,
            source_format="nasa-power",
            site_timezone="Not/A_Real_Zone",
        )

    assert not output.exists()
