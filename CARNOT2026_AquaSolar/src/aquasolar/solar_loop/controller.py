"""Solar loop controller module.

Per P5-1: Collector loop controller with differential temperature control.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def differential_controller(
    T_collector: float,
    T_tank_bottom: float,
    dT_on: float,
    dT_off: float,
    state: bool,
) -> bool:
    """Differential temperature controller for solar loop.

    Args:
        T_collector: Collector temperature (K)
        T_tank_bottom: Tank bottom temperature (K)
        dT_on: Turn-on differential (K)
        dT_off: Turn-off differential (K)
        state: Current pump state (True=on, False=off)

    Returns:
        New pump state
    """
    dT = T_collector - T_tank_bottom

    if state:
        # Pump is on: turn off if dT drops below dT_off
        return dT >= dT_off
    else:
        # Pump is off: turn on if dT exceeds dT_on
        return dT >= dT_on


def solar_controller(
    T_collector: float,
    T_tank_bottom: float,
    T_tank_top: float,
    dT_on: float,
    dT_off: float,
    state: bool,
    max_tank_temp: float = float("353.15"),
    freeze_protection: bool = False,
    T_freeze_on: float = float("277.15"),
    T_freeze_off: float = float("283.15"),
) -> Tuple[bool, str]:
    """Full solar controller with protection functions.

    Args:
        T_collector: Collector temperature (K)
        T_tank_bottom: Tank bottom temperature (K)
        T_tank_top: Tank top temperature (K)
        dT_on: Turn-on differential (K)
        dT_off: Turn-off differential (K)
        state: Current pump state
        max_tank_temp: Maximum tank temperature for overheat protection (K)
        freeze_protection: Enable freeze protection
        T_freeze_on: Freeze protection turn-on temperature (K)
        T_freeze_off: Freeze protection turn-off temperature (K)

    Returns:
        (new_pump_state, reason)
    """
    # Overheat protection: stop if tank too hot
    if T_tank_top >= max_tank_temp:
        return False, "overheat_protection"

    # Freeze protection: run pump if collector near freezing
    if freeze_protection and T_collector <= T_freeze_on:
        return True, "freeze_protection"
    if freeze_protection and state and T_collector >= T_freeze_off:
        return False, "freeze_protection_off"

    # Normal differential control
    new_state = differential_controller(T_collector, T_tank_bottom, dT_on, dT_off, state)
    reason = "differential_on" if new_state and not state else "differential_off" if not new_state and state else "steady"

    return new_state, reason


def controller_series(
    T_collector_series: list,
    T_tank_bottom_series: list,
    T_tank_top_series: list,
    dT_on: float,
    dT_off: float,
    initial_state: bool = False,
    **params,
) -> Tuple[list, list]:
    """Run controller over time series.

    Args:
        T_collector_series: Collector temperatures (K)
        T_tank_bottom_series: Tank bottom temperatures (K)
        T_tank_top_series: Tank top temperatures (K)
        dT_on: Turn-on differential
        dT_off: Turn-off differential
        initial_state: Initial pump state
        **params: Additional parameters

    Returns:
        (pump_states, reasons)
    """
    states = []
    reasons = []
    state = initial_state

    for T_col, T_bot, T_top in zip(T_collector_series, T_tank_bottom_series, T_tank_top_series):
        state, reason = solar_controller(T_col, T_bot, T_top, dT_on, dT_off, state, **params)
        states.append(state)
        reasons.append(reason)

    return states, reasons
