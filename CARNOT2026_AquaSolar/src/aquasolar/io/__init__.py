"""IO module for AquaSolar Living.

Handles loading time series, tables, and generating quality reports.
"""

from __future__ import annotations

from .timeseries import load_timeseries, validate_timeseries
from .tables import load_table
from .quality_report import write_quality_report, generate_all_quality_reports
from .species import validate_species_registry
from .epw import convert_epw_to_weather_csv
from .nasa_power import convert_nasa_power_hourly_json
from .tm2 import convert_tm2_to_weather_csv

__all__ = [
    "load_timeseries",
    "validate_timeseries",
    "load_table",
    "write_quality_report",
    "generate_all_quality_reports",
    "validate_species_registry",
    "convert_epw_to_weather_csv",
    "convert_nasa_power_hourly_json",
    "convert_tm2_to_weather_csv",
]
