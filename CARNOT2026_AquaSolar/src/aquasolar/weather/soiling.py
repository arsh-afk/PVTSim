"""Soiling loss module.

Per P3-10: Soiling decay model based on rainfall and time since last rain.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def soiling_factor(
    days_since_rain: int,
    max_soiling: float,
    decay_rate: float,
    rainfall_factor: float = 0.0,
    last_rainfall: float = 0.0,
) -> float:
    """Calculate soiling factor from rain history.

    Args:
        days_since_rain: Days since last rainfall
        max_soiling: Maximum possible soiling loss (0-1)
        decay_rate: Daily soiling accumulation rate
        rainfall_factor: Effectiveness of rain in removing soiling
        last_rainfall: Last rainfall amount (mm)

    Returns:
        Soiling factor (0-1, where 1 = no soiling)
    """
    # Calculate soiling based on days without rain
    soil_level = max_soiling * (1.0 - (1.0 - decay_rate) ** days_since_rain)

    # Apply rain cleaning effect
    if last_rainfall > 0:
        rain_effect = rainfall_factor * (1.0 - (1.0 - decay_rate) ** days_since_rain)
        soil_level = max(0.0, soil_level - rain_effect)

    # Convert to factor (1 - soil_level)
    return max(0.0, min(1.0, 1.0 - soil_level))


def soiling_factor_series(
    rainfall_series: list,
    days_since_rain_series: list,
    max_soiling: float,
    decay_rate: float,
    rainfall_factor: float = 0.0,
) -> list:
    """Calculate soiling factor for a time series."""
    results = []
    current_soil = 0.0
    for rainfall, days in zip(rainfall_series, days_since_rain_series):
        factor = soiling_factor(days, max_soiling, decay_rate, rainfall_factor, rainfall)
        results.append(factor)
    return results
