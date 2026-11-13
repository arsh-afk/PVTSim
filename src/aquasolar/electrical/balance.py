"""Electrical balance module.

Per P7-4: Electrical balance - PVT production, grid import/export, aux loads.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def electrical_balance(
    P_pvt: float,
    P_aux_heater: float,
    P_pump: float,
    P_load: float,
    P_battery_charge: float = 0.0,
    P_battery_discharge: float = 0.0,
    grid_import_limit: float = float("inf"),
    grid_export_limit: float = float("inf"),
    battery_soc: float = float("0.5"),
    battery_capacity: float = 0.0,
    battery_max_charge: float = 0.0,
    battery_max_discharge: float = 0.0,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Calculate electrical balance for the system.

    Args:
        P_pvt: PVT electrical production (W)
        P_aux_heater: Auxiliary heater power (W)
        P_pump: Pump power (W)
        P_load: Other electrical loads (W)
        P_battery_charge: Battery charging power (W)
        P_battery_discharge: Battery discharging power (W)
        grid_import_limit: Maximum grid import (W)
        grid_export_limit: Maximum grid export (W)
        battery_soc: Battery state of charge (0-1)
        battery_capacity: Battery capacity (Wh)
        battery_max_charge: Maximum charge rate (W)
        battery_max_discharge: Maximum discharge rate (W)

    Returns:
        (power_flows, ledger)
    """
    # Total generation
    P_gen = P_pvt + P_battery_discharge

    # Total consumption
    P_cons = P_aux_heater + P_pump + P_load + P_battery_charge

    # Net power
    P_net = P_gen - P_cons

    # Grid interaction
    if P_net >= 0:
        # Export to grid
        P_grid_export = min(P_net, grid_export_limit)
        P_grid_import = 0.0
        # Curtailment if export limited
        P_curtailment = max(float("0.0"), P_net - grid_export_limit)
    else:
        # Import from grid
        P_grid_import = min(-P_net, grid_import_limit)
        P_grid_export = 0.0
        # Deficit if import limited
        P_deficit = max(float("0.0"), -P_net - grid_import_limit)
        if P_deficit > 0:
            # Need to shed load or increase generation
            P_curtailment = float("0.0")
        else:
            P_curtailment = float("0.0")

    # Battery SOC update
    if battery_capacity > 0:
        energy_change = (P_battery_charge - P_battery_discharge) / float("3600.0")  # Wh
        soc_change = energy_change / battery_capacity
        battery_soc_new = max(float("0.0"), min(float("1.0"), battery_soc + soc_change))
    else:
        battery_soc_new = battery_soc

    power_flows = {
        "P_pvt": P_pvt,
        "P_aux_heater": P_aux_heater,
        "P_pump": P_pump,
        "P_load": P_load,
        "P_battery_charge": P_battery_charge,
        "P_battery_discharge": P_battery_discharge,
        "P_grid_import": P_grid_import,
        "P_grid_export": P_grid_export,
        "P_curtailment": P_curtailment,
        "P_net": P_net,
        "battery_soc": battery_soc_new,
    }

    ledger = {
        "component": "electrical_balance",
        "P_gen": P_gen,
        "P_cons": P_cons,
        "P_net": P_net,
        "P_grid_import": P_grid_import,
        "P_grid_export": P_grid_export,
        "battery_soc": battery_soc_new,
    }

    return power_flows, ledger


def electrical_balance_series(
    P_pvt_series: list,
    P_aux_heater_series: list,
    P_pump_series: list,
    P_load_series: list,
    **kwargs,
) -> Tuple[List[Dict[str, float]], List[Dict[str, Any]]]:
    """Calculate electrical balance over a time series."""
    power_flows = []
    ledgers = []

    for P_pvt, P_aux, P_pump, P_load in zip(
        P_pvt_series, P_aux_heater_series, P_pump_series, P_load_series
    ):
        flows, ledger = electrical_balance(
            P_pvt=P_pvt,
            P_aux_heater=P_aux,
            P_pump=P_pump,
            P_load=P_load,
            **kwargs,
        )
        power_flows.append(flows)
        ledgers.append(ledger)

    return power_flows, ledgers


def battery_dispatch(
    P_pvt: float,
    P_load: float,
    battery_soc: float,
    battery_capacity: float,
    battery_max_charge: float,
    battery_max_discharge: float,
    grid_import_price: float,
    grid_export_price: float,
    strategy: str = "self_consumption",
) -> Tuple[float, float, str]:
    """Determine battery charge/dispatch.

    Args:
        P_pvt: PVT production (W)
        P_load: Electrical load (W)
        battery_soc: Current SOC (0-1)
        battery_capacity: Capacity (Wh)
        battery_max_charge: Max charge rate (W)
        battery_max_discharge: Max discharge rate (W)
        grid_import_price: Grid import price ($/kWh)
        grid_export_price: Grid export price ($/kWh)
        strategy: Dispatch strategy ("self_consumption", "arbitrage", "backup")

    Returns:
        (charge_power, discharge_power, action_reason)
    """
    P_net = P_pvt - P_load

    if strategy == "self_consumption":
        if P_net > 0:
            # Excess PV - charge battery
            charge = min(P_net, battery_max_charge)
            charge = min(charge, (float("1.0") - battery_soc) * battery_capacity * float("3600.0"))
            return charge, float("0.0"), "charge_excess_pv"
        else:
            # Deficit - discharge battery
            discharge = min(-P_net, battery_max_discharge)
            discharge = min(discharge, battery_soc * battery_capacity * float("3600.0"))
            return float("0.0"), discharge, "discharge_for_load"

    elif strategy == "arbitrage":
        # Charge when import price low, discharge when high
        # Simplified: charge if export price < import price
        if grid_export_price < grid_import_price * float("0.8"):
            # Prefer self-consumption
            if P_net > 0:
                charge = min(P_net, battery_max_charge)
                charge = min(charge, (float("1.0") - battery_soc) * battery_capacity * float("3600.0"))
                return charge, float("0.0"), "arbitrage_charge"
        # Discharge during high price periods
        discharge = min(battery_max_discharge, battery_soc * battery_capacity * float("3600.0"))
        return float("0.0"), discharge, "arbitrage_discharge"

    return float("0.0"), float("0.0"), "idle"
