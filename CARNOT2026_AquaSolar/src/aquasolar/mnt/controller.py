"""MNT Controller module.

Per P7-2: Sensor-based controller for pathway selection.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .oracle import mnt_oracle, pathway_cost


def sensor_readings(
    quality: Dict[str, float],
    sensor_config: Dict[str, Any],
) -> Dict[str, float]:
    """Simulate sensor readings with noise and detection limits.

    Args:
        quality: True water quality
        sensor_config: Sensor specifications

    Returns:
        Simulated sensor readings
    """
    readings = {}

    for param, true_value in quality.items():
        if param in sensor_config:
            spec = sensor_config[param]

            # Detection limit
            dl = spec.get("detection_limit", float("0.0"))
            if true_value < dl:
                readings[param] = dl / float("2.0")  # Report as half DL
                continue

            # Add noise
            noise_pct = spec.get("noise_percent", float("0.0"))
            import random
            noise = random.gauss(float("0.0"), true_value * noise_pct / float("100.0"))
            readings[param] = max(dl, true_value + noise)
        else:
            # No sensor for this parameter
            readings[param] = true_value

    return readings


def sensor_based_controller(
    sensor_data: Dict[str, float],
    flow: float,
    pathways_available: List[str],
    parameters: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """MNT controller using sensor readings.

    Args:
        sensor_data: Sensor readings
        flow: Flow rate (m³/s)
        pathways_available: Available pathways
        parameters: Controller parameters

    Returns:
        (selected_pathway, decision_info)
    """
    # Use oracle with sensor data
    return mnt_oracle(sensor_data, flow, pathways_available, parameters)


def hysteresis_controller(
    sensor_data: Dict[str, float],
    current_pathway: str,
    flow: float,
    pathways_available: List[str],
    parameters: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """Controller with hysteresis to prevent rapid switching.

    Args:
        sensor_data: Sensor readings
        current_pathway: Currently active pathway
        flow: Flow rate
        pathways_available: Available pathways
        parameters: Controller parameters (including hysteresis thresholds)

    Returns:
        (new_pathway, decision_info)
    """
    # Get oracle recommendation
    recommended, decision = mnt_oracle(sensor_data, flow, pathways_available, parameters)

    # Check hysteresis
    hysteresis = parameters.get("hysteresis", {})
    if current_pathway in hysteresis:
        h = hysteresis[current_pathway]
        current_cost = pathway_cost(current_pathway, flow, parameters)["total"]
        recommended_cost = pathway_cost(recommended, flow, parameters)["total"]

        # Only switch if savings exceed hysteresis threshold
        if recommended_cost < current_cost * (float("1.0") - h.get("cost_threshold", float("0.1"))):
            return recommended, {**decision, "hysteresis": "override"}
        else:
            return current_pathway, {**decision, "hysteresis": "hold"}

    return recommended, decision


def adaptive_controller(
    sensor_data: Dict[str, float],
    current_pathway: str,
    flow: float,
    pathways_available: List[str],
    parameters: Dict[str, Any],
    performance_history: List[Dict[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    """Adaptive controller that learns from performance history.

    Args:
        sensor_data: Sensor readings
        current_pathway: Currently active pathway
        flow: Flow rate
        pathways_available: Available pathways
        parameters: Controller parameters
        performance_history: Historical performance data

    Returns:
        (new_pathway, decision_info)
    """
    # Get base recommendation
    recommended, decision = hysteresis_controller(
        sensor_data, current_pathway, flow, pathways_available, parameters
    )

    # Adjust based on performance history
    if performance_history:
        # Calculate recent performance metrics
        recent = performance_history[-1 - (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1):]  # Last 10 periods

        for pathway in pathways_available:
            path_perf = [p for p in recent if p.get("pathway") == pathway]
            if path_perf:
                avg_cost = sum(p.get("cost", float("0.0")) for p in path_perf) / len(path_perf)
                avg_quality = sum(p.get("quality_score", float("0.0")) for p in path_perf) / len(path_perf)

                # If current pathway underperforming, consider switching
                if pathway == current_pathway and avg_quality < parameters.get("min_quality_score", float("80.0")):
                    # Look for better pathway
                    for alt in pathways_available:
                        if alt != current_pathway:
                            alt_perf = [p for p in recent if p.get("pathway") == alt]
                            if alt_perf:
                                alt_quality = sum(p.get("quality_score", float("0.0")) for p in alt_perf) / len(alt_perf)
                                if alt_quality > avg_quality:
                                    recommended = alt
                                    decision["adaptive"] = "quality_improvement"
                                    break

    return recommended, decision


def controller_ledger(
    decision: Dict[str, Any],
    flow: float,
    pathway: str,
) -> Dict[str, Any]:
    """Generate controller decision ledger."""
    return {
        "component": "mnt_controller",
        "selected_pathway": pathway,
        "flow": flow,
        "reason": decision.get("reason", "unknown"),
        "cost": decision.get("cost", float("0.0")),
        "all_results": decision.get("all_results", {}),
    }
