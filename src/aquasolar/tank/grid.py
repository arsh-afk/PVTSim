"""Tank grid module.

Per P4-1: Tank grid representation and stratification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class TankGrid:
    """Stratified tank grid representation."""

    def __init__(
        self,
        n_nodes: int,
        volume_total: float,
        height: float,
        diameter: float,
    ):
        """Initialize tank grid.

        Args:
            n_nodes: Number of vertical nodes
            volume_total: Total tank volume (m³)
            height: Tank height (m)
            diameter: Tank diameter (m)
        """
        self.n_nodes = n_nodes
        self.volume_total = volume_total
        self.height = height
        self.diameter = diameter

        # Node properties
        self.node_height = height / n_nodes
        self.node_volume = volume_total / n_nodes
        self.node_area = volume_total / height  # Cross-sectional area

        # State arrays
        self.T = [float("293.15")] * n_nodes  # Temperature per node (K)
        self.m = [self.node_volume * float("997.0")] * n_nodes  # Mass per node (kg)
        self.quality = [None] * n_nodes  # Water quality per node

    def get_temperature(self, node: int) -> float:
        """Get temperature at node."""
        return self.T[node]

    def set_temperature(self, node: int, T: float) -> None:
        """Set temperature at node."""
        self.T[node] = T

    def get_mass(self, node: int) -> float:
        """Get mass at node."""
        return self.m[node]

    def set_mass(self, node: int, m: float) -> None:
        """Set mass at node."""
        self.m[node] = m

    def get_volume(self, node: int) -> float:
        """Get volume at node."""
        return self.m[node] / float("997.0")

    def get_energy(self, node: int, cp: float = float("4180.0")) -> float:
        """Get internal energy at node."""
        return self.m[node] * cp * (self.T[node] - float("273.15"))

    def total_energy(self, cp: float = float("4180.0")) -> float:
        """Total internal energy of tank."""
        return sum(self.get_energy(i, cp) for i in range(self.n_nodes))

    def average_temperature(self) -> float:
        """Mass-weighted average temperature."""
        total_mass = sum(self.m)
        if total_mass == 0:
            return float("293.15")
        return sum(self.m[i] * self.T[i] for i in range(self.n_nodes)) / total_mass

    def top_temperature(self) -> float:
        """Temperature at top node."""
        return self.T[0] if self.n_nodes > 0 else float("293.15")

    def bottom_temperature(self) -> float:
        """Temperature at bottom node."""
        return self.T[-1] if self.n_nodes > 0 else float("293.15")


def create_tank_grid(registry: Dict[str, Any]) -> TankGrid:
    """Create tank grid from registry."""
    n_nodes = registry.get("tank.n_nodes", 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1))
    volume_total = registry["tank.volume_total"]
    height = registry["tank.height"]
    diameter = registry["tank.diameter"]
    return TankGrid(n_nodes, volume_total, height, diameter)


def tank_grid_state(grid: TankGrid) -> Dict[str, Any]:
    """Export tank grid state."""
    return {
        "n_nodes": grid.n_nodes,
        "T": grid.T.copy(),
        "m": grid.m.copy(),
        "average_T": grid.average_temperature(),
        "top_T": grid.top_temperature(),
        "bottom_T": grid.bottom_temperature(),
    }
