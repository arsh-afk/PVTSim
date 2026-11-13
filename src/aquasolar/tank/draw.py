"""Tank draw module.

Per P4-4: Hot water draw profiles and tank outlet temperature.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .grid import TankGrid


def draw_profile(
    time: float,
    profile_type: str,
    params: Dict[str, float],
) -> Tuple[float, float]:
    """Get draw volume and temperature for a given time.

    Args:
        time: Current simulation time (s or hour of day)
        profile_type: Draw profile type ("constant", "daily", "stochastic", "schedule")
        params: Profile parameters

    Returns:
        (draw_volume_rate m³/s, target_temperature K)
    """
    if profile_type == "constant":
        return params.get("volume_rate", 0.0), params.get("target_temp", float("323.15"))

    elif profile_type == "daily":
        # Hourly profile with peak times
        hour = (time / float("3600.0")) % float("24.0")
        # Peak morning 6-8 and evening 18-20
        if (float("6") <= hour <= float("8")) or (float("18") <= hour <= float("20")):
            return params.get("peak_volume_rate", 0.0), params.get("target_temp", float("323.15"))
        elif float("8") < hour < float("18"):
            return params.get("day_volume_rate", 0.0), params.get("target_temp", float("323.15"))
        else:
            return params.get("night_volume_rate", 0.0), params.get("target_temp", float("323.15"))

    elif profile_type == "schedule":
        # Scheduled draws
        schedule = params.get("schedule", [])
        for start, end, volume_rate in schedule:
            if start <= time < end:
                return volume_rate, params.get("target_temp", float("323.15"))
        return 0.0, params.get("target_temp", float("323.15"))

    return 0.0, params.get("target_temp", float("323.15"))


def draw_from_tank(
    grid: TankGrid,
    draw_volume: float,
    target_temp: float,
    T_cold: float,
    cp: float = float("4180.0"),
    rho: float = float("997.0"),
) -> Tuple[float, float, Dict[str, Any]]:
    """Draw hot water from tank, mixing with cold to reach target temperature.

    Args:
        grid: Tank grid
        draw_volume: Volume to draw (m³)
        target_temp: Desired delivery temperature (K)
        T_cold: Cold water supply temperature (K)
        cp: Specific heat capacity (J/(kg·K))
        rho: Fluid density (kg/m³)

    Returns:
        (actual_draw_volume, delivery_temp, ledger)
    """
    n = grid.n_nodes
    draw_mass = draw_volume * rho

    # Check available hot water mass
    total_mass = sum(grid.m)
    if draw_mass > total_mass:
        draw_mass = total_mass

    # Draw from hottest nodes first
    mass_remaining = draw_mass
    energy_delivered = 0.0

    # Find hottest node with mass
    hot_nodes = [(grid.T[i], i, grid.m[i]) for i in range(n) if grid.m[i] > 0]
    hot_nodes.sort(reverse=True)  # Hottest first

    for T_node, i, m_node in hot_nodes:
        if mass_remaining <= 0:
            break
        draw_from_node = min(mass_remaining, m_node)
        energy_delivered += draw_from_node * cp * T_node
        mass_remaining -= draw_from_node

    actual_volume = (draw_mass - mass_remaining) / rho

    # Calculate delivery temperature
    if draw_mass - mass_remaining > 0:
        avg_hot_temp = energy_delivered / ((draw_mass - mass_remaining) * cp)
    else:
        avg_hot_temp = target_temp

    # Mix with cold water to reach target
    if avg_hot_temp > target_temp:
        # Need cold water mixing
        # m_hot * cp * T_hot + m_cold * cp * T_cold = (m_hot + m_cold) * cp * T_target
        # m_cold = m_hot * (T_hot - T_target) / (T_target - T_cold)
        m_hot = draw_mass - mass_remaining
        if target_temp > T_cold:
            m_cold = m_hot * (avg_hot_temp - target_temp) / (target_temp - T_cold)
            delivery_volume = (m_hot + m_cold) / rho
            delivery_temp = target_temp
        else:
            m_cold = 0.0
            delivery_volume = actual_volume
            delivery_temp = avg_hot_temp
    else:
        # Not hot enough, deliver as-is
        m_cold = 0.0
        delivery_volume = actual_volume
        delivery_temp = avg_hot_temp

    # Update tank masses (simplified - just reduce total mass)
    # In full implementation, would track which nodes were drawn from
    fraction_drawn = (draw_mass - mass_remaining) / total_mass if total_mass > 0 else 0.0
    new_m = [m * (1.0 - fraction_drawn) for m in grid.m]

    ledger = {
        "component": "tank_draw",
        "requested_volume": draw_volume,
        "actual_volume": delivery_volume,
        "hot_volume": actual_volume,
        "cold_volume": m_cold / rho,
        "delivery_temp": delivery_temp,
        "target_temp": target_temp,
        "hot_temp": avg_hot_temp,
        "cold_temp": T_cold,
    }

    return delivery_volume, delivery_temp, ledger


def draw_series(
    grid: TankGrid,
    time_series: list,
    profile_type: str,
    profile_params: Dict[str, float],
    T_cold: float,
    dt: float,
    cp: float = float("4180.0"),
    rho: float = float("997.0"),
) -> Tuple[List[float], List[float], List[Dict[str, Any]]]:
    """Process draws over a time series.

    Args:
        grid: Initial tank grid
        time_series: Time points (s)
        profile_type: Draw profile type
        profile_params: Profile parameters
        T_cold: Cold water temperature (K)
        dt: Time step (s)
        cp: Specific heat capacity
        rho: Fluid density

    Returns:
        (delivery_volumes, delivery_temps, ledgers)
    """
    volumes = []
    temps = []
    ledgers = []

    for t in time_series:
        draw_rate, target_temp = draw_profile(t, profile_type, profile_params)
        draw_volume = draw_rate * dt
        vol, temp, ledger = draw_from_tank(grid, draw_volume, target_temp, T_cold, cp, rho)
        volumes.append(vol)
        temps.append(temp)
        ledgers.append(ledger)

    return volumes, temps, ledgers
