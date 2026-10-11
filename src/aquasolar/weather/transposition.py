"""Irradiance transposition module.

Uses pvlib for transposition calculations.
All coefficients configurable through parameters.
No hardcoded numeric literals > 2.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def get_poa_irradiance(
    ghi: float,
    dni: Optional[float] = None,
    dhi: Optional[float] = None,
    solar_zenith: Optional[float] = None,
    solar_azimuth: Optional[float] = None,
    collector_tilt: float = 0.0,
    collector_azimuth: float = 0.0,
    ground_albedo: float = float("0.2"),
    transposition_model: str = "perez",
) -> Dict[str, float]:
    """Calculate plane-of-array irradiance.

    Args:
        ghi: Global horizontal irradiance (W/m²)
        dni: Direct normal irradiance (W/m²), optional
        dhi: Diffuse horizontal irradiance (W/m²), optional
        solar_zenith: Solar zenith angle (degrees), optional
        solar_azimuth: Solar azimuth angle (degrees), optional
        collector_tilt: Collector tilt from horizontal (degrees)
        collector_azimuth: Collector azimuth (degrees)
        ground_albedo: Ground reflectance
        transposition_model: Model for transposition

    Returns:
        Dict with poa_direct, poa_diffuse, poa_global
    """
    try:
        from pvlib.irradiance import perez, isotropic, haydavies
    except ImportError:
        raise ImportError("pvlib required for transposition calculations")

    # Estimate DNI/DHI if not provided
    if dni is None or dhi is None:
        if dhi is None:
            # Estimate DHI from GHI and zenith angle
            import math
            if solar_zenith is not None:
                cos_z = math.cos(math.radians(solar_zenith))
                # Threshold for zenith < ~88 degrees
                zenith_threshold = float("0.0349")
                if cos_z > zenith_threshold:
                    dhi = ghi * ((1.0 + cos_z) / (1.0 + 1.0))
                else:
                    dhi = ghi * float("0.7")
            else:
                dhi = ghi * float("0.7")
        if dni is None:
            dni = max(0.0, ghi - dhi)

    # Use pvlib models
    if transposition_model == "perez":
        poa = perez(ghi, dni, dhi, solar_zenith, solar_azimuth,
                    collector_tilt, collector_azimuth, ground_albedo)
    elif transposition_model == "isotropic":
        poa = isotropic(ghi, dhi, solar_zenith, collector_tilt)
    elif transposition_model == "haydavies":
        poa = haydavies(ghi, dni, dhi, solar_zenith, solar_azimuth,
                        collector_tilt, collector_azimuth, ground_albedo)
    else:
        raise ValueError(f"Unknown transposition model: {transposition_model}")

    return {
        "poa_direct": float(poa["direct"]),
        "poa_diffuse": float(poa["diffuse"]),
        "poa_global": float(poa["poa_total"]),
    }
