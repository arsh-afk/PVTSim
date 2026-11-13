"""Tank step module.

Per P4-2: Tank time step with stratification and heat transfer.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .grid import TankGrid, tank_grid_state


def tank_step(
    grid: TankGrid,
    dt: float,
    Q_in: float,
    T_in: float,
    m_dot_in: float,
    Q_out: float,
    m_dot_out: float,
    Q_loss: float,
    T_amb: float,
    U_loss: float,
    A_loss: float,
    cp: float = float("4180.0"),
    rho: float = float("997.0"),
    mixing_model: str = "ideal",
    registry: Optional[Dict[str, Any]] = None,
) -> Tuple[TankGrid, Dict[str, Any]]:
    """Perform one tank time step.

    Args:
        grid: Current tank grid state
        dt: Time step (s)
        Q_in: Heat input from collector (W)
        T_in: Inlet temperature (K)
        m_dot_in: Inlet mass flow rate (kg/s)
        Q_out: Heat drawn from tank (W)
        m_dot_out: Outlet mass flow rate (kg/s)
        Q_loss: Heat loss to ambient (W)
        T_amb: Ambient temperature (K)
        U_loss: Loss coefficient (W/(m²·K))
        A_loss: Loss area (m²)
        cp: Specific heat capacity (J/(kg·K))
        rho: Fluid density (kg/m³)
        mixing_model: Mixing model type
        registry: Parameter registry

    Returns:
        Updated grid and ledger
    """
    n = grid.n_nodes
    new_T = grid.T.copy()
    new_m = grid.m.copy()

    # 1. Handle mass inflows/outflows (advection)
    # Inflow at top node (node 0)
    if m_dot_in > 0:
        m_in = m_dot_in * dt
        # Add mass to top node
        new_m[0] += m_in
        # Mix temperatures (ideal mixing at node)
        if new_m[0] > 0:
            new_T[0] = (grid.m[0] * grid.T[0] + m_in * T_in) / new_m[0]

    # Outflow from bottom node (node n-1)
    if m_dot_out > 0:
        m_out = m_dot_out * dt
        # Remove mass from bottom node
        available_mass = new_m[-1]
        m_out = min(m_out, available_mass)
        new_m[-1] -= m_out

    # 2. Handle heat inputs/outputs
    # Collector heat input at top node
    if Q_in > 0 and new_m[0] > 0:
        new_T[0] += Q_in * dt / (new_m[0] * cp)

    # Draw heat output from top node (hottest water drawn first)
    if Q_out > 0 and new_m[0] > 0:
        # Find hottest node with mass
        for i in range(n):
            if new_m[i] > 0:
                energy_available = new_m[i] * cp * (new_T[i] - T_amb)
                energy_draw = Q_out * dt
                if energy_available >= energy_draw:
                    new_T[i] -= energy_draw / (new_m[i] * cp)
                    break
                else:
                    new_T[i] = T_amb
                    # Continue to next node for remaining energy
                    pass

    # 3. Heat loss to ambient (distributed)
    if Q_loss > 0:
        for i in range(n):
            if new_m[i] > 0:
                # Distribute loss proportionally to node surface area
                node_loss = Q_loss * (grid.node_area / A_loss) if A_loss > 0 else 0.0
                new_T[i] -= node_loss * dt / (new_m[i] * cp)
                new_T[i] = max(new_T[i], T_amb)

    # 4. Conduction/natural convection between nodes (stratification)
    # Simple vertical conduction
    k_eff = registry.get("tank.k_eff", float("0.6")) if registry else float("0.6")
    for i in range(n - 1):
        T_avg = (new_T[i] + new_T[i + 1]) / 2.0
        dT_dz = (new_T[i + 1] - new_T[i]) / grid.node_height
        q_cond = -k_eff * grid.node_area * dT_dz
        # Update node temperatures
        if new_m[i] > 0:
            new_T[i] += q_cond * dt / (new_m[i] * cp)
        if new_m[i + 1] > 0:
            new_T[i + 1] -= q_cond * dt / (new_m[i + 1] * cp)

    # 5. Apply mixing model
    if mixing_model == "ideal":
        new_T = _ideal_mixing(new_T, new_m)
    elif mixing_model == "stratified":
        new_T = _stratified_mixing(new_T, new_m, grid.node_height, cp)

    # Create new grid with updated state
    new_grid = TankGrid(n, grid.volume_total, grid.height, grid.diameter)
    new_grid.T = new_T
    new_grid.m = new_m
    new_grid.quality = grid.quality.copy()

    # Ledger
    ledger = {
        "component": "tank_step",
        "dt": dt,
        "Q_in": Q_in,
        "Q_out": Q_out,
        "Q_loss": Q_loss,
        "m_dot_in": m_dot_in,
        "m_dot_out": m_dot_out,
        "T_avg_before": grid.average_temperature(),
        "T_avg_after": new_grid.average_temperature(),
    }

    return new_grid, ledger


def _ideal_mixing(T: List[float], m: List[float]) -> List[float]:
    """Ideal mixing - uniform temperature across all nodes with mass."""
    total_mass = sum(m)
    if total_mass == 0:
        return T
    total_energy = sum(m[i] * T[i] for i in range(len(T)))
    T_uniform = total_energy / total_mass
    return [T_uniform if m[i] > 0 else T[i] for i in range(len(T))]


def _stratified_mixing(T: List[float], m: List[float], node_height: float, cp: float) -> List[float]:
    """Stratified mixing - only mix adjacent nodes if unstable."""
    n = len(T)
    new_T = T.copy()
    for i in range(n - 1):
        # If lower node is hotter than upper node, mix them
        if new_T[i + 1] > new_T[i] and m[i] > 0 and m[i + 1] > 0:
            total_m = m[i] + m[i + 1]
            new_T[i] = new_T[i + 1] = (m[i] * T[i] + m[i + 1] * T[i + 1]) / total_m
    return new_T


def tank_series_step(
    grid: TankGrid,
    time_series: Dict[str, list],
    dt: float,
    registry: Dict[str, Any],
) -> Tuple[List[TankGrid], List[Dict[str, Any]]]:
    """Run tank step over a time series."""
    grids = [grid]
    ledgers = []
    current_grid = grid

    n_steps = len(time_series.get("Q_in", []))
    for i in range(n_steps):
        step_inputs = {k: v[i] for k, v in time_series.items() if isinstance(v, list)}
        current_grid, ledger = tank_step(current_grid, dt, registry=registry, **step_inputs)
        grids.append(current_grid)
        ledgers.append(ledger)

    return grids, ledgers
