"""Solar geometry module for AquaSolar Living.

Per P3-1: Solar position from site, timestamp and time zone.
Uses pvlib for solar position calculations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd


def solar_position(
    timestamp: pd.Timestamp,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
    pressure: Optional[float] = None,
) -> Dict[str, float]:
    """Calculate solar position angles.

    Args:
        timestamp: UTC timestamp
        latitude: Site latitude in degrees
        longitude: Site longitude in degrees
        elevation: Site elevation in meters
        pressure: Atmospheric pressure in Pa (optional, computed from elevation)

    Returns:
        Dict with solar_zenith, solar_azimuth, equation_of_time, solar_declination
    """
    try:
        from pvlib.positiontrace import get_solarposition
    except ImportError:
        # Fallback to simple approximation
        return _simple_solar_position(timestamp, latitude, longitude, elevation)

    # Compute pressure from elevation if not provided
    if pressure is None:
        pressure = 101325 * (1 - 2.2557e-5 * elevation) ** 5.2559  # ISA atmosphere

    # Calculate solar position
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
        "solar_declination": float(solpos["declination"]),
    }


def _simple_solar_position(
    timestamp: pd.Timestamp,
    latitude: float,
    longitude: float,
    elevation: float = 0.0,
) -> Dict[str, float]:
    """Simple solar position approximation.

    Uses basic astronomical formulas.
    """
    import math

    # Julian day calculation
    utc_dt = timestamp.to_pydatetime()
    year, month, day = utc_dt.year, utc_dt.month, utc_dt.day
    hour, minute, second = utc_dt.hour, utc_dt.minute, utc_dt.second

    # Approximate Julian day
    if month <= 2:
        year -= 1
        month += 12
    A = int(year / 100)
    B = 2 - A + int(A / 4)
    JD = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + \
         (hour + minute / 60 + second / 3600) / 24 - B - 1524.5

    # Solar calculations
    T = (JD - 2451545.0) / 36525.0
    G = 357.529 + 35999.050 * T  # Sun's mean anomaly
    L = 280.466 + 36000.770 * T  # Sun's mean longitude
    G_rad = math.radians(G)
    L_rad = math.radians(L)

    # Equation of center
    C = (1.9148 - 0.0048 * T) * math.sin(G_rad) + \
        0.0200 * math.sin(2 * G_rad)
    λ = L + C  # Sun's ecliptic longitude

    # Obliquity of ecliptic
    ε = 23.439 - 0.0000004 * T

    # Solar declination
    δ = math.asin(math.sin(math.radians(ε)) * math.sin(math.radians(λ)))

    # Hour angle
    EoT = 4 * (L_rad - math.modf((L_rad + math.pi) / (2 * math.pi))[0] * 2 * math.pi - G_rad) / math.pi * 60
    HA = (longitude + (EoT + 4 * longitude) / 60) * 15 - 180

    # Solar zenith
    sin_zenith = math.sin(math.radians(latitude)) * math.sin(δ) + \
                 math.cos(math.radians(latitude)) * math.cos(δ) * math.cos(math.radians(HA))
    zenith = math.degrees(math.asin(sin_zenith))

    # Solar azimuth
    cos_azimuth = (math.sin(math.radians(latitude)) * math.cos(math.radians(zenith)) -
                   math.sin(δ)) / (math.cos(math.radians(latitude)) * math.sin(math.radians(zenith)))
    azimuth = math.degrees(math.acos(cos_azimuth))
    if HA > 0:
        azimuth = 360 - azimuth

    return {
        "solar_zenith": zenith,
        "solar_azimuth": azimuth,
        "equation_of_time": EoT,
        "solar_declination": math.degrees(δ),
    }


def calculate_incident_angle(
    solar_zenith: float,
    solar_azimuth: float,
    collector_tilt: float,
    collector_azimuth: float,
    azimuth_convention: str = "south_zero_east_negative",
) -> float:
    """Calculate angle of incidence on tilted surface.

    Args:
        solar_zenith: Solar zenith angle in degrees
        solar_azimuth: Solar azimuth angle in degrees
        collector_tilt: Collector tilt from horizontal in degrees
        collector_azimuth: Collector azimuth in degrees
        azimuth_convention: Convention for azimuth angles

    Returns:
        Angle of incidence in degrees
    """
    import math

    # Convert to radians
    θ = math.radians(solar_zenith)
    γ = math.radians(solar_azimuth)
    β = math.radians(collector_tilt)
    ψ = math.radians(collector_azimuth)

    # Calculate cosine of incidence angle
    cos_θi = (math.sin(θ) * math.cos(β) +
              math.cos(θ) * math.sin(β) * math.cos(γ - ψ))

    # Clamp to [-1, 1] to avoid numerical issues
    cos_θi = max(-1.0, min(1.0, cos_θi))

    return math.degrees(math.acos(cos_θi))


def transposition(
    ghi: float,
    dni: Optional[float] = None,
    dhi: Optional[float] = None,
    solar_zenith: Optional[float] = None,
    solar_azimuth: Optional[float] = None,
    collector_tilt: Optional[float] = None,
    collector_azimuth: Optional[float] = None,
    ground_albedo: float = 0.2,
    model: str = "perez",
) -> Dict[str, float]:
    """Transpose horizontal irradiance to plane-of-array.

    Args:
        ghi: Global horizontal irradiance in W/m²
        dni: Direct normal irradiance in W/m² (optional if solar positions provided)
        dhi: Diffuse horizontal irradiance in W/m² (optional)
        solar_zenith: Solar zenith angle (optional if dni/dhi provided)
        solar_azimuth: Solar azimuth angle (optional)
        collector_tilt: Collector tilt from horizontal
        collector_azimuth: Collector azimuth
        ground_albedo: Ground reflectance
        model: Transposition model ("perez", "isotropic", "haydavies")

    Returns:
        Dict with poa_direct, poa_diffuse, poa_global
    """
    try:
        from pvlib.irradiance import get_total_irradiance, perez, isotropic, haydavies
    except ImportError:
        # Fallback: simple isotropic model
        if dhi is None or solar_zenith is None:
            raise ValueError("dhi and solar_zenith required for fallback model")
        dni = ghi - dhi
        zenith_rad = math.radians(solar_zenith)
        tilt_rad = math.radians(collector_tilt or 0)

        # Isotropic diffuse
        poa_diffuse = dhi * ((1 + math.cos(tilt_rad)) / 2)
        # Direct
        if solar_zenith < 88:
            poa_direct = dni * math.cos(math.radians(
                calculate_incident_angle(solar_zenith, solar_azimuth or 0,
                                         collector_tilt or 0, collector_azimuth or 0)
            ))
        else:
            poa_direct = 0
        # Ground reflected
        poa_ground = ghi * ground_albedo * ((1 - math.cos(tilt_rad)) / 2)

        return {
            "poa_direct": max(0, poa_direct),
            "poa_diffuse": poa_diffuse,
            "poa_global": poa_direct + poa_diffuse + poa_ground,
        }

    # Use pvlib models
    if model == "perez":
        poa = perez(ghi, dni, dhi, solar_zenith, solar_azimuth,
                    collector_tilt, collector_azimuth, ground_albedo)
    elif model == "isotropic":
        poa = isotropic(ghi, dhi, solar_zenith, collector_tilt)
    elif model == "haydavies":
        poa = haydavies(ghi, dni, dhi, solar_zenith, solar_azimuth,
                        collector_tilt, collector_azimuth, ground_albedo)
    else:
        raise ValueError(f"Unknown transposition model: {model}")

    return {
        "poa_direct": float(poa["direct"]),
        "poa_diffuse": float(poa["diffuse"]),
        "poa_global": float(poa["poa_total"]),
    }


import math
