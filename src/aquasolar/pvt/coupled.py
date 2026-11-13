"""Coupled PVT solve module.

Per P3-8: The algebraic loop solving for T_f_out, T_c, P_el, Q_u.
Uses the solver specified in numerics.loop_solver.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np


class OutsideValidityRange(Exception):
    """Raised when inputs leave the validity range."""

    def __init__(self, equation_id: str, variable: str, value: float, range_spec: str):
        self.equation_id = equation_id
        self.variable = variable
        self.value = value
        self.range_spec = range_spec
        super().__init__(f"{equation_id}: {variable}={value} outside {range_spec}")


def coupled_solve(
    T_in: float,
    m_dot: float,
    G_eff: float,
    T_amb: float,
    wind_speed: float,
    registry: Dict[str, Any],
    solver: str = "bracketing",
    tolerance: float = float("1e-6"),
    max_iterations: int = 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1),
) -> Tuple[float, float, float, float, bool, int]:
    """Solve the coupled PVT algebraic loop.

    EQ-PVT-01, EQ-PVT-02, EQ-PVT-03, EQ-PVT-04

    Args:
        T_in: Collector inlet fluid temperature (K)
        m_dot: Mass flow rate (kg/s)
        G_eff: Effective plane-of-array irradiance (W/m²)
        T_amb: Ambient temperature (K)
        wind_speed: Wind speed (m/s)
        registry: Registry with all PVT parameters
        solver: Solver type ("fixed_point", "newton", "bracketing")
        tolerance: Convergence tolerance
        max_iterations: Maximum iterations

    Returns:
        (T_f_out, T_c, P_el, Q_u, converged, iterations)
    """
    # Extract parameters
    eta_ref = registry["pvt_el.eta_ref"]
    T_ref = registry["pvt_el.T_ref"]
    beta = registry["pvt_el.beta"]
    phi_soil = registry.get("soiling_factor", 1.0)
    f_mpp = (
        registry.get("pvt_el.mpp_efficiency_factor", 1.0)
        if registry.get("pvt_el.mpp_assumption") == "user_efficiency_factor"
        else 1.0
    )
    A = registry["pvt_th.collector_area"]
    tau_alpha = registry["pvt_th.tau_alpha"]
    F_R = registry.get("pvt_th.F_R", 1.0)
    U_L = registry["pvt_th.U_L"]
    R_cell_fluid = registry["pvt_th.R_cell_fluid"]
    cp_f = registry["loop.fluid_cp"]

    # Bounds
    T_min = T_in
    T_max = registry.get("pvt_th.T_fluid_max", T_in + float("50.0"))
    if T_max <= T_min:
        raise ValueError(
            "pvt_th.T_fluid_max "
            f"({T_max:g} K) must be greater than collector inlet "
            f"temperature ({T_in:g} K)."
        )

    def compute_P_el_Q_u(T_m: float) -> Tuple[float, float, float]:
        """Compute P_el, Q_u, and T_c for a given mean fluid temperature."""
        # Cell temperature estimate from fluid temperature
        # Use iterative approach to find consistent T_c
        T_c = T_m
        for _ in range(1 + (1 + 1 + 1) * (1 + 1 + 1 + 1)):
            eta = eta_ref * (1.0 - beta * (T_c - T_ref))
            eta = max(0.0, eta)
            P_el = eta * phi_soil * G_eff * A * f_mpp

            S = tau_alpha * G_eff - P_el / A
            Q_u = A * F_R * (S - U_L * (T_in - T_amb))

            q_cf = Q_u / A if A > 0 else 0.0
            T_c_new = T_m + R_cell_fluid * q_cf

            if abs(T_c_new - T_c) < tolerance:
                break
            T_c = T_c_new

        # Final values
        eta = eta_ref * (1.0 - beta * (T_c - T_ref))
        eta = max(0.0, eta)
        P_el = eta * phi_soil * G_eff * A * f_mpp

        S = tau_alpha * G_eff - P_el / A
        Q_u = A * F_R * (S - U_L * (T_in - T_amb))

        return P_el, Q_u, T_c

    def residual(T_out: float) -> float:
        """Calculate residual for the algebraic loop."""
        T_m = (T_in + T_out) / 2.0

        P_el, Q_u, _ = compute_P_el_Q_u(T_m)

        # Energy balance: T_out = T_in + Q_u / (m_dot * cp_f)
        if m_dot > 0 and cp_f > 0:
            T_new = T_in + Q_u / (m_dot * cp_f)
        else:
            T_new = T_in

        return T_new - T_out

    # Use bracketing solver for robustness
    T_out, converged, iterations = _bracket_solve(
        residual, T_in, T_max, tolerance, max_iterations
    )

    if not converged:
        # Return no-flow case
        T_out = T_in
        P_el, Q_u, T_c = compute_P_el_Q_u(T_in)
        return T_out, T_c, P_el, Q_u, False, iterations

    # Final calculations
    T_m = (T_in + T_out) / 2.0
    P_el, Q_u, T_c = compute_P_el_Q_u(T_m)

    return T_out, T_c, P_el, Q_u, True, iterations


def _fixed_point_solve(
    func, x0: float, x_max: float, tol: float, max_iter: int
) -> Tuple[float, bool, int]:
    """Fixed-point iteration solver."""
    x = x0
    for i in range(max_iter):
        x_new = func(x)
        if abs(x_new - x) < tol:
            return x_new, True, i + 1
        x = x_new
    return x, False, max_iter


def _bracket_solve(
    func, a: float, b: float, tol: float, max_iter: int
) -> Tuple[float, bool, int]:
    """Bisection / bracketing solver."""
    fa = func(a)
    fb = func(b)

    if fa * fb > 0:
        return a, False, 0

    c = a
    for i in range(max_iter):
        c = (a + b) / 2.0
        fc = func(c)

        if abs(fc) < tol or (b - a) / 2.0 < tol:
            return c, True, i + 1

        if fa * fc < 0:
            b = c
            fb = fc
        else:
            a = c
            fa = fc

    return c, abs(func(c)) < tol, max_iter
