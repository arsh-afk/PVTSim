"""Convert EnergyPlus Weather (EPW) files to the project weather CSV schema."""

from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path


_LOCATION_COLUMNS = (
    "label",
    "city",
    "region",
    "country",
    "source",
    "station_id",
    "latitude",
    "longitude",
    "time_zone",
    "elevation",
)

_EPW_DATA_COLUMNS = (
    "year",
    "month",
    "day",
    "hour",
    "minute",
    "data_source",
    "dry_bulb_temperature",
    "dew_point_temperature",
    "relative_humidity",
    "atmospheric_station_pressure",
    "extraterrestrial_horizontal_radiation",
    "extraterrestrial_direct_normal_radiation",
    "horizontal_infrared_radiation",
    "global_horizontal_radiation",
    "direct_normal_radiation",
    "diffuse_horizontal_radiation",
    "global_horizontal_illuminance",
    "direct_normal_illuminance",
    "diffuse_horizontal_illuminance",
    "zenith_luminance",
    "wind_direction",
    "wind_speed",
    "total_sky_cover",
    "opaque_sky_cover",
    "visibility",
    "ceiling_height",
    "present_weather_observation",
    "present_weather_codes",
    "precipitable_water",
    "aerosol_optical_depth",
    "snow_depth",
    "days_since_last_snowfall",
    "albedo",
    "liquid_precipitation_depth",
    "liquid_precipitation_quantity",
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


def convert_epw_to_weather_csv(
    epw_path: str | Path,
    csv_path: str | Path,
    *,
    calendar_year: int,
) -> int:
    """Write EPW weather records as a validated project-schema CSV.

    ``calendar_year`` is supplied by the caller because typical-year EPW files
    can combine records whose source years differ. EPW timestamps are
    reconstructed from their hour and minute fields in the supplied year.
    EPW radiation fields are hourly energy per area; for hourly EPW records
    this is numerically equal to the interval-average irradiance in W/m².
    Temperatures remain in the EPW unit, °C. Optional POA irradiance and cloud
    cover are left blank.

    The output is created exclusively, so an existing file is never replaced.
    Returns the number of records written.
    """
    if isinstance(calendar_year, bool) or not isinstance(calendar_year, int):
        raise TypeError("calendar_year must be an integer selected by the caller")

    source_path = Path(epw_path)
    output_path = Path(csv_path)
    if source_path.resolve() == output_path.resolve():
        raise ValueError("EPW source and CSV output must be different files")

    with source_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        try:
            location_row = next(reader)
        except StopIteration as exc:
            raise ValueError(f"EPW file is empty: {source_path}") from exc

        if len(location_row) != len(_LOCATION_COLUMNS):
            raise ValueError("EPW LOCATION header has an unexpected number of fields")
        location = dict(zip(_LOCATION_COLUMNS, location_row, strict=True))
        if location["label"] != "LOCATION":
            raise ValueError("EPW file must start with a LOCATION header")

        try:
            timezone_offset = float(location["time_zone"])
        except ValueError as exc:
            raise ValueError("EPW LOCATION header has an invalid time-zone offset") from exc
        if not math.isfinite(timezone_offset):
            raise ValueError("EPW LOCATION header has a non-finite time-zone offset")
        local_timezone = timezone(timedelta(hours=timezone_offset))

        for header_row in reader:
            if header_row and header_row[0] == "DATA PERIODS":
                break
        else:
            raise ValueError("EPW file has no DATA PERIODS header")

        converted_rows: list[dict[str, str]] = []
        previous_timestamp: datetime | None = None
        for record_number, row in enumerate(reader, start=1):
            if not row:
                continue
            if len(row) != len(_EPW_DATA_COLUMNS):
                raise ValueError(
                    f"EPW data record {record_number} has {len(row)} fields; "
                    f"expected {len(_EPW_DATA_COLUMNS)}"
                )
            data = dict(zip(_EPW_DATA_COLUMNS, row, strict=True))
            minute_text = data["minute"].strip()
            if minute_text not in {"0", "30", "60"}:
                raise ValueError(
                    f"EPW data record {record_number} has an unsupported minute value: "
                    f"{minute_text!r}"
                )

            try:
                int(data["year"])
                month = int(data["month"])
                day = int(data["day"])
                hour = int(data["hour"])
                minute = int(minute_text)
                day_start = datetime(calendar_year, month, day, tzinfo=local_timezone)
                timestamp = day_start + timedelta(hours=hour - 1, minutes=minute)
            except (OverflowError, ValueError) as exc:
                raise ValueError(
                    f"EPW data record {record_number} has an invalid date or hour"
                ) from exc

            day_end = day_start + timedelta(days=1)
            if (
                not day_start <= timestamp <= day_end
                or (timestamp == day_end and str(hour) != "24")
            ):
                raise ValueError(
                    f"EPW data record {record_number} has an hour outside its calendar day"
                )
            if (
                previous_timestamp is not None
                and timestamp - previous_timestamp != timedelta(hours=1)
            ):
                raise ValueError(
                    f"EPW data record {record_number} is not one hour after the preceding record"
                )
            previous_timestamp = timestamp

            ghi = _parse_weather_value(
                data["global_horizontal_radiation"], "GHI", "9999", True, record_number
            )
            ambient_temperature = _parse_weather_value(
                data["dry_bulb_temperature"], "dry-bulb temperature", "99.9", True, record_number
            )
            wind_speed = _parse_weather_value(
                data["wind_speed"], "wind speed", "999", True, record_number
            )

            converted_rows.append(
                {
                    "timestamp": timestamp.isoformat(timespec="seconds"),
                    "ghi": ghi,
                    "dni": _parse_weather_value(
                        data["direct_normal_radiation"], "DNI", "9999", True, record_number
                    ),
                    "dhi": _parse_weather_value(
                        data["diffuse_horizontal_radiation"], "DHI", "9999", True, record_number
                    ),
                    "poa_irradiance": "",
                    "t_ambient": ambient_temperature,
                    "wind_speed": wind_speed,
                    "relative_humidity": _parse_weather_value(
                        data["relative_humidity"], "relative humidity", "999", False, record_number
                    ),
                    "cloud_cover": "",
                    "qc_flag": "",
                }
            )

    if not converted_rows:
        raise ValueError(f"EPW file contains no hourly weather records: {source_path}")

    with output_path.open("x", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=_WEATHER_COLUMNS)
        writer.writeheader()
        writer.writerows(converted_rows)

    return len(converted_rows)


def _parse_weather_value(
    raw_value: str,
    field_name: str,
    missing_sentinel: str,
    required: bool,
    record_number: int,
) -> str:
    """Validate an EPW numeric value and return its normalized CSV form."""
    value = raw_value.strip()
    if not value:
        if required:
            raise ValueError(f"EPW data record {record_number} is missing {field_name}")
        return ""

    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(
            f"EPW data record {record_number} has invalid {field_name}: {value!r}"
        ) from exc

    if not math.isfinite(number):
        raise ValueError(
            f"EPW data record {record_number} has non-finite {field_name}: {value!r}"
        )
    if number == float(missing_sentinel):
        if required:
            raise ValueError(
                f"EPW data record {record_number} uses the missing-value sentinel for {field_name}"
            )
        return ""
    return str(number)
