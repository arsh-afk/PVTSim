"""Tests for prevalidated TRNSYS TMY2 TM2 weather conversion."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import yaml

from aquasolar.io.tm2 import _RECORD_FIELDS, convert_tm2_to_weather_csv


_HEADER = " 412170Abu Dhabi Intl            4   N 24 26 E 54  39  27"


def _record(timestamp: datetime, *, invalid_field: str | None = None) -> str:
    values = {
        "year": "95",
        "month": f"{timestamp.month:02d}",
        "day": f"{timestamp.day:02d}",
        "hour": f"{timestamp.hour + 1:02d}",
        "ghi": "100",
        "dni": "200",
        "dhi": "30",
        "dry_bulb": "250",
        "relative_humidity": "87",
        "wind_speed": "24",
        "present_weather": "99999999?0",
    }
    parts = [" "]
    for name, width_text, field_type in _RECORD_FIELDS:
        width = int(width_text)
        if name == invalid_field:
            value = "X" * width
        elif field_type == "flag":
            value = "E"
        else:
            value = values.get(name, "0").rjust(width, "0")
        parts.append(value)
    return "".join(parts)


def _write_tm2(
    path: Path,
    *,
    invalid_first_field: str | None = None,
    first_ghi: str | None = None,
    first_hour: str | None = None,
    wrong_first_record_width: bool = False,
) -> None:
    start = datetime(1995, 1, 1)
    lines = [_HEADER]
    for record_index in range(8760):
        timestamp = start + timedelta(hours=record_index)
        row = _record(
            timestamp,
            invalid_field=invalid_first_field if record_index == 0 else None,
        )
        if record_index == 0 and first_ghi is not None:
            fields = list(row)
            ghi_start = 1 + sum(
                int(width)
                for name, width, _field_type in _RECORD_FIELDS
                if name in {
                    "year",
                    "month",
                    "day",
                    "hour",
                    "etr",
                    "etrn",
                }
            )
            fields[ghi_start : ghi_start + 4] = list(first_ghi)
            row = "".join(fields)
        if record_index == 0 and first_hour is not None:
            fields = list(row)
            fields[7:9] = list(first_hour)
            row = "".join(fields)
        if record_index == 0 and wrong_first_record_width:
            row = row[:-1]
        lines.append(row)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def test_converts_valid_tm2_and_writes_weather_metadata(tmp_path: Path) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"
    _write_tm2(source)

    result = convert_tm2_to_weather_csv(
        source,
        output,
        calendar_year=2025,
        site_timezone="Asia/Dubai",
    )

    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    metadata = yaml.safe_load(
        output.with_name("weather.meta.yaml").read_text(encoding="utf-8")
    )
    assert result.records == 8760
    assert result.station_id == "412170"
    assert result.station_name == "Abu Dhabi Intl"
    assert result.latitude == pytest.approx(24 + 26 / 60)
    assert result.longitude == pytest.approx(54 + 39 / 60)
    assert rows[0]["timestamp"] == "2025-01-01T00:00:00+04:00"
    assert rows[0]["ghi"] == "100"
    assert rows[0]["dni"] == "200"
    assert rows[0]["dhi"] == "30"
    assert rows[0]["t_ambient"] == "25.0"
    assert rows[0]["wind_speed"] == "2.4"
    assert rows[0]["relative_humidity"] == "87"
    assert rows[0]["qc_flag"] == "GHI=E0;DNI=E0;DHI=E0;T=E0;WS=E0"
    assert rows[-1]["timestamp"] == "2025-12-31T23:00:00+04:00"
    assert metadata["site_timezone"] == "Asia/Dubai"
    assert metadata["timestamp_convention"] == "interval_start"


def test_rejects_invalid_weather_field_at_expected_position_before_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"
    _write_tm2(source, invalid_first_field="ghi")

    with pytest.raises(ValueError, match="invalid ghi field"):
        convert_tm2_to_weather_csv(
            source,
            output,
            calendar_year=2025,
            site_timezone="Asia/Dubai",
        )

    assert not output.exists()
    assert not output.with_name("weather.meta.yaml").exists()


def test_rejects_different_record_width_before_output(tmp_path: Path) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"
    _write_tm2(source, wrong_first_record_width=True)

    with pytest.raises(ValueError, match="different TM2 field layout"):
        convert_tm2_to_weather_csv(
            source,
            output,
            calendar_year=2025,
            site_timezone="Asia/Dubai",
        )

    assert not output.exists()


def test_rejects_hourly_gap_or_reordering_before_output(tmp_path: Path) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"
    _write_tm2(source, first_hour="02")

    with pytest.raises(ValueError, match="not one hour after"):
        convert_tm2_to_weather_csv(
            source,
            output,
            calendar_year=2025,
            site_timezone="Asia/Dubai",
        )

    assert not output.exists()


def test_rejects_missing_weather_sentinel_before_output(tmp_path: Path) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"
    _write_tm2(source, first_ghi="9999")

    with pytest.raises(ValueError, match="missing-value sentinel for ghi"):
        convert_tm2_to_weather_csv(
            source,
            output,
            calendar_year=2025,
            site_timezone="Asia/Dubai",
        )

    assert not output.exists()


def test_rejects_leap_calendar_year(tmp_path: Path) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"

    with pytest.raises(ValueError, match="non-leap calendar year"):
        convert_tm2_to_weather_csv(
            source,
            output,
            calendar_year=2024,
            site_timezone="Asia/Dubai",
        )


@pytest.mark.parametrize("existing_name", ["weather.csv", "weather.meta.yaml"])
def test_refuses_to_overwrite_csv_or_metadata(
    tmp_path: Path, existing_name: str
) -> None:
    source = tmp_path / "station.tm2"
    output = tmp_path / "weather.csv"
    existing_output = tmp_path / existing_name
    existing_output.write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        convert_tm2_to_weather_csv(
            source,
            output,
            calendar_year=2025,
            site_timezone="Asia/Dubai",
        )

    assert existing_output.read_text(encoding="utf-8") == "keep"
