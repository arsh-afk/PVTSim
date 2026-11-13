"""Convert NASA POWER hourly point JSON to the project weather CSV schema."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


_POWER_TO_WEATHER = {
    "ALLSKY_SFC_SW_DWN": "ghi",
    "ALLSKY_SFC_SW_DNI": "dni",
    "ALLSKY_SFC_SW_DIFF": "dhi",
    "T2M": "t_ambient",
    "WS10M": "wind_speed",
    "RH2M": "relative_humidity",
}

_WEATHER_COLUMNS = (
    "timestamp",
    "ghi",
    "dni",
    "dhi",
    "poa_irradiance",
    "t_ambient",
    "wind_speed",
    "relative_humidity",
    "cloud_cover",
    "qc_flag",
)

_EXPECTED_UNITS = {
    "ALLSKY_SFC_SW_DWN": "Wh/m^2",
    "ALLSKY_SFC_SW_DNI": "Wh/m^2",
    "ALLSKY_SFC_SW_DIFF": "Wh/m^2",
    "T2M": "C",
    "WS10M": "m/s",
    "RH2M": "%",
}


def convert_nasa_power_hourly_json(
    json_path: str | Path,
    csv_path: str | Path,
) -> int:
    """Convert a NASA POWER hourly UTC point JSON file to weather CSV.

    The three solar-radiation series are hourly energies in Wh/m². Since each
    source interval is one hour, their numeric values are written as hourly
    average irradiance in W/m². Missing/non-finite required values and
    misaligned or non-consecutive hourly timestamps are rejected. POA
    irradiance, cloud cover, and QC flags remain blank because they are not
    supplied by this NASA request.

    The destination is created exclusively; an existing file is never
    overwritten. Returns the number of hourly records written.
    """
    source_path = Path(json_path)
    output_path = Path(csv_path)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("JSON source and CSV output must be different files")

    with source_path.open(encoding="utf-8") as source:
        payload: dict[str, Any] = json.load(source)

    header = payload.get("header", {})
    if header.get("time_standard") != "UTC":
        raise ValueError("NASA POWER JSON must use time_standard=UTC")

    parameters = payload.get("parameters", {})
    series = payload.get("properties", {}).get("parameter", {})
    for parameter, expected_unit in _EXPECTED_UNITS.items():
        if parameter not in series:
            raise ValueError(f"NASA POWER JSON is missing parameter {parameter}")
        if parameters.get(parameter, {}).get("units") != expected_unit:
            raise ValueError(
                f"NASA POWER parameter {parameter} must use units {expected_unit!r}"
            )

    timestamp_sets = [
        set(series[parameter])
        for parameter in _POWER_TO_WEATHER
    ]
    timestamps = timestamp_sets[0]
    if not timestamps:
        raise ValueError("NASA POWER JSON contains no hourly records")
    if any(item != timestamps for item in timestamp_sets[1:]):
        raise ValueError("NASA POWER weather parameter timestamps do not align")

    parsed_timestamps: list[tuple[str, datetime]] = []
    for timestamp_text in sorted(timestamps):
        try:
            timestamp = datetime.strptime(timestamp_text, "%Y%m%d%H").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise ValueError(
                f"Invalid NASA POWER hourly timestamp: {timestamp_text!r}"
            ) from exc
        parsed_timestamps.append((timestamp_text, timestamp))

    for previous, current in zip(parsed_timestamps, parsed_timestamps[1:]):
        if current[1] - previous[1] != timedelta(hours=1):
            raise ValueError(
                f"NASA POWER timestamps are not consecutive hourly records: "
                f"{previous[0]} then {current[0]}"
            )

    missing_value = header.get("fill_value")
    if missing_value is None:
        raise ValueError("NASA POWER JSON is missing its fill_value metadata")

    rows: list[dict[str, str]] = []
    for timestamp_text, timestamp in parsed_timestamps:
        row = {
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "poa_irradiance": "",
            "cloud_cover": "",
            "qc_flag": "",
        }
        for parameter, weather_column in _POWER_TO_WEATHER.items():
            raw_value = series[parameter][timestamp_text]
            try:
                value = float(raw_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"NASA POWER value {parameter} at {timestamp_text} is not numeric"
                ) from exc
            if not math.isfinite(value) or value == float(missing_value):
                raise ValueError(
                    f"NASA POWER value {parameter} at {timestamp_text} is missing "
                    "or non-finite"
                )
            row[weather_column] = str(value)
        rows.append(row)

    with output_path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=_WEATHER_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)
