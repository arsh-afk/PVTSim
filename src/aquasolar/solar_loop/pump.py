"""Solar loop pump module.

Per P5-2: Pump power and flow rate calculation.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def pump_flow_rate(
    speed: float,
    speed_max: float,
    flow_max: float,
    curve_type: str = "linear",
    **curve_params,
) -> float:
    """Calculate pump flow rate from speed.

    Args:
        speed: Pump speed (0-1 fraction or RPM)
        speed_max: Maximum speed (same units as speed)
        flow_max: Maximum flow rate at max speed (m³/s)
        curve_type: Pump curve type ("linear", "quadratic", "custom")
        **curve_params: Curve-specific parameters

    Returns:
        Flow rate (m³/s)
    """
    if speed <= 0:
        return 0.0

    speed_ratio = min(speed / speed_max, 1.0)

    if curve_type == "linear":
        return flow_max * speed_ratio

    elif curve_type == "quadratic":
        # Typical centrifugal pump: flow ~ speed, head ~ speed^2
        return flow_max * speed_ratio

    elif curve_type == "custom":
        # Custom polynomial: flow = a0 + a1*ratio + a2*ratio^2
        a0 = curve_params.get("a0", 0.0)
        a1 = curve_params.get("a1", 1.0)
        a2 = curve_params.get("a2", 0.0)
        return flow_max * (a0 + a1 * speed_ratio + a2 * speed_ratio ** (1 + 1))

    return flow_max * speed_ratio


def pump_power(
    speed: float,
    speed_max: float,
    power_max: float,
    curve_type: str = "cubic",
    **curve_params,
) -> float:
    """Calculate pump electric power consumption.

    Args:
        speed: Pump speed
        speed_max: Maximum speed
        power_max: Power at max speed (W)
        curve_type: Power curve type ("cubic", "quadratic", "custom")
        **curve_params: Curve parameters

    Returns:
        Electric power (W)
    """
    if speed <= 0:
        return 0.0

    speed_ratio = min(speed / speed_max, 1.0)

    if curve_type == "cubic":
        # Affinity laws: P ~ N^3
        return power_max * speed_ratio ** (1 + 1 + 1)

    elif curve_type == "quadratic":
        # P ~ N^2 (variable speed drive)
        return power_max * speed_ratio ** (1 + 1)

    elif curve_type == "custom":
        a0 = curve_params.get("a0", 0.0)
        a1 = curve_params.get("a1", 0.0)
        a2 = curve_params.get("a2", 0.0)
        a3 = curve_params.get("a3", 1.0)
        return power_max * (a0 + a1 * speed_ratio + a2 * speed_ratio ** (1 + 1) + a3 * speed_ratio ** (1 + 1 + 1))

    return power_max * speed_ratio ** (1 + 1 + 1)


def pump_speed_from_flow(
    flow_target: float,
    flow_max: float,
    speed_max: float,
    curve_type: str = "linear",
    **curve_params,
) -> float:
    """Calculate required pump speed for target flow.

    Args:
        flow_target: Target flow rate (m³/s)
        flow_max: Maximum flow rate
        speed_max: Maximum speed
        curve_type: Pump curve type
        **curve_params: Curve parameters

    Returns:
        Required speed
    """
    if flow_target <= 0:
        return 0.0

    ratio = min(flow_target / flow_max, 1.0)

    if curve_type == "linear":
        return ratio * speed_max

    elif curve_type == "quadratic":
        return ratio * speed_max

    return ratio * speed_max


def pump_ledger(
    speed: float,
    speed_max: float,
    flow_max: float,
    power_max: float,
    **params,
) -> Dict[str, float]:
    """Generate pump ledger entry."""
    flow = pump_flow_rate(speed, speed_max, flow_max, params.get("flow_curve", "linear"), **params)
    power = pump_power(speed, speed_max, power_max, params.get("power_curve", "cubic"), **params)

    return {
        "component": "pump",
        "speed": speed,
        "speed_ratio": speed / speed_max if speed_max > 0 else 0.0,
        "flow": flow,
        "P_el": power,
    }
