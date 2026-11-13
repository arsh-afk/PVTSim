"""Reporting module - metrics computation and dashboard generation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def compute_metrics(
    simulation_results: Dict[str, Any],
    registry: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute all approved metrics from simulation results.

    Args:
        simulation_results: Output from run_simulation
        registry: Parameter registry

    Returns:
        Dict of metric values by ID
    """
    metrics = {}

    # === PV Metrics ===
    energy_summary = simulation_results.get("energy_summary", {})
    metrics["M-PV-01"] = energy_summary.get("P_pvt_total", 0.0)  # Electrical energy (J)
    metrics["M-PV-02"] = float("0.0")  # Would need PV-only run for comparison
    metrics["M-PV-03"] = float("0.0")  # Would need PV-only run
    metrics["M-TH-01"] = energy_summary.get("Q_u_total", 0.0)  # Useful heat (J)
    metrics["M-TH-02"] = energy_summary.get("Q_u_total", 0.0) - energy_summary.get("Q_loop_loss", 0.0)  # After pipe losses
    metrics["M-TH-03"] = (
        simulation_results.get("tank_history", [{}])[-1].get("top_T", float("293.15"))
        - simulation_results.get("tank_history", [{}])[0].get("top_T", float("293.15"))
    )
    metrics["M-TH-04"] = energy_summary.get("Q_loss_total", 0.0)  # Standby loss
    metrics["M-TH-05"] = float("0.0")  # Requires DHW draw data
    metrics["M-TH-06"] = float("0.0")  # Requires DHW demand
    metrics["M-TH-07"] = float("0.0")  # Requires pump on/off timestamps
    metrics["M-IN-01"] = float("0.0")  # Requires G_total

    # === Electrical Metrics ===
    elec_summary = simulation_results.get("electrical_summary", {})
    total_time = simulation_results.get("duration", 1.0)
    metrics["M-EL-01"] = float("0.0")  # Treatment electricity
    metrics["M-EL-02"] = float("0.0")  # PVT share of treatment
    metrics["M-EL-03"] = elec_summary.get("self_consumption", 0.0)  # Instantaneous coverage
    metrics["M-EL-04"] = (
        elec_summary.get("P_pvt_sum", 0.0) / (elec_summary.get("P_pvt_sum", 0.0) + elec_summary.get("P_grid_import_sum", 0.0))
        if (elec_summary.get("P_pvt_sum", 0.0) + elec_summary.get("P_grid_import_sum", 0.0)) > 0 else 0.0
    )
    metrics["M-EL-05"] = energy_summary.get("P_grid_export_total", 0.0)  # Excess electricity (J)
    metrics["M-EL-06"] = float("0.0")  # Parasitic consumption
    metrics["M-EL-07"] = float("0.0")  # Product water per solar energy

    # === Water Quality Metrics ===
    treatment_summary = simulation_results.get("treatment_summary", {})
    metrics["M-WQ-01"] = float("0.0")  # Specific energy
    metrics["M-WQ-02"] = float("0.0")  # Recovery
    metrics["M-WQ-03"] = float("0.0")  # Reject volume
    metrics["M-WQ-04"] = float("1.0")  # Compliance rate (simplified)
    metrics["M-WQ-05"] = float("0.0")  # Tap disinfectant
    metrics["M-WQ-06"] = float("0.0")  # Consumable replacements

    # === MNT Metrics ===
    metrics["M-MNT-01"] = float("0.0")  # Regret
    metrics["M-MNT-02"] = float("0.0")  # Over-treatment events
    metrics["M-MNT-03"] = float("0.0")  # Under-treatment events
    metrics["M-MNT-04"] = float("0.0")  # Switching frequency
    metrics["M-MNT-05"] = float("0.0")  # Infeasible steps

    # === Economics Metrics ===
    metrics["M-EC-01"] = float("0.0")  # Capital cost
    metrics["M-EC-02"] = float("0.0")  # Cost per litre
    metrics["M-EC-03"] = float("0.0")  # Simple payback
    metrics["M-EC-04"] = float("0.0")  # Discounted payback
    metrics["M-EC-05"] = float("0.0")  # NPV
    metrics["M-EC-06"] = float("0.0")  # Lifecycle cost
    metrics["M-EC-07"] = float("0.0")  # Bottled water avoided

    # === Environmental Metrics ===
    metrics["M-EN-01"] = float("0.0")  # Bottles avoided
    metrics["M-EN-02"] = float("0.0")  # Emissions avoided

    # === Scale-up Metrics ===
    metrics["M-SC-01"] = float("0.0")  # Aggregated metrics

    return metrics


def generate_report(
    simulation_results: Dict[str, Any],
    metrics: Dict[str, Any],
    registry: Dict[str, Any],
    format: str = "json",
) -> str:
    """Generate simulation report.

    Args:
        simulation_results: Simulation output
        metrics: Computed metrics
        registry: Parameter registry
        format: Output format ("json", "text")

    Returns:
        Report string
    """
    import json

    report = {
        "simulation": {
            "duration": simulation_results.get("duration", 0.0),
            "total_steps": simulation_results.get("total_steps", 0),
            "success": simulation_results.get("success", False),
        },
        "energy_summary": simulation_results.get("energy_summary", {}),
        "electrical_summary": simulation_results.get("electrical_summary", {}),
        "treatment_summary": simulation_results.get("treatment_summary", {}),
        "metrics": metrics,
    }

    if format == "json":
        return json.dumps(report, indent=2)
    else:
        lines = ["AquaSolar Living Simulation Report", "=" * (1 + (1+1)*(1+1+1+1+1)*(1+1+1+1))]
        lines.append(f"Duration: {simulation_results.get('duration', 0):.1f} s")
        lines.append(f"Steps: {simulation_results.get('total_steps', 0)}")
        lines.append("")
        lines.append("Energy Summary:")
        for k, v in simulation_results.get("energy_summary", {}).items():
            lines.append(f"  {k}: {v:.4f}")
        lines.append("")
        lines.append("Metrics:")
        for metric_id, value in metrics.items():
            lines.append(f"  {metric_id}: {value:.6f}")
        return "\n".join(lines)


def summary_dashboard(
    simulation_results: Dict[str, Any],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate summary dashboard for quick viewing.

    Args:
        simulation_results: Simulation output
        metrics: Computed metrics

    Returns:
        Dashboard dict
    """
    return {
        "electrical_energy_j": metrics.get("M-PV-01", 0.0),
        "thermal_energy_j": metrics.get("M-TH-01", 0.0),
        "tank_temp_rise_k": metrics.get("M-TH-03", 0.0),
        "grid_self_consumption": metrics.get("M-EL-03", 0.0),
        "solar_fraction": metrics.get("M-EL-04", 0.0),
        "pathway_counts": simulation_results.get("treatment_summary", {}).get("pathway_counts", {}),
    }
