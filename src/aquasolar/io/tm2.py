"""Convert the supported fixed-width TRNSYS TMY2 weather file to project CSV."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml


_RECORD_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("year", "2", "value"),
    ("month", "2", "value"),
    ("day", "2", "value"),
    ("hour", "2", "value"),
    ("etr", "4", "value"),
    ("etrn", "4", "value"),
    ("ghi", "4", "value"),
    ("ghi_source", "1", "flag"),
    ("ghi_uncertainty", "1", "value"),
    ("dni", "4", "value"),
    ("dni_source", "1", "flag"),
    ("dni_uncertainty", "1", "value"),
    ("dhi", "4", "value"),
    ("dhi_source", "1", "flag"),
    ("dhi_uncertainty", "1", "value"),
    ("ghillum", "4", "value"),
    ("ghillum_source", "1", "flag"),
    ("ghillum_uncertainty", "1", "value"),
    ("dnillum", "4", "value"),
    ("dnillum_source", "1", "flag"),
    ("dnillum_uncertainty", "1", "value"),
    ("dhillum", "4", "value"),
    ("dhillum_source", "1", "flag"),
    ("dhillum_uncertainty", "1", "value"),
    ("zenithlum", "4", "value"),
    ("zenithlum_source", "1", "flag"),
    ("zenithlum_uncertainty", "1", "value"),
    ("total_cloud", "2", "value"),
    ("total_cloud_source", "1", "flag"),
    ("total_cloud_uncertainty", "1", "value"),
    ("opaque_cloud", "2", "value"),
    ("opaque_cloud_source", "1", "flag"),
    ("opaque_cloud_uncertainty", "1", "value"),
    ("dry_bulb", "4", "value"),
    ("dry_bulb_source", "1", "flag"),
    ("dry_bulb_uncertainty", "1", "value"),
    ("dew_point", "4", "value"),
    ("dew_point_source", "1", "flag"),
    ("dew_point_uncertainty", "1", "value"),
    ("relative_humidity", "3", "value"),
    ("relative_humidity_source", "1", "flag"),
    ("relative_humidity_uncertainty", "1", "value"),
    ("pressure", "4", "value"),
    ("pressure_source", "1", "flag"),
    ("pressure_uncertainty", "1", "value"),
    ("wind_direction", "3", "value"),
    ("wind_direction_source", "1", "flag"),
    ("wind_direction_uncertainty", "1", "value"),
    ("wind_speed", "3", "value"),
    ("wind_speed_source", "1", "flag"),
    ("wind_speed_uncertainty", "1", "value"),
    ("visibility", "4", "value"),
    ("visibility_source", "1", "flag"),
    ("visibility_uncertainty", "1", "value"),
    ("ceiling_height", "5", "value"),
    ("ceiling_height_source", "1", "flag"),
    ("ceiling_height_uncertainty", "1", "value"),
    ("present_weather", "10", "opaque"),
    ("precipitable_water", "3", "value"),
    ("precipitable_water_source", "1", "flag"),
    ("precipitable_water_uncertainty", "1", "value"),
    ("aerosol_optical_depth", "3", "value"),
    ("aerosol_optical_depth_source", "1", "flag"),
    ("aerosol_optical_depth_uncertainty", "1", "value"),
    ("snow_depth", "3", "value"),
    ("snow_depth_source", "1", "flag"),
    ("snow_depth_uncertainty", "1", "value"),
    ("days_since_snow", "2", "value"),
    ("days_since_snow_source", "1", "flag"),
    ("days_since_snow_uncertainty", "1", "value"),
)

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

_HEADER_PATTERN = re.compile(
    r"^\s*(?P<station>\d{6})(?P<name>.*?)\s+"
    r"(?P<offset>[+-]?\d+)\s+(?P<ns>[NS])\s+"
    r"(?P<lat_deg>\d{1,2})\s+(?P<lat_min>\d{1,2})\s+"
    r"(?P<ew>[EW])\s+(?P<lon_deg>\d{1,3})\s+"
    r"(?P<lon_min>\d{1,2})\s+(?P<elevation>-?\d+(?:\.\d+)?)\s*$"
)


@dataclass(frozen=True)
class TM2Conversion:
    """Station information reported after a successful TM2 conversion."""

    records: int
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    elevation_m: float
    utc_offset_hours: int
    source_year: int
    csv_path: Path
    metadata_path: Path


def _read_station_header(line: str, source_path: Path) -> dict[str, Any]:
    match = _HEADER_PATTERN.fullmatch(line)
    if match is None:
        raise ValueError(
            f"Unsupported TM2 station header in {source_path.name}; "
            "expected station id/name, UTC offset, latitude, longitude, and elevation."
        )

    offset = int(match.group("offset"))
    latitude_degrees = int(match.group("lat_deg"))
    latitude_minutes = int(match.group("lat_min"))
    longitude_degrees = int(match.group("lon_deg"))
    longitude_minutes = int(match.group("lon_min"))
    if abs(offset) > int("14"):
        raise ValueError("TM2 station UTC offset must be within -14 to +14 hours")
    if latitude_minutes >= int("60") or longitude_minutes >= int("60"):
        raise ValueError("TM2 station coordinates have invalid arc minutes")
    if (
        latitude_degrees > int("90")
        or longitude_degrees > int("180")
        or (latitude_degrees == int("90") and latitude_minutes > 0)
        or (longitude_degrees == int("180") and longitude_minutes > 0)
    ):
        raise ValueError("TM2 station coordinates are outside valid bounds")

    latitude = latitude_degrees + latitude_minutes / float("60.0")
    longitude = longitude_degrees + longitude_minutes / float("60.0")
    if match.group("ns") == "S":
        latitude = -latitude
    if match.group("ew") == "W":
        longitude = -longitude

    return {
        "station_id": match.group("station"),
        "station_name": match.group("name").strip(),
        "utc_offset_hours": offset,
        "latitude": latitude,
        "longitude": longitude,
        "elevation_m": float(match.group("elevation")),
    }


def _parse_record(line: str, record_number: int) -> dict[str, str]:
    expected_length = int("142")
    if len(line) != expected_length or not line.startswith(" "):
        raise ValueError(
            f"TM2 record {record_number} has {len(line)} characters; "
            f"expected {expected_length} including its leading space. "
            "The file may use a different TM2 field layout."
        )

    payload = line[1:]
    fields: dict[str, str] = {}
    cursor = 0
    for name, width_text, field_type in _RECORD_FIELDS:
        width = int(width_text)
        value = payload[cursor : cursor + width]
        cursor += width
        if field_type == "flag":
            if not all(char.isalpha() or char == "?" for char in value):
                raise ValueError(
                    f"TM2 record {record_number} has an invalid source flag "
                    f"for {name}: {value!r}"
                )
        elif field_type == "value":
            if not value.strip().lstrip("+-").isdigit():
                raise ValueError(
                    f"TM2 record {record_number} has an invalid {name} field: {value!r}"
                )
        fields[name] = value.strip()

    if cursor != len(payload):
        raise ValueError(
            f"TM2 record {record_number} does not match the supported field layout"
        )
    return fields


def _required_value(
    fields: dict[str, str],
    field: str,
    sentinel: str,
    record_number: int,
) -> int:
    value = int(fields[field])
    if value == int(sentinel):
        raise ValueError(
            f"TM2 record {record_number} uses the missing-value sentinel for {field}"
        )
    return value


def _weather_metadata(
    csv_path: Path,
    source_path: Path,
    station: dict[str, Any],
    site_timezone: str,
    calendar_year: int,
) -> dict[str, Any]:
    source_flags = (
        "GHI=source+uncertainty;DNI=source+uncertainty;"
        "DHI=source+uncertainty;dry_bulb=source+uncertainty;"
        "wind_speed=source+uncertainty"
    )
    offset = station["utc_offset_hours"]
    return {
        "file": csv_path.name,
        "description": "Hourly TMY2 weather converted from a TRNSYS TM2 file",
        "needed_by_phase": 1,
        "encoding": "UTF-8",
        "delimiter": "comma",
        "decimal_separator": "period",
        "header_row": True,
        "data_origin": "typical_year",
        "provenance_ref": source_path.name,
        "notes": (
            f"Converted from {source_path.name}; station "
            f"{station['station_id']} {station['station_name']} "
            f"({station['latitude']:.5f}, {station['longitude']:.5f}, "
            f"{station['elevation_m']:g} m). The original TM2 source and "
            "uncertainty flags for required weather values are retained in qc_flag."
        ),
        "timezone_note": (
            f"TM2 station UTC offset is {offset:+d} hours. Timestamps retain "
            "this fixed source offset; the IANA timezone is recorded separately."
        ),
        "site_timezone": site_timezone,
        "timestamp_convention": "interval_start",
        "interval": "1 hour",
        "interval_note": (
            f"Hourly TMY2 records mapped to calendar year {calendar_year}; "
            "record hours 01-24 are interpreted as intervals starting at "
            "00:00-23:00 local standard time."
        ),
        "qc_flag_codes": None,
        "qc_flag_note": f"TMY2 source flags retained as {source_flags}.",
        "columns": [
            {
                "name": "timestamp",
                "description": "Hourly interval start, ISO 8601 with UTC offset",
                "required": True,
                "unit": None,
                "quantity_kind": "timestamp",
                "sensor_or_source": "TM2 year/month/day/hour fields",
            },
            {
                "name": "ghi",
                "description": "Global horizontal irradiance",
                "required": True,
                "unit": "W/m2",
                "quantity_kind": "irradiance",
                "sensor_or_source": "TM2 GHI, hourly Wh/m2",
            },
            {
                "name": "dni",
                "description": "Direct normal irradiance",
                "required": True,
                "unit": "W/m2",
                "quantity_kind": "irradiance",
                "sensor_or_source": "TM2 DNI, hourly Wh/m2",
            },
            {
                "name": "dhi",
                "description": "Diffuse horizontal irradiance",
                "required": True,
                "unit": "W/m2",
                "quantity_kind": "irradiance",
                "sensor_or_source": "TM2 DHI, hourly Wh/m2",
            },
            {
                "name": "poa_irradiance",
                "description": "Not supplied by TM2",
                "required": False,
                "unit": "W/m2",
                "quantity_kind": "irradiance",
                "sensor_or_source": "Not supplied; left blank",
            },
            {
                "name": "t_ambient",
                "description": "Ambient dry-bulb temperature",
                "required": True,
                "unit": "C",
                "quantity_kind": "temperature",
                "sensor_or_source": "TM2 dry bulb in tenths of degrees Celsius",
            },
            {
                "name": "wind_speed",
                "description": "Wind speed",
                "required": True,
                "unit": "m/s",
                "quantity_kind": None,
                "sensor_or_source": "TM2 wind speed in tenths of m/s",
            },
            {
                "name": "relative_humidity",
                "description": "Relative humidity",
                "required": False,
                "unit": "%",
                "quantity_kind": "dimensionless",
                "sensor_or_source": "TM2 relative humidity",
            },
            {
                "name": "cloud_cover",
                "description": "Not supplied to this schema",
                "required": False,
                "unit": None,
                "quantity_kind": None,
                "sensor_or_source": None,
            },
            {
                "name": "qc_flag",
                "description": "TM2 source and uncertainty flags",
                "required": False,
                "unit": None,
                "quantity_kind": None,
                "sensor_or_source": "TM2 required-weather field flags",
            },
        ],
    }


def convert_tm2_to_weather_csv(
    tm2_path: str | Path,
    csv_path: str | Path,
    *,
    calendar_year: int,
    site_timezone: str,
) -> TM2Conversion:
    """Validate a fixed-width TRNSYS TMY2 file and write project weather inputs.

    The accepted input is the 142-character, leading-space TMY2 record layout.
    Input records are fully parsed and validated before the CSV or metadata
    sidecar is created. Existing output files are never overwritten.
    """
    if isinstance(calendar_year, bool) or not isinstance(calendar_year, int):
        raise TypeError("calendar_year must be an integer selected by the caller")
    if (datetime(calendar_year + 1, 1, 1) - datetime(calendar_year, 1, 1)).days != int("365"):
        raise ValueError("TM2 conversion requires a non-leap calendar year")
    if not site_timezone:
        raise ValueError("site_timezone must be an IANA timezone name")
    try:
        ZoneInfo(site_timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown IANA site timezone: {site_timezone!r}") from exc

    source_path = Path(tm2_path)
    output_path = Path(csv_path)
    metadata_path = output_path.with_name(
        f"{output_path.stem}.meta.yaml"
    )
    if source_path.resolve() in {output_path.resolve(), metadata_path.resolve()}:
        raise ValueError("TM2 source and output files must be different")
    if output_path.exists() or metadata_path.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing weather CSV or metadata file"
        )

    with source_path.open(encoding="ascii", newline="") as source:
        header_line = source.readline().rstrip("\r\n")
        if not header_line:
            raise ValueError(f"TM2 file is empty: {source_path}")
        station = _read_station_header(header_line, source_path)
        local_timezone = timezone(
            timedelta(hours=station["utc_offset_hours"])
        )
        rows: list[dict[str, str]] = []
        timestamps: list[datetime] = []
        source_year: str | None = None

        for record_number, raw_line in enumerate(source, start=1):
            line = raw_line.rstrip("\r\n")
            fields = _parse_record(line, record_number)
            if source_year is None:
                source_year = fields["year"]
            elif fields["year"] != source_year:
                raise ValueError(
                    f"TM2 record {record_number} changes source year "
                    f"from {source_year} to {fields['year']}"
                )

            try:
                month = int(fields["month"])
                day = int(fields["day"])
                hour = int(fields["hour"])
                if hour < 1 or hour > int("24"):
                    raise ValueError("hour must be in the range 01-24")
                timestamp = datetime(
                    calendar_year,
                    month,
                    day,
                    hour=hour - 1,
                    tzinfo=local_timezone,
                )
            except ValueError as exc:
                raise ValueError(
                    f"TM2 record {record_number} has an invalid date/hour: {exc}"
                ) from exc
            if timestamps and timestamp - timestamps[-1] != timedelta(hours=1):
                raise ValueError(
                    f"TM2 record {record_number} is not one hour after the "
                    "preceding record"
                )

            ghi = _required_value(fields, "ghi", "9999", record_number)
            dni = _required_value(fields, "dni", "9999", record_number)
            dhi = _required_value(fields, "dhi", "9999", record_number)
            dry_bulb = _required_value(fields, "dry_bulb", "9999", record_number)
            wind_speed = _required_value(fields, "wind_speed", "999", record_number)
            relative_humidity = _required_value(
                fields, "relative_humidity", "999", record_number
            )
            if min(ghi, dni, dhi, wind_speed) < 0:
                raise ValueError(
                    f"TM2 record {record_number} has negative irradiance or wind speed"
                )
            if relative_humidity < 0 or relative_humidity > int("100"):
                raise ValueError(
                    f"TM2 record {record_number} has relative humidity outside 0-100%"
                )

            timestamps.append(timestamp)
            rows.append(
                {
                    "timestamp": timestamp.isoformat(timespec="seconds"),
                    "ghi": str(ghi),
                    "dni": str(dni),
                    "dhi": str(dhi),
                    "poa_irradiance": "",
                    "t_ambient": str(dry_bulb / float("10.0")),
                    "wind_speed": str(wind_speed / float("10.0")),
                    "relative_humidity": str(relative_humidity),
                    "cloud_cover": "",
                    "qc_flag": (
                        f"GHI={fields['ghi_source']}{fields['ghi_uncertainty']};"
                        f"DNI={fields['dni_source']}{fields['dni_uncertainty']};"
                        f"DHI={fields['dhi_source']}{fields['dhi_uncertainty']};"
                        f"T={fields['dry_bulb_source']}{fields['dry_bulb_uncertainty']};"
                        f"WS={fields['wind_speed_source']}"
                        f"{fields['wind_speed_uncertainty']}"
                    ),
                }
            )

    expected_records = int("8760")
    if len(rows) != expected_records:
        raise ValueError(
            f"TM2 file has {len(rows)} records; expected {expected_records} "
            "hourly records for a typical non-leap year"
        )
    metadata = _weather_metadata(
        output_path, source_path, station, site_timezone, calendar_year
    )
    metadata_text = yaml.safe_dump(
        metadata, sort_keys=False, allow_unicode=True
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    csv_created = False
    metadata_created = False
    try:
        with output_path.open("x", encoding="utf-8", newline="") as output:
            csv_created = True
            writer = csv.DictWriter(output, fieldnames=_WEATHER_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        with metadata_path.open("x", encoding="utf-8", newline="") as metadata_file:
            metadata_created = True
            metadata_file.write(metadata_text)
    except OSError:
        if csv_created:
            output_path.unlink(missing_ok=True)
        if metadata_created:
            metadata_path.unlink(missing_ok=True)
        raise

    return TM2Conversion(
        records=len(rows),
        station_id=station["station_id"],
        station_name=station["station_name"],
        latitude=station["latitude"],
        longitude=station["longitude"],
        elevation_m=station["elevation_m"],
        utc_offset_hours=station["utc_offset_hours"],
        source_year=int(source_year) if source_year is not None else 0,
        csv_path=output_path,
        metadata_path=metadata_path,
    )
