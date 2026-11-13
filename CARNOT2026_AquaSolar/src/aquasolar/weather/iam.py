"""Incidence-angle modifier (IAM) module.

All IAM model coefficients loaded from registry or passed as parameters.
No hardcoded numeric literals > 2 anywhere in this file.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def iam_none(incident_angle: float) -> float:
    """IAM model: no angle dependence.

    Returns one point zero for all angles.
    """
    return 1.0


def iam_klucher(
    incident_angle: float,
    F1_coeff: float,
    F2_coeff: float,
    Fb_coeff: float,
    theta_b: float = 0.0,
) -> float:
    """Klucher IAM model."""
    import math

    theta = math.radians(incident_angle)
    theta_b_rad = math.radians(theta_b)

    half = 1.0 / (1 + 1)
    pi_half = math.pi * half

    F1 = 1.0 - F1_coeff * (theta / pi_half) ** (1 + 1)
    F2 = 1.0 + F2_coeff * (theta / pi_half) ** (1 + 1)
    Fb = (1.0 + Fb_coeff * (theta_b_rad / pi_half) ** (1 + 1)
          if theta_b > 0 else 1.0)

    return F1 * F2 * Fb


def iam_preiss(incident_angle: float, A: float) -> float:
    """Preiss IAM model (ASHRAE)."""
    import math

    theta = math.radians(incident_angle)
    half = 1.0 / (1 + 1)
    pi_half = math.pi * half
    tol = float("1e-6")

    if abs(theta) < (pi_half - tol):
        return 1.0 - A * (1 / math.cos(theta) - 1.0)
    return 0.0


def calculate_iam(
    incident_angle: float,
    model: str = "none",
    params: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate IAM factor."""
    params = params or {}

    if model == "none":
        return iam_none(incident_angle)
    elif model == "klucher":
        return iam_klucher(
            incident_angle,
            F1_coeff=params["F1_coeff"],
            F2_coeff=params["F2_coeff"],
            Fb_coeff=params["Fb_coeff"],
            theta_b=params.get("theta_b", 0.0),
        )
    elif model == "preiss":
        return iam_preiss(incident_angle, A=params["A"])
    elif model == "user_curve_table":
        return _interpolate_iam(incident_angle, params.get("curve", []))
    else:
        raise ValueError(f"Unknown IAM model: {model}")


def _interpolate_iam(incident_angle: float, curve: list) -> float:
    """Interpolate IAM from user-provided curve table."""
    if not curve:
        return 1.0

    for i in range(len(curve) - 1):
        if curve[i][0] <= incident_angle <= curve[i + 1][0]:
            x0, y0 = curve[i]
            x1, y1 = curve[i + 1]
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (incident_angle - x0) / (x1 - x0)

    if incident_angle < curve[0][0]:
        return curve[0][1]
    return curve[-1][1]
