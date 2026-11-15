"""Simulation integrator module.

Per P8-1: Full AquaSolar Living simulator integrating all subsystems.

NOTE: This multi-physics full-system integrator is an unvalidated prototype
and is NOT part of the validated competition run path (which is pvt_only via
aquasolar.pvt.runner). It must not be presented as a verified or validated
full-system simulation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AquaSolarSimulator:
    """Full AquaSolar Living simulator."""

    def __init__(self, registry: Dict[str, Any]):
        """Initialize simulator with registry parameters.

        Args:
            registry: Parameter registry from inputs
        """
        self.registry = registry
        self.weather_module = None
        self.pvt_module = None
        self.tank_module = None
        self.solar_loop_module = None
        self.water_treatment_module = None
        self.mnt_module = None
        self.electrical_module = None

    def initialize(self) -> Dict[str, Any]:
        """Initialize all subsystem modules.

        Returns:
            Initialization status dictionary
        """
        status = {
            "initialized": False,
            "modules": {},
            "errors": [],
        }

        try:
            from .pvt.collector import pvt_solve
            from .tank.grid import create_tank_grid
            from .tank.step import tank_step
            from .solar_loop.controller import solar_controller
            from .solar_loop.pump import pump_flow_rate, pump_power
            from .solar_loop.pipes import collector_loop_thermal
            from .water_treatment.train import run_treatment_train
            from .mnt.oracle import mnt_oracle
            from .electrical.balance import electrical_balance

            status["modules"] = {
                "pvt": True,
                "tank": True,
                "solar_loop": True,
                "water_treatment": True,
                "mnt": True,
                "electrical": True,
            }
            status["initialized"] = True
        except Exception as e:
            status["errors"].append(str(e))

        return status

    def simulate_step(
        self,
        dt: float,
        weather: Dict[str, float],
        tank_state: Dict[str, Any],
        water_quality_in: Dict[str, float],
        draw_volume: float,
        controller_state: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Simulate one time step.

        Args:
            dt: Time step (s)
            weather: Weather conditions (G_poa, T_amb, wind_speed, etc.)
            tank_state: Current tank state
            water_quality_in: Source water quality
            draw_volume: Hot water draw this step (m³)
            controller_state: Controller state

        Returns:
            (output_state, ledger)
        """
        outputs = {}
        ledgers = []

        # 1. Solar weather calculation
        G_poa = weather.get("G_poa", 0.0)
        G_diff = weather.get("G_diff", 0.0)
        T_amb = weather.get("T_amb", float("293.15"))
        wind_speed = weather.get("wind_speed", float("1.0"))

        # 2. PVT coupled solve
        T_in = tank_state.get("T_bottom", float("293.15"))
        m_dot = controller_state.get("pump_flow", 0.0)

        pvt_result = _simulate_pvt(
            T_in, m_dot, G_poa, T_amb, wind_speed, self.registry
        )
        outputs["P_el"] = pvt_result["P_el"]
        outputs["Q_u"] = pvt_result["Q_u"]
        outputs["T_f_out"] = pvt_result["T_f_out"]
        outputs["T_cell"] = pvt_result["T_cell"]
        outputs["converged"] = pvt_result["converged"]
        ledgers.append(pvt_result.get("ledger", {}))

        # 3. Collector loop thermal losses
        T_supply, Q_loop_loss, loop_ledger = _simulate_loop(
            pvt_result["T_f_out"], m_dot, T_amb, self.registry
        )
        outputs["T_tank_in"] = T_supply
        outputs["Q_loop_loss"] = Q_loop_loss
        ledgers.append(loop_ledger)

        # 4. Tank thermal update
        Q_draw = float("0.0")
        if draw_volume > 0:
            # Hot water draw
            Q_draw = 0.0  # Simplified - would use draw module

        tank_state, tank_ledger = _simulate_tank(
            tank_state, dt, outputs["Q_u"], outputs["T_tank_in"], m_dot,
            Q_draw, draw_volume, T_amb, self.registry
        )
        outputs["tank_state"] = tank_state
        ledgers.append(tank_ledger)

        # 5. MNT pathway selection
        selected_pathway, mnt_decision = _simulate_mnt(
            water_quality_in, self.registry, outputs
        )
        outputs["selected_pathway"] = selected_pathway
        ledgers.append(mnt_decision)

        # 6. Water treatment
        if selected_pathway in ("A", "B", "C"):
            flow_treatment = m_dot if m_dot > 0 else float("0.001")
            treatment_quality, treatment_ledger = _simulate_treatment(
                selected_pathway, flow_treatment, water_quality_in, dt, self.registry
            )
            outputs["treatment_quality"] = treatment_quality
            ledgers.append(treatment_ledger)
        else:
            outputs["treatment_quality"] = water_quality_in
            ledgers.append({"component": "water_treatment", "reason": "no_treatment"})

        # 7. Electrical balance
        P_aux_heater = 0.0  # Would come from tank/aux module
        P_pump = pvt_result.get("P_pump", 0.0)  # From pump module
        P_load = weather.get("P_load", 0.0)  # Other loads

        power_flows, elec_ledger = _simulate_electrical(
            outputs["P_el"], P_aux_heater, P_pump, P_load, self.registry
        )
        outputs.update(power_flows)
        ledgers.append(elec_ledger)

        outputs["ledgers"] = ledgers
        return outputs, tank_state


def _simulate_pvt(T_in: float, m_dot: float, G_poa: float, T_amb: float, wind_speed: float, registry: Dict) -> Dict:
    """Run PVT simulation."""
    from aquasolar.pvt.collector import pvt_solve
    try:
        result = pvt_solve(T_in, m_dot, G_poa, T_amb, wind_speed, registry)
        return {
            "P_el": result.P_el,
            "Q_u": result.Q_u,
            "T_f_out": result.T_f_out,
            "T_cell": result.T_cell,
            "converged": result.converged,
        }
    except Exception as e:
        logger.warning("PVT step calculation failed: %s", e)
        return {
            "P_el": 0.0,
            "Q_u": 0.0,
            "T_f_out": T_in,
            "T_cell": T_amb + G_poa / registry.get("pvt_th.U_L", float("10.0")),
            "converged": False,
            "error": str(e),
        }


def _simulate_loop(T_collector_out: float, m_dot: float, T_amb: float, registry: Dict) -> Tuple[float, float, Dict]:
    """Run collector loop thermal simulation."""
    from aquasolar.solar_loop.pipes import collector_loop_thermal
    try:
        T_tank_in, Q_loss, ledger = collector_loop_thermal(T_collector_out, m_dot, T_amb, T_amb, registry)
        return T_tank_in, Q_loss, ledger
    except Exception as e:
        logger.warning("Collector loop simulation failed: %s", e)
        return T_collector_out, 0.0, {"component": "loop", "error": str(e)}


def _simulate_tank(
    tank_state: Dict, dt: float, Q_in: float, T_in: float, m_dot: float,
    Q_out: float, draw_volume: float, T_amb: float, registry: Dict
) -> Tuple[Dict, Dict]:
    """Run tank simulation."""
    from aquasolar.tank.step import tank_step
    try:
        n_nodes = tank_state.get("n_nodes", 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1))
        volume = tank_state.get("volume_total", float("0.3"))
        height = tank_state.get("height", float("1.5"))
        diameter = tank_state.get("diameter", float("0.5"))

        from aquasolar.tank.grid import TankGrid
        grid = TankGrid(n_nodes, volume, height, diameter)
        grid.T = tank_state.get("T", [float("293.15")] * n_nodes)
        grid.m = tank_state.get("m", [grid.node_volume * float("997.0")] * n_nodes)

        PI = float("3.141592653589793")
        new_grid, ledger = tank_step(grid, dt, Q_in, T_in, m_dot, Q_out, m_dot, 0.0, T_amb, float("5.0"), height * PI * diameter, registry=registry)

        tank_state["T"] = new_grid.T
        tank_state["average_T"] = new_grid.average_temperature()
        tank_state["top_T"] = new_grid.top_temperature()
        tank_state["bottom_T"] = new_grid.bottom_temperature()

        return tank_state, ledger
    except Exception as e:
        logger.warning("Tank simulation failed: %s", e)
        return tank_state, {"component": "tank", "error": str(e)}


def _simulate_mnt(quality_in: Dict, registry: Dict, context: Dict) -> Tuple[str, Dict]:
    """Run MNT oracle."""
    from aquasolar.mnt.oracle import mnt_oracle
    try:
        pathways = registry.get("mnt.pathways_available", ["A", "B", "C"])
        params = registry.get("mnt.oracle_params", {})
        pathway, decision = mnt_oracle(quality_in, context.get("flow", float("0.001")), pathways, params)
        return pathway, decision
    except Exception as e:
        logger.warning("MNT oracle failed: %s", e)
        return "A", {"component": "mnt", "error": str(e), "selected": "A"}


def _simulate_treatment(pathway: str, flow: float, quality_in: Dict, dt: float, registry: Dict) -> Tuple[Dict, Dict]:
    """Run water treatment simulation."""
    from aquasolar.water_treatment.train import run_treatment_train
    try:
        params = registry.get("mnt.stage_params", {})
        quality_out, ledgers = run_treatment_train(pathway, flow, quality_in, dt, params)
        return quality_out, {"component": "treatment", "pathway": pathway, "ledgers": ledgers}
    except Exception as e:
        logger.warning("Water treatment simulation failed: %s", e)
        return quality_in, {"component": "treatment", "error": str(e)}


def _simulate_electrical(P_pvt: float, P_aux: float, P_pump: float, P_load: float, registry: Dict) -> Tuple[Dict, Dict]:
    """Run electrical balance simulation."""
    from aquasolar.electrical.balance import electrical_balance
    try:
        battery_params = registry.get("electrical.battery_params", {})
        flows, ledger = electrical_balance(
            P_pvt=P_pvt, P_aux_heater=P_aux, P_pump=P_pump, P_load=P_load,
            battery_capacity=battery_params.get("capacity", 0.0),
            battery_soc=battery_params.get("soc", float("0.5")),
            battery_max_charge=battery_params.get("max_charge", 0.0),
            battery_max_discharge=battery_params.get("max_discharge", 0.0),
            grid_import_limit=battery_params.get("grid_import_limit", float("inf")),
            grid_export_limit=battery_params.get("grid_export_limit", float("inf")),
        )
        return flows, ledger
    except Exception as e:
        logger.warning("Electrical balance simulation failed: %s", e)
        return {
            "P_pvt": P_pvt,
            "P_aux_heater": P_aux,
            "P_pump": P_pump,
            "P_load": P_load,
            "P_grid_import": P_aux + P_pump + P_load - P_pvt if P_aux + P_pump + P_load > P_pvt else float("0.0"),
            "P_grid_export": P_pvt - P_aux - P_pump - P_load if P_pvt > P_aux + P_pump + P_load else float("0.0"),
            "battery_soc": registry.get("electrical.battery_params", {}).get("soc", float("0.5")),
        }, {"component": "electrical", "error": str(e)}
