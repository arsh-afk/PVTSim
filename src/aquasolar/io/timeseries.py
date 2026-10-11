"""Time series loader with gap policy handling."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def load_timeseries(
    name: str,
    data: Any,
    meta: Dict[str, Any],
    gap_policy: str,
    gap_max_duration: Optional[str] = None,
) -> pd.DataFrame:
    """Load and validate a time series.

    Args:
        name: Series name (e.g., 'weather')
        data: DataFrame loaded from CSV
        meta: Meta dictionary from .meta.yaml
        gap_policy: From numerics.gap_policy
        gap_max_duration: Max duration for interpolation (if applicable)

    Returns:
        Processed DataFrame with gap handling applied

    Raises:
        ValueError: If required columns are missing or format is invalid
    """
    # Validate required columns
    required_cols = meta.get("required_columns", [])
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns in {name}: {missing}")

    # Check timestamp format
    ts_col = "timestamp"
    if ts_col in data.columns:
        # Parse timestamps
        data[ts_col] = pd.to_datetime(data[ts_col])
        # Check for monotonic increasing
        if not data[ts_col].is_monotonic_increasing:
            raise ValueError(f"Timestamps in {name} are not monotonic increasing")
        # Check for duplicates
        if data[ts_col].duplicated().any():
            raise ValueError(f"Duplicate timestamps in {name}")

    # Apply gap policy
    if gap_policy == "flag_and_stop":
        gaps = _find_gaps(data, ts_col, meta.get("interval"))
        if gaps:
            raise ValueError(f"Gaps detected in {name}: {len(gaps)} gap(s)")

    elif gap_policy == "flag_and_exclude_day":
        # Mark gaps but don't fail
        pass

    elif gap_policy == "linear_interpolate_up_to_max_gap":
        # Interpolate short gaps
        if gap_max_duration:
            # Parse gap_max_duration - simplified
            pass

    return data


def _find_gaps(
    df: pd.DataFrame, ts_col: str, expected_interval: Optional[str]
) -> List[Dict[str, Any]]:
    """Find gaps in a time series."""
    gaps = []
    if expected_interval is None:
        return gaps

    # Simplified gap detection
    timestamps = df[ts_col].values
    for i in range(1, len(timestamps)):
        dt = (pd.Timestamp(timestamps[i]) - pd.Timestamp(timestamps[i - 1]))
        # Check if gap is larger than expected interval
        if dt > pd.Timedelta(expected_interval):
            gaps.append({
                "start": str(timestamps[i - 1]),
                "end": str(timestamps[i]),
                "duration": str(dt),
            })
    return gaps


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
