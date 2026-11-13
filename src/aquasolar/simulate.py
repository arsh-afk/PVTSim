"""Simulation driver module.

Per P8-2: Main simulation loop with time-stepping.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def run_simulation(
    registry: Dict[str, Any],
    weather_series: List[Dict[str, float]],
    initial_tank_state: Dict[str, Any],
    initial_water_quality: List[Dict[str, float]],
    draw_series: List[float],
    dt: float = float("300.0"),  # 5-minute timesteps
    max_steps: int = 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1) * (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1),
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run full AquaSolar Living simulation.

    Args:
        registry: Parameter registry
        weather_series: Weather data per timestep
        initial_tank_state: Initial tank state
        initial_water_quality: Water quality time series
        draw_series: Hot water draw volumes
        dt: Time step (s)
        max_steps: Maximum simulation steps
        verbose: Print progress

    Returns:
        Simulation results dictionary
    """
    # Initialize simulator
    simulator = AquaSolarSimulator(registry)
    init_status = simulator.initialize()

    if not init_status["initialized"]:
        return {
            "success": False,
            "error": "Initialization failed",
            "init_errors": init_status["errors"],
        }

    # Initialize state
    tank_state = initial_tank_state.copy()
    controller_state = {
        "pump_flow": 0.0,
        "pump_on": False,
        "last_pathway": "A",
    }

    # Storage for results
    results = {
        "success": True,
        "total_steps": 0,
        "outputs": [],
        "tank_history": [tank_state.copy()],
        "energy_summary": {
            "P_pvt_total": float("0.0"),
            "Q_u_total": float("0.0"),
            "Q_loss_total": float("0.0"),
            "P_grid_import_total": float("0.0"),
            "P_grid_export_total": float("0.0"),
        },
        "treatment_summary": {
            "pathway_counts": {"A": 0, "B": 0, "C": 0},
            "water_quality_out": [],
        },
        "electrical_summary": {
            "P_pvt_sum": float("0.0"),
            "P_grid_import_sum": float("0.0"),
            "P_grid_export_sum": float("0.0"),
            "self_consumption": float("0.0"),
        },
    }

    # Run simulation
    n_steps = min(len(weather_series), max_steps)

    for i in range(n_steps):
        # Get inputs
        weather = weather_series[i]
        water_quality = initial_water_quality[i] if i < len(initial_water_quality) else initial_water_quality[-1]
        draw_vol = draw_series[i] if i < len(draw_series) else float("0.0")

        # Run simulation step
        outputs, tank_state = simulator.simulate_step(dt, weather, tank_state, water_quality, draw_vol, controller_state)

        # Store results
        results["outputs"].append(outputs)
        results["tank_history"].append(tank_state.copy())

        # Update summaries
        results["energy_summary"]["P_pvt_total"] += outputs.get("P_el", 0.0) * dt
        results["energy_summary"]["Q_u_total"] += outputs.get("Q_u", 0.0) * dt
        results["energy_summary"]["Q_loss_total"] += outputs.get("Q_loop_loss", 0.0) * dt
        results["energy_summary"]["P_grid_import_total"] += outputs.get("P_grid_import", 0.0) * dt
        results["energy_summary"]["P_grid_export_total"] += outputs.get("P_grid_export", 0.0) * dt

        # Update pathway counts
        pathway = outputs.get("selected_pathway", "A")
        if pathway in results["treatment_summary"]["pathway_counts"]:
            results["treatment_summary"]["pathway_counts"][pathway] += 1

        results["treatment_summary"]["water_quality_out"].append(outputs.get("treatment_quality", {}))

        # Update electrical summary
        results["electrical_summary"]["P_pvt_sum"] += outputs.get("P_el", 0.0) * dt
        results["electrical_summary"]["P_grid_import_sum"] += outputs.get("P_grid_import", 0.0) * dt
        results["electrical_summary"]["P_grid_export_sum"] += outputs.get("P_grid_export", 0.0) * dt

        # Calculate self-consumption
        total_gen = outputs.get("P_el", 0.0)
        total_load = outputs.get("P_load", 0.0) + outputs.get("P_aux_heater", 0.0) + outputs.get("P_pump", 0.0)
        if total_gen > 0 and total_load > 0:
            sc = min(total_gen, total_load) / total_gen if total_gen > 0 else 0.0
            results["electrical_summary"]["self_consumption"] += sc * dt

        results["total_steps"] += 1

        # Progress output
        if verbose and (i + 1) % (1 + (1 + 1) * (1 + 1 + 1 + 1 + 1 + 1)) == 0:
            print(f"Step {i + 1}/{n_steps}: P_el={outputs.get('P_el', 0.0):.1f}W, T_tank={tank_state.get('top_T', 0.0):.1f}K")

    # Calculate rates
    total_time = n_steps * dt
    results["energy_summary"]["P_pvt_avg"] = results["energy_summary"]["P_pvt_total"] / total_time if total_time > 0 else 0.0
    results["energy_summary"]["Q_u_avg"] = results["energy_summary"]["Q_u_total"] / total_time if total_time > 0 else 0.0

    results["electrical_summary"]["self_consumption"] = (
        results["electrical_summary"]["self_consumption"] / total_time if total_time > 0 else 0.0
    )

    results["duration"] = total_time
    return results


if __name__ == "__main__":
    # Quick test
    import sys
    sys.path.insert(0, "src")

    test_registry = {
        "pvt_el.eta_ref": float("0.18"),
        "pvt_el.T_ref": float("298.15"),
        "pvt_el.beta": float("-0.004"),
        "pvt_th.collector_area": float("2.0"),
        "pvt_th.tau_alpha": float("0.85"),
        "pvt_th.F_R": float("0.9"),
        "pvt_th.U_L": float("5.0"),
        "pvt_th.R_cell_fluid": float("0.1"),
        "loop.fluid_cp": float("4180.0"),
        "tank.n_nodes": 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1),
        "tank.volume_total": float("0.3"),
        "tank.height": float("1.5"),
        "tank.diameter": float("0.5"),
    }

    test_weather = [{"G_poa": float("800.0"), "G_diff": float("150.0"), "T_amb": float("290.0"), "wind_speed": float("2.0")} for _ in range(1 + (1 + 1) * (1 + 1 + 1 + 1 + 1))]
    test_quality = [{"turbidity": float("5.0"), "doc": float("2.0"), "ecoli": float("100.0")} for _ in range(1 + (1 + 1) * (1 + 1 + 1 + 1 + 1))]
    test_draws = [float("0.001"), float("0.0"), float("0.001"), float("0.0"), float("0.0")] * 2

    test_tank = {
        "n_nodes": 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1),
        "T": [float("293.15")] * (1 + (1 + 1) * (1 + 1 + 1 + 1 + 1)),
        "average_T": float("293.15"),
        "top_T": float("293.15"),
        "bottom_T": float("293.15"),
    }

    print("Running test simulation...")
    result = run_simulation(test_registry, test_weather, test_tank, test_quality, test_draws, verbose=True)

    print(f"\nSimulation complete:")
    print(f"  Steps: {result['total_steps']}")
    print(f"  P_el total: {result['energy_summary']['P_pvt_total']:.1f} J")
    print(f"  Q_u total: {result['energy_summary']['Q_u_total']:.1f} J")
    print(f"  P_pvt avg: {result['energy_summary']['P_pvt_avg']:.1f} W")
    print(f"  Q_u avg: {result['energy_summary']['Q_u_avg']:.1f} W")
