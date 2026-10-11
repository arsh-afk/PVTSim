"""IO module for AquaSolar Living.

Handles loading time series, tables, and generating quality reports.
"""

from __future__ import annotations

from .timeseries import load_timeseries
from .tables import load_table
from .quality_report import write_quality_report

__all__ = ["load_timeseries", "load_table", "write_quality_report"]
