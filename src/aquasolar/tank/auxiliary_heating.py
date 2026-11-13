"""Auxiliary electric heating for the stratified storage tank."""

from __future__ import annotations

import math
from typing import Any

from .grid import TankGrid


def aux_heating(
    grid: TankGrid,
    target_temp: float,
    max_power: float,
    efficiency: float = float("1.0"),
    deadband: float = float("0.0"),
    dt: float = float("1.0"),
    cp: float = float("4180.0"),
) -> tuple[float, dict[str, Any]]:
    """Heat the top tank node when its temperature is below the deadband.

    The returned auxiliary power is electrical input in watts. The tank
    temperature is updated in place; delivered heat is electrical power
    multiplied by ``efficiency``.
    """
    values = {
        "target_temp": target_temp,
        "max_power": max_power,
        "efficiency": efficiency,
        "deadband": deadband,
        "dt": dt,
        "cp": cp,
    }
    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite.")
    if max_power < 0:
        raise ValueError("max_power must not be negative.")
    if efficiency <= 0 or efficiency > 1:
        raise ValueError("efficiency must be greater than zero and at most one.")
    if deadband < 0:
        raise ValueError("deadband must not be negative.")
    if dt <= 0:
        raise ValueError("dt must be greater than zero.")
    if cp <= 0:
        raise ValueError("cp must be greater than zero.")
    if grid.n_nodes <= 0 or len(grid.T) != grid.n_nodes or len(grid.m) != grid.n_nodes:
        raise ValueError("Tank grid must contain at least one node with matching state arrays.")

    top_temperature = grid.top_temperature()
    top_mass = grid.get_mass(0)
    ledger: dict[str, Any] = {
        "component": "aux_heating",
        "status": "off",
        "target_temp": target_temp,
        "top_temp_before": top_temperature,
        "top_temp_after": top_temperature,
        "electrical_power": 0.0,
        "thermal_power": 0.0,
        "energy_added": 0.0,
        "dt": dt,
    }

    if top_mass <= 0:
        ledger["status"] = "no_water"
        return 0.0, ledger
    if top_temperature >= target_temp - deadband or max_power == 0:
        return 0.0, ledger

    energy_required = top_mass * cp * (target_temp - top_temperature)
    requested_power = energy_required / (dt * efficiency)
    electrical_power = min(max_power, requested_power)
    thermal_power = electrical_power * efficiency
    energy_added = thermal_power * dt
    grid.set_temperature(0, top_temperature + energy_added / (top_mass * cp))

    ledger.update(
        {
            "status": "heating",
            "top_temp_after": grid.top_temperature(),
            "electrical_power": electrical_power,
            "thermal_power": thermal_power,
            "energy_added": energy_added,
        }
    )
    return electrical_power, ledger
