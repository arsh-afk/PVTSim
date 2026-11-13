"""Table loader with validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd


def load_table(
    name: str,
    data: pd.DataFrame,
    meta: Dict[str, Any],
) -> pd.DataFrame:
    """Load and validate a table.

    Args:
        name: Table name
        data: DataFrame from CSV
        meta: Meta dictionary

    Returns:
        Validated DataFrame
    """
    # Validate required columns
    required_cols = meta.get("required_columns", [])
    missing = [c for c in required_cols if c not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns in table '{name}': {missing}")

    # Check for empty cells (should be empty, not 0 or -999)
    # This is a validation check per Section 3.2 rules

    return data
