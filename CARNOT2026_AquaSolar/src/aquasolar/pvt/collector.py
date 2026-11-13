"""PVT collector energy balance module.

Per P3-9: Energy balance with heat extraction and auxiliary heating.
Combines electrical and thermal outputs with storage tank interface.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .electrical import electrical_output
from .thermal import useful_heat, useful_heat_no_flow
from .coupled import coupled_solve
from .pv_only import pv_only_reference


class PVTCoupledResult:
    """Container for coupled PVT solution."""

    def __init__(
        self,
        T_f_out: float,
        T_cell: float,
        P_el: float,
        Q_u: float,
        converged: bool,
        iterations: int,
        T_f_in: float,
        m_dot: float,
        registry: Dict[str, Any],
    ):
        self.T_f_out = T_f_out
        self.T_cell = T_cell
        self.P_el = P_el
        self.Q_u = Q_u
        self.converged = converged
        self.iterations = iterations
        self.T_f_in = T_f_in
        self.m_dot = m_dot
        self.registry = registry

    @property
    def eta_el(self) -> float:
        """Electrical efficiency."""
        if self.registry.get("pvt_th.collector_area", 0) > 0:
            A = self.registry["pvt_th.collector_area"]
            return self.P_el / (self.registry.get("weather.G_poa", 0) * A) if self.registry.get("weather.G_poa", 0) > 0 else 0.0
        return 0.0

    @property
    def eta_th(self) -> float:
        """Thermal efficiency."""
        if self.registry.get("pvt_th.collector_area", 0) > 0:
            A = self.registry["pvt_th.collector_area"]
            return self.Q_u / (self.registry.get("weather.G_poa", 0) * A) if self.registry.get("weather.G_poa", 0) > 0 else 0.0
        return 0.0


def pvt_solve(
    T_in: float,
    m_dot: float,
    G_eff: float,
    T_amb: float,
    wind_speed: float,
    registry: Dict[str, Any],
    use_coupled: bool = True,
) -> PVTCoupledResult:
    """Solve PVT collector for given conditions.

    Args:
        T_in: Collector inlet temperature (K)
        m_dot: Mass flow rate (kg/s)
        G_eff: Effective POA irradiance (W/m²)
        T_amb: Ambient temperature (K)
        wind_speed: Wind speed (m/s)
        registry: Parameter registry
        use_coupled: Whether to solve coupled system or sequential

    Returns:
        PVTCoupledResult with all outputs
    """
    # Use coupled solver
    if use_coupled and m_dot > 0:
        T_out, T_c, P_el, Q_u, converged, iterations = coupled_solve(
            T_in=T_in,
            m_dot=m_dot,
            G_eff=G_eff,
            T_amb=T_amb,
            wind_speed=wind_speed,
            registry=registry,
        )
    else:
        # No flow case
        T_out = T_in
        T_c = T_amb + G_eff / max(registry.get("pvt_th.U_L", float("10.0")), float("0.1"))
        P_el, _ = electrical_output(T_c, G_eff, registry["pvt_el.eta_ref"],
                                     registry["pvt_el.T_ref"], registry["pvt_el.beta"],
                                     registry.get("soiling_factor", 1.0),
                                     registry["pvt_th.collector_area"],
                                     f_mpp=(
                                         registry.get("pvt_el.mpp_efficiency_factor", 1.0)
                                         if registry.get("pvt_el.mpp_assumption")
                                         == "user_efficiency_factor"
                                         else 1.0
                                     ))
        Q_u = 0.0
        converged = True
        iterations = 0

    return PVTCoupledResult(
        T_f_out=T_out,
        T_cell=T_c,
        P_el=P_el,
        Q_u=Q_u,
        converged=converged,
        iterations=iterations,
        T_f_in=T_in,
        m_dot=m_dot,
        registry=registry,
    )


def pvt_series_solve(
    T_in_series: list,
    m_dot_series: list,
    G_eff_series: list,
    T_amb_series: list,
    wind_speed_series: list,
    registry: Dict[str, Any],
    use_coupled: bool = True,
) -> List[PVTCoupledResult]:
    """Solve PVT for a time series."""
    results = []
    for T_in, m_dot, G_eff, T_amb, wind in zip(
        T_in_series, m_dot_series, G_eff_series, T_amb_series, wind_speed_series
    ):
        result = pvt_solve(T_in, m_dot, G_eff, T_amb, wind, registry, use_coupled)
        results.append(result)
    return results
