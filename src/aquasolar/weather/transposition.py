"""Irradiance transposition module."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .solar_geometry import calculate_incident_angle, transposition as geo_transposition


def get_poa_irradiance(
    ghi: float,
    dni: Optional[float] = None,
    dhi: Optional[float] = None,
    solar_zenith: Optional[float] = None,
    solar_azimuth: Optional[float] = None,
    collector_tilt: float = 0.0,
    collector_azimuth: float = 0.0,
    azimuth_convention: str = "south_zero_east_negative",
    ground_albedo: float = 0.2,
    transposition_model: str = "perez",
) -> Dict[str, float]:
    """Calculate plane-of-array irradiance.

    This is the main entry point for transposition calculations.
    If DNI/DHI are not provided, they are estimated from GHI and solar position.

    Args:
        ghi: Global horizontal irradiance (W/m²)
        dni: Direct normal irradiance (W/m²), optional
        dhi: Diffuse horizontal irradiance (W/m²), optional
        solar_zenith: Solar zenith angle (degrees), optional
        solar_azimuth: Solar azimuth angle (degrees), optional
        collector_tilt: Collector tilt from horizontal (degrees)
        collector_azimuth: Collector azimuth (degrees)
        azimuth_convention: Convention for azimuth angles
        ground_albedo: Ground reflectance
        transposition_model: Model for transposition

    Returns:
        Dict with poa_direct, poa_diffuse, poa_global
    """
    # Estimate DNI/DHI if not provided
    if dni is None or dhi is None:
        if dhi is None:
            # Estimate DHI from GHI and zenith angle
            import math
            if solar_zenith is not None and solar_zenith < 88:
                # Simple clear-sky estimate
                dhi = ghi * (0.5 + 0.5 * math.cos(math.radians(solar_zenith)))
            else:
                dhi = ghi * 0.7  # Overcast assumption
        if dni is None:
            dni = max(0, ghi - dhi)

    # Call transposition from solar_geometry
    return geo_transposition(
        ghi=ghi,
        dni=dni,
        dhi=dhi,
        solar_zenith=solar_zenith,
        solar_azimuth=solar_azimuth,
        collector_tilt=collector_tilt,
        collector_azimuth=collector_azimuth,
        ground_albedo=ground_albedo,
        model=transposition_model,
    )
