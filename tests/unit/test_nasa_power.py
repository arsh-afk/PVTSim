"""TOY tests for NASA POWER hourly JSON conversion."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from aquasolar.io.nasa_power import convert_nasa_power_hourly_json


_TOY_PARAMETER_DATA = {
    "ALLSKY_SFC_SW_DWN": ("Wh/m^2", (0.0, 100.0)),
    "ALLSKY_SFC_SW_DNI": ("Wh/m^2", (0.0, 200.0)),
    "ALLSKY_SFC_SW_DIFF": ("Wh/m^2", (0.0, 30.0)),
    "T2M": ("C", (20.0, 21.0)),
    "WS10M": ("m/s", (2.0, 2.5)),
    "RH2M": ("%", (50.0, 55.0)),
}


def _write_toy_json(path: Path, *, time_standard: str = "UTC") -> None:
    parameter_meta = {
        parameter: {"units": units}
        for parameter, (units, _) in _TOY_PARAMETER_DATA.items()
    }
    parameter_series = {
        parameter: {
            "2025010100": values[0],
            "2025010101": values[1],
        }
        for parameter, (_, values) in _TOY_PARAMETER_DATA.items()
    }
    payload = {
        "header": {
            "time_standard": time_standard,
            "fill_value": -999.0,
        },
        "parameters": parameter_meta,
        "properties": {"parameter": parameter_series},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_converts_toy_nasa_hourly_json(tmp_path: Path) -> None:
    source = tmp_path / "toy.json"
    output = tmp_path / "weather.csv"
    _write_toy_json(source)

    written = convert_nasa_power_hourly_json(source, output)

    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert written == 2
    assert rows[0]["timestamp"] == "2025-01-01T00:00:00+00:00"
    assert rows[0]["ghi"] == "0.0"
    assert rows[1]["dni"] == "200.0"
    assert rows[1]["t_ambient"] == "21.0"
    assert rows[1]["wind_speed"] == "2.5"
    assert rows[1]["relative_humidity"] == "55.0"
    assert rows[0]["poa_irradiance"] == ""


def test_rejects_non_utc_data(tmp_path: Path) -> None:
    source = tmp_path / "toy.json"
    output = tmp_path / "weather.csv"
    _write_toy_json(source, time_standard="LST")

    with pytest.raises(ValueError, match="time_standard=UTC"):
        convert_nasa_power_hourly_json(source, output)


def test_rejects_fill_values_without_creating_output(tmp_path: Path) -> None:
    source = tmp_path / "toy.json"
    output = tmp_path / "weather.csv"
    _write_toy_json(source)
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["properties"]["parameter"]["T2M"]["2025010101"] = -999.0
    source.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing or non-finite"):
        convert_nasa_power_hourly_json(source, output)

    assert not output.exists()
