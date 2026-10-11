"""Incidence-angle modifier (IAM) module."""

from __future__ import annotations

from typing import Any, Dict, Optional


def iam_none(incident_angle: float) -> float:
    """IAM model: no angle dependence.

    Returns 1.0 for all angles.
    """
    return 1.0


def iam_klucher(incident_angle: float, theta_b: float = 0.0) -> float:
    """Klucher IAM model.

    Args:
        incident_angle: Angle of incidence in degrees
        theta_b: Base angle for asymmetric correction

    Returns:
        IAM factor (0 to 1)
    """
    import math

    theta = math.radians(incident_angle)
    theta_b_rad = math.radians(theta_b)

    # Klucher formula
    F1 = 1.0 - 0.09 * (theta / (math.pi / 2)) ** 2
    F2 = 1.0 + 0.015 * (theta / (math.pi / 2)) ** 2
    Fb = 1.0 + 0.025 * (theta_b_rad / (math.pi / 2)) ** 2 if theta_b > 0 else 1.0

    return F1 * F2 * Fb


def iam_preiss(incident_angle: float) -> float:
    """Preiss IAM model (ASHRAE).

    Returns:
        IAM factor (0 to 1)
    """
    import math

    theta = math.radians(incident_angle)
    # ASHRAE formula
    return 1.0 - 0.01 * (1 / math.cos(theta) - 1.0) if abs(theta) < (math.pi / 2 - 1e-6) else 0.0


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
        return iam_klucher(incident_angle, params.get("theta_b", 0.0))
    elif model == "preiss":
        return iam_preiss(incident_angle)
    elif model == "user_curve_table":
        # Interpolate from user-provided curve table
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
