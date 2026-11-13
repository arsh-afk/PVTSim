"""MNT Oracle module.

Per P7-1: Minimum Necessary Treatment oracle - selects optimal pathway.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def water_quality_index(
    quality: Dict[str, float],
    parameters: Dict[str, Any],
) -> float:
    """Calculate water quality index (0-100, higher is better).

    Args:
        quality: Water quality parameters
        parameters: Weighting and threshold parameters

    Returns:
        WQI score
    """
    weights = parameters.get("weights", {})
    thresholds = parameters.get("thresholds", {})

    score = float("100.0")

    # Check each parameter against thresholds
    for param, value in quality.items():
        if param in thresholds:
            threshold = thresholds[param]
            weight = weights.get(param, 1.0)

            if value > threshold:
                # Exceeds threshold - reduce score
                exceedance = (value - threshold) / threshold
                score -= weight * exceedance * float("10.0")

    return max(float("0.0"), min(float("100.0"), score))


def pathway_cost(
    pathway: str,
    flow: float,
    parameters: Dict[str, Any],
) -> Dict[str, float]:
    """Calculate treatment cost for a pathway.

    Args:
        pathway: Pathway identifier (A, B, C)
        flow: Flow rate (m³/s)
        parameters: Cost parameters

    Returns:
        Dict with capital, operational, and total costs
    """
    pathway_costs = parameters.get("pathway_costs", {})

    if pathway not in pathway_costs:
        return {"capital": 0.0, "operational": 0.0, "total": 0.0}

    costs = pathway_costs[pathway]
    flow_m3h = flow * float("3600.0")

    # Capital cost (annualized)
    capital_annual = costs.get("capital_per_m3h", 0.0) * flow_m3h

    # Operational cost
    energy_cost = costs.get("energy_per_m3", 0.0) * flow_m3h
    consumable_cost = costs.get("consumable_per_m3", 0.0) * flow_m3h
    maintenance_cost = costs.get("maintenance_per_m3", 0.0) * flow_m3h

    operational = energy_cost + consumable_cost + maintenance_cost

    return {
        "capital": capital_annual,
        "operational": operational,
        "total": capital_annual + operational,
    }


def mnt_oracle(
    quality: Dict[str, float],
    flow: float,
    pathways_available: List[str],
    parameters: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """Minimum Necessary Treatment Oracle.

    Selects the minimum treatment pathway that meets quality targets
    at lowest cost.

    Args:
        quality: Source water quality
        flow: Required flow rate (m³/s)
        pathways_available: List of available pathway names
        parameters: Oracle parameters (thresholds, weights, costs)

    Returns:
        (selected_pathway, decision_info)
    """
    # Quality targets from parameters
    targets = parameters.get("quality_targets", {})

    # Evaluate each available pathway
    pathway_results = {}

    for pathway in pathways_available:
        # Simulate treatment outcome
        from aquasolar.water_treatment.train import run_treatment_train
        try:
            effluent, _ = run_treatment_train(pathway, flow, quality, 1.0, parameters.get("stage_params", {}))
        except Exception:
            # If pathway fails, mark as infeasible
            pathway_results[pathway] = {
                "feasible": False,
                "reason": "simulation_failed",
                "cost": float("inf"),
            }
            continue

        # Check if effluent meets targets
        feasible = True
        violations = []
        for param, target in targets.items():
            if param in effluent and effluent[param] > target:
                feasible = False
                violations.append(f"{param}: {effluent[param]:.2f} > {target:.2f}")

        # Calculate cost
        cost_info = pathway_cost(pathway, flow, parameters)

        pathway_results[pathway] = {
            "feasible": feasible,
            "violations": violations,
            "cost": cost_info["total"],
            "effluent": effluent,
        }

    # Select minimum cost feasible pathway
    feasible_pathways = {p: r for p, r in pathway_results.items() if r["feasible"]}

    if not feasible_pathways:
        # No feasible pathway - return most advanced available
        selected = pathways_available[-1]
        return selected, {
            "selected_pathway": selected,
            "reason": "no_feasible_pathway",
            "all_results": pathway_results,
        }

    # Choose cheapest feasible
    selected = min(feasible_pathways.keys(), key=lambda p: feasible_pathways[p]["cost"])

    return selected, {
        "selected_pathway": selected,
        "reason": "minimum_cost_feasible",
        "cost": feasible_pathways[selected]["cost"],
        "all_results": pathway_results,
    }


def mnt_oracle_series(
    quality_series: list,
    flow_series: list,
    pathways_available: List[str],
    parameters: Dict[str, Any],
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Run MNT oracle over a time series."""
    selections = []
    decisions = []

    for quality, flow in zip(quality_series, flow_series):
        pathway, decision = mnt_oracle(quality, flow, pathways_available, parameters)
        selections.append(pathway)
        decisions.append(decision)

    return selections, decisions
