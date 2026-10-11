"""Solar geometry module for AquaSolar Living.

Per P3-1: Solar position from site, timestamp and time zone.
Uses pvlib for all solar position calculations.
All physical constants loaded from registry or unit library.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd


def solar_position(
    timestamp: pd.Timestamp,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
    pressure: Optional[float] = None,
) -> Dict[str, float]:
    """Calculate solar position angles using pvlib.

    Args:
        timestamp: UTC timestamp
        latitude: Site latitude in degrees
        longitude: Site longitude in degrees
        elevation: Site elevation in meters
        pressure: Atmospheric pressure in Pa (optional)

    Returns:
        Dict with solar_zenith, solar_azimuth, equation_of_time
    """
    try:
        from pvlib.solarposition import ephemeralsunsolarposition
    except ImportError:
        from pvlib.positiontrace import get_solarposition
        solpos = get_solarposition(
            timestamp,
            latitude,
            longitude,
            elevation,
            pressure=pressure,
        )
        return {
            "solar_zenith": float(solpos["apparent_zenith"]),
            "solar_azimuth": float(solpos["azimuth"]),
            "equation_of_time": float(solpos["equation_of_time"]),
        }

    # Use pvlib solar position
    solpos = ephemeralsunsolarposition(
        method="nrel",
        pressure=pressure,
        temperature=None,
        zenith=timestamp,
        latitude=latitude,
        longitude=longitude,
        elevation=elevation,
    )
    return {
        "solar_zenith": float(solpos["apparent_zenith"]),
        "solar_azimuth": float(solpos["azimuth"]),
        "equation_of_time": float(solpos["equation_of_time"]),
    }


def calculate_incident_angle(
    solar_zenith: float,
    solar_azimuth: float,
    collector_tilt: float,
    collector_azimuth: float,
) -> float:
    """Calculate angle of incidence on tilted surface.

    Args:
        solar_zenith: Solar zenith angle in degrees
        solar_azimuth: Solar azimuth angle in degrees
        collector_tilt: Collector tilt from horizontal in degrees
        collector_azimuth: Collector azimuth in degrees

    Returns:
        Angle of incidence in degrees
    """
    import math

    # Convert to radians
    theta = math.radians(solar_zenith)
    gamma = math.radians(solar_azimuth)
    beta = math.radians(collector_tilt)
    psi = math.radians(collector_azimuth)

    # Calculate cosine of incidence angle
    cos_thetai = (math.sin(theta) * math.cos(beta) +
                  math.cos(theta) * math.sin(beta) * math.cos(gamma - psi))

    # Clamp to [-1, 1]
    cos_thetai = max(-1.0, min(1.0, cos_thetai))

    return math.degrees(math.acos(cos_thetai))
