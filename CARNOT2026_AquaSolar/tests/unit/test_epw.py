"""TOY EPW conversion tests using small in-memory weather records."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from aquasolar.io.epw import convert_epw_to_weather_csv


def _toy_epw_record(hour: str = "1") -> list[str]:
    fields = ["0"] * 35
    fields[0] = "2001"
    fields[1] = "1"
    fields[2] = "1"
    fields[3] = hour
    fields[4] = "30"
    fields[6] = "25.0"
    fields[8] = "50"
    fields[13] = "100"
    fields[14] = "200"
    fields[15] = "30"
    fields[21] = "2.5"
    return fields


def _write_toy_epw(path: Path, records: list[list[str]]) -> None:
    header = [
        "LOCATION,Toy,Region,Country,Source,Station,25,55,4,10",
        "DESIGN CONDITIONS",
        "TYPICAL/EXTREME PERIODS",
        "GROUND TEMPERATURES",
        "HOLIDAYS/DAYLIGHT SAVINGS",
        "COMMENTS 1",
        "COMMENTS 2",
        "DATA PERIODS",
    ]
    path.write_text(
        "\n".join(header + [",".join(record) for record in records]) + "\n",
        encoding="utf-8",
    )


def test_converts_toy_epw_to_project_weather_columns(tmp_path: Path) -> None:
    source = tmp_path / "toy.epw"
    output = tmp_path / "weather.csv"
    next_record = _toy_epw_record("2")
    next_record[0] = "1985"
    _write_toy_epw(source, [_toy_epw_record(), next_record])

    written = convert_epw_to_weather_csv(source, output, calendar_year=2001)

    with output.open(encoding="utf-8", newline="") as result_file:
        rows = list(csv.DictReader(result_file))
    assert written == 2
    assert rows[0]["timestamp"] == "2001-01-01T00:30:00+04:00"
    assert rows[0]["ghi"] == "100.0"
    assert rows[0]["dni"] == "200.0"
    assert rows[0]["dhi"] == "30.0"
    assert rows[0]["t_ambient"] == "25.0"
    assert rows[0]["wind_speed"] == "2.5"
    assert rows[0]["relative_humidity"] == "50.0"
    assert rows[0]["poa_irradiance"] == ""
    assert rows[0]["cloud_cover"] == ""
    assert rows[1]["timestamp"] == "2001-01-01T01:30:00+04:00"


def test_does_not_replace_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "toy.epw"
    output = tmp_path / "weather.csv"
    _write_toy_epw(source, [_toy_epw_record()])
    output.write_text("keep this file\n", encoding="utf-8")

    with pytest.raises(FileExistsError):
        convert_epw_to_weather_csv(source, output, calendar_year=2001)

    assert output.read_text(encoding="utf-8") == "keep this file\n"


def test_rejects_missing_required_irradiance(tmp_path: Path) -> None:
    source = tmp_path / "toy.epw"
    output = tmp_path / "weather.csv"
    record = _toy_epw_record()
    record[13] = "9999"
    _write_toy_epw(source, [record])

    with pytest.raises(ValueError, match="missing-value sentinel for GHI"):
        convert_epw_to_weather_csv(source, output, calendar_year=2001)

    assert not output.exists()


@pytest.mark.parametrize(
    ("field_index", "field_name"),
    [(14, "DNI"), (15, "DHI")],
)
def test_rejects_missing_runner_required_irradiance(
    tmp_path: Path, field_index: int, field_name: str
) -> None:
    source = tmp_path / "toy.epw"
    output = tmp_path / "weather.csv"
    record = _toy_epw_record()
    record[field_index] = "9999"
    _write_toy_epw(source, [record])

    with pytest.raises(ValueError, match=f"missing-value sentinel for {field_name}"):
        convert_epw_to_weather_csv(source, output, calendar_year=2001)

    assert not output.exists()
