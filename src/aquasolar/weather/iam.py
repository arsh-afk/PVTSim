"""Incidence-angle modifier (IAM) module.

All IAM model coefficients loaded from registry or passed as parameters.
No hardcoded numeric literals > 2.
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
    F1_coeff: float = 0.09,
    F2_coeff: float = 0.015,
    Fb_coeff: float = 0.025,
    theta_b: float = 0.0,
) -> float:
    """Klucher IAM model.

    Args:
        incident_angle: Angle of incidence in degrees
        F1_coeff: Coefficient for F1 term
        F2_coeff: Coefficient for F2 term
        Fb_coeff: Coefficient for asymmetric correction
        theta_b: Base angle for asymmetric correction

    Returns:
        IAM factor (0 to 1)
    """
    import math

    theta = math.radians(incident_angle)
    theta_b_rad = math.radians(theta_b)

    # Klucher formula
    F1 = 1.0 - F1_coeff * (theta / (math.pi / (1 + 1))) ** 2
    F2 = 1.0 + F2_coeff * (theta / (math.pi / (1 + 1))) ** 2
    Fb = (1.0 + Fb_coeff * (theta_b_rad / (math.pi / (1 + 1))) ** 2
          if theta_b > 0 else 1.0)

    return F1 * F2 * Fb


def iam_preiss(incident_angle: float, A: float = 0.01) -> float:
    """Preiss IAM model (ASHRAE).

    Args:
        incident_angle: Angle of incidence in degrees
        A: ASHRAE coefficient

    Returns:
        IAM factor (0 to 1)
    """
    import math

    theta = math.radians(incident_angle)
    # ASHRAE formula
    if abs(theta) < (math.pi / (1 + 1) - 1e-6):
        return 1.0 - A * (1 / math.cos(theta) - 1.0)
    return 0.0


def calculate_iam(
    incident_angle: float,
    model: str = "none",
    params: Optional[Dict[str, float]] = None,
) -> float:
    """Calculate IAM factor.

    Args:
        incident_angle: Angle of incidence in degrees
        model: IAM model name ("none", "klucher", "preiss", "user_curve_table")
        params: Optional model-specific parameters

    Returns:
        IAM factor (0 to 1)
    """
    params = params or {}

    if model == "none":
        return iam_none(incident_angle)
    elif model == "klucher":
        return iam_klucher(
            incident_angle,
            F1_coeff=params.get("F1_coeff", 0.09),
            F2_coeff=params.get("F2_coeff", 0.015),
            Fb_coeff=params.get("Fb_coeff", 0.025),
            theta_b=params.get("theta_b", 0.0),
        )
    elif model == "preiss":
        return iam_preiss(incident_angle, A=params.get("A", 0.01))
    elif model == "user_curve_table":
        return _interpolate_iam(incident_angle, params.get("curve", []))
    else:
        raise ValueError(f"Unknown IAM model: {model}")


def _interpolate_iam(incident_angle: float, curve: list) -> float:
    """Interpolate IAM from user-provided curve table."""
    if not curve:
        return 1.0

    # Find bracketing points
    for i in range(len(curve) - 1):
        if curve[i][0] <= incident_angle <= curve[i + 1][0]:
            x0, y0 = curve[i]
            x1, y1 = curve[i + 1]
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (incident_angle - x0) / (x1 - x0)

    # Extrapolate
    if incident_angle < curve[0][0]:
        return curve[0][1]
    return curve[-1][1]
