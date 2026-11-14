"""Command-line converter for common weather source formats."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from aquasolar.io.epw import convert_epw_to_weather_csv
from aquasolar.io.nasa_power import convert_nasa_power_hourly_json
from aquasolar.io.tm2 import convert_tm2_to_weather_csv


_WEATHER_COLUMNS = (
    ("timestamp", "Time in ISO 8601 format with a UTC offset", None, "timestamp"),
    ("ghi", "Global horizontal irradiance", "W/m2", "irradiance"),
    ("dni", "Direct normal irradiance", "W/m2", "irradiance"),
    ("dhi", "Diffuse horizontal irradiance", "W/m2", "irradiance"),
    ("poa_irradiance", "Plane-of-array irradiance, if available", "W/m2", "irradiance"),
    ("t_ambient", "Ambient dry-bulb temperature", "C", "temperature"),
    ("wind_speed", "Wind speed", "m/s", None),
    ("relative_humidity", "Relative humidity, if available", "%", "dimensionless"),
    ("cloud_cover", "Cloud cover, if available", None, None),
    ("qc_flag", "Source quality flag, if available", None, None),
)

_REQUIRED_COLUMNS = {"timestamp", "ghi", "dni", "dhi", "t_ambient", "wind_speed"}


def _metadata(
    output_path: Path,
    source_path: Path,
    source_format: str,
    site_timezone: str,
) -> dict[str, Any]:
    is_nasa = source_format == "nasa-power"
    return {
        "file": output_path.name,
        "description": f"Hourly weather converted from {source_format} data",
        "needed_by_phase": int("1"),
        "encoding": "UTF-8",
        "delimiter": "comma",
        "decimal_separator": "period",
        "header_row": True,
        "data_origin": "other_described_in_notes",
        "provenance_ref": source_path.name,
        "notes": (
            f"Converted from {source_path.name}. Verify source location, "
            "time convention, and units before simulation."
        ),
        "timezone_note": (
            "Source timestamps are UTC."
            if is_nasa
            else "Timestamps use the UTC offset supplied by the source weather file."
        ),
        "site_timezone": site_timezone,
        "timestamp_convention": "interval_start" if is_nasa else "interval_end",
        "interval": "1 hour",
        "interval_note": "Converted records are hourly.",
        "qc_flag_codes": None,
        "qc_flag_note": "No quality flags were supplied by the converter.",
        "columns": [
            {
                "name": name,
                "description": description,
                "required": name in _REQUIRED_COLUMNS,
                "unit": unit,
                "quantity_kind": quantity_kind,
                "sensor_or_source": (
                    "Converted from the selected source format"
                    if name in _REQUIRED_COLUMNS
                    else None
                ),
            }
            for name, description, unit, quantity_kind in _WEATHER_COLUMNS
        ],
    }


def convert_weather_file(
    source: str | Path,
    output: str | Path,
    *,
    source_format: str,
    site_timezone: str,
    calendar_year: int | None = None,
) -> tuple[int, Path]:
    """Convert EPW, TRNSYS TM2, or NASA POWER hourly JSON weather data."""
    source_path = Path(source)
    output_path = Path(output)
    if not isinstance(site_timezone, str) or not site_timezone.strip():
        raise ValueError("site_timezone must be a non-empty IANA timezone name")
    try:
        ZoneInfo(site_timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown IANA site timezone: {site_timezone!r}") from exc

    if source_format == "tm2":
        if calendar_year is None:
            raise ValueError("TM2 conversion requires --calendar-year")
        result = convert_tm2_to_weather_csv(
            source_path,
            output_path,
            calendar_year=calendar_year,
            site_timezone=site_timezone,
        )
        return result.records, result.metadata_path

    if source_format not in {"epw", "nasa-power"}:
        raise ValueError(f"Unsupported weather format: {source_format}")
    if source_format == "epw" and calendar_year is None:
        raise ValueError("EPW conversion requires --calendar-year")
    if source_path.resolve() == output_path.with_name(
        f"{output_path.stem}.meta.yaml"
    ).resolve():
        raise ValueError("Weather source and metadata output must be different files")

    metadata_path = output_path.with_name(f"{output_path.stem}.meta.yaml")
    if metadata_path.exists():
        raise FileExistsError(
            f"Metadata output already exists; choose a unique filename: {metadata_path}"
        )
    metadata_text = yaml.safe_dump(
        _metadata(output_path, source_path, source_format, site_timezone),
        sort_keys=False,
        allow_unicode=True,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if source_format == "epw":
        record_count = convert_epw_to_weather_csv(
            source_path,
            output_path,
            calendar_year=calendar_year,
        )
    else:
        record_count = convert_nasa_power_hourly_json(source_path, output_path)

    metadata_created = False
    try:
        with metadata_path.open("x", encoding="utf-8", newline="") as stream:
            metadata_created = True
            stream.write(metadata_text)
    except OSError:
        output_path.unlink(missing_ok=True)
        if metadata_created:
            metadata_path.unlink(missing_ok=True)
        raise
    return record_count, metadata_path


def main(argv: list[str] | None = None) -> int:
    """Run the weather conversion command."""
    parser = argparse.ArgumentParser(
        description="Convert supported hourly weather data to AquaSolar CSV."
    )
    parser.add_argument(
        "--format",
        required=True,
        choices=("epw", "tm2", "nasa-power"),
        help="Source format: EPW, TRNSYS TMY2/TM2, or NASA POWER hourly JSON",
    )
    parser.add_argument("source", help="Weather source file")
    parser.add_argument("output", help="Destination weather CSV")
    parser.add_argument(
        "--calendar-year",
        type=int,
        help="Calendar year used to reconstruct EPW or TM2 timestamps",
    )
    parser.add_argument(
        "--site-timezone",
        required=True,
        help="IANA timezone for the modeled site, such as Asia/Dubai",
    )
    args = parser.parse_args(argv)

    try:
        records, metadata_path = convert_weather_file(
            args.source,
            args.output,
            source_format=args.format,
            site_timezone=args.site_timezone,
            calendar_year=args.calendar_year,
        )
    except (OSError, ImportError, TypeError, ValueError) as exc:
        print(f"Weather conversion failed: {exc}", file=sys.stderr)
        return int("1")

    print(f"Converted {records} hourly weather rows.")
    print(f"Weather CSV: {Path(args.output)}")
    print(f"Metadata: {metadata_path}")
    return int("0")


if __name__ == "__main__":
    raise SystemExit(main())
