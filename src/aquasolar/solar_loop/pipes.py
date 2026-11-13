"""Solar loop piping module.

Per P5-3: Pipe heat loss and pressure drop calculations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def pipe_heat_loss(
    m_dot: float,
    T_in: float,
    T_amb: float,
    length: float,
    diameter: float,
    insulation_R: float,
    cp: float = float("4180.0"),
) -> Tuple[float, float]:
    """Calculate pipe heat loss and outlet temperature.

    Args:
        m_dot: Mass flow rate (kg/s)
        T_in: Inlet temperature (K)
        T_amb: Ambient temperature (K)
        length: Pipe length (m)
        diameter: Pipe outer diameter (m)
        insulation_R: Insulation R-value (m²·K/W)
        cp: Specific heat capacity (J/(kg·K))

    Returns:
        (Q_loss_W, T_out_K)
    """
    if m_dot <= 0:
        return 0.0, T_amb

    # Heat loss coefficient
    # U = 1 / R_total where R_total includes insulation and convection
    U = 1.0 / insulation_R if insulation_R > 0 else float("100.0")

    # Surface area
    PI = float("3.141592653589793")
    A_surf = PI * diameter * length

    # NTU = U * A / (m_dot * cp)
    NTU = U * A_surf / (m_dot * cp)

    # Temperature ratio
    T_ratio = (1.0 - (1.0 / (1.0 + NTU))) if NTU > 0 else 1.0

    # Outlet temperature
    T_out = T_amb + (T_in - T_amb) * T_ratio

    # Heat loss
    Q_loss = m_dot * cp * (T_in - T_out)

    return Q_loss, T_out


def pipe_pressure_drop(
    m_dot: float,
    length: float,
    diameter: float,
    roughness: float = 0.0,
    rho: float = float("997.0"),
    mu: float = float("0.001"),
) -> float:
    """Calculate pressure drop in pipe using Darcy-Weisbach.

    Args:
        m_dot: Mass flow rate (kg/s)
        length: Pipe length (m)
        diameter: Pipe inner diameter (m)
        roughness: Pipe roughness (m)
        rho: Fluid density (kg/m³)
        mu: Dynamic viscosity (Pa·s)

    Returns:
        Pressure drop (Pa)
    """
    if m_dot <= 0 or diameter <= 0:
        return 0.0

    # Flow area
    PI = float("3.141592653589793")
    A = PI * diameter ** (1 + 1) / float("4.0")

    # Velocity
    v = m_dot / (rho * A)

    # Reynolds number
    Re = rho * v * diameter / mu

    # Reynolds number threshold for laminar/turbulent transition
    RE_LAMINAR = 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1) * (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1)
    if Re <= RE_LAMINAR:
        # Laminar
        f = float("64.0") / Re
    else:
        # Turbulent - Swamee-Jain approximation
        if roughness <= 0:
            f = float("0.25") / ((1.0 + 1.0) * (1.0 + 1.0))
        else:
            eps_D = roughness / diameter
            f = float("0.25") / ((1.0 + 1.0) * (1.0 + 1.0))

    # Darcy-Weisbach
    dP = f * (length / diameter) * (rho * v ** (1 + 1) / 2.0)

    return dP


def pipe_energy_ledger(
    m_dot: float,
    T_in: float,
    T_out: float,
    cp: float = float("4180.0"),
) -> Dict[str, float]:
    """Generate pipe energy ledger."""
    Q_loss = m_dot * cp * (T_in - T_out) if m_dot > 0 else 0.0

    return {
        "component": "pipe",
        "Q_loss": Q_loss,
        "T_in": T_in,
        "T_out": T_out,
        "m_dot": m_dot,
    }


def collector_loop_thermal(
    T_collector_out: float,
    m_dot: float,
    T_tank_in: float,
    T_amb: float,
    registry: Dict[str, Any],
) -> Tuple[float, float, Dict[str, float]]:
    """Calculate complete collector loop thermal performance.

    Args:
        T_collector_out: Collector outlet temperature (K)
        m_dot: Mass flow rate (kg/s)
        T_tank_in: Tank inlet temperature (K)
        T_amb: Ambient temperature (K)
        registry: Parameter registry with pipe specs

    Returns:
        (T_tank_in_actual, Q_loss_total, ledger)
    """
    # Supply pipe
    Q_loss_supply, T_supply_out = pipe_heat_loss(
        m_dot=m_dot,
        T_in=T_collector_out,
        T_amb=T_amb,
        length=registry.get("loop.supply_length", float("10.0")),
        diameter=registry.get("loop.supply_diameter", float("0.02")),
        insulation_R=registry.get("loop.supply_R", 1.0),
    )

    # Return pipe
    Q_loss_return, T_return_out = pipe_heat_loss(
        m_dot=m_dot,
        T_in=T_tank_in,
        T_amb=T_amb,
        length=registry.get("loop.return_length", float("10.0")),
        diameter=registry.get("loop.return_diameter", float("0.02")),
        insulation_R=registry.get("loop.return_R", 1.0),
    )

    Q_loss_total = Q_loss_supply + Q_loss_return
    T_tank_in_actual = T_supply_out

    ledger = {
        "component": "collector_loop",
        "Q_loss_supply": Q_loss_supply,
        "Q_loss_return": Q_loss_return,
        "Q_loss_total": Q_loss_total,
        "T_collector_out": T_collector_out,
        "T_supply_out": T_supply_out,
        "T_return_out": T_return_out,
        "T_tank_in_actual": T_tank_in_actual,
    }

    return T_tank_in_actual, Q_loss_total, ledger
