"""PVT thermal output module.

Per P3-6: Q_u from inlet temperature, flow, effective irradiance, ambient, wind (EQ-PVT-02).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def useful_heat(
    T_f_in: float,
    m_dot: float,
    G_eff: float,
    P_el: float,
    T_amb: float,
    wind_speed: float,
    A: float,
    tau_alpha: float,
    F_R: float,
    U_L: float,
    U_L_wind_dep: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, Any]]:
    """Calculate PVT useful thermal energy.

    EQ-PVT-02: Q_u = A * F_R * [S - U_L * (T_f_in - T_amb)]
    where S = tau_alpha * G_eff - P_el / A

    Args:
        T_f_in: Fluid inlet temperature (K)
        m_dot: Mass flow rate (kg/s)
        G_eff: Effective plane-of-array irradiance (W/m²)
        P_el: Electrical power (W)
        T_amb: Ambient temperature (K)
        wind_speed: Wind speed (m/s)
        A: Collector area (m²)
        tau_alpha: Transmittance-absorptance product
        F_R: Heat-removal factor
        U_L: Overall heat-loss coefficient (W/(m²·K))
        U_L_wind_dep: Optional wind dependence parameters

    Returns:
        (Q_u in W, ledger dict)
    """
    # Calculate solar flux
    S = tau_alpha * G_eff - P_el / A

    # Apply wind-dependent U_L if specified
    if U_L_wind_dep and wind_speed > 0:
        U_L_effective = U_L * (1.0 + U_L_wind_dep.get("wind_coeff", 0.0) * wind_speed)
    else:
        U_L_effective = U_L

    # Calculate useful heat
    Q_u = A * F_R * (S - U_L_effective * (T_f_in - T_amb))

    # Ledger record
    ledger = {
        "component": "pvt_thermal",
        "quantity": "useful_heat",
        "in": G_eff * A,
        "out": Q_u,
        "generated": Q_u,
        "residual": 0.0,
    }

    return Q_u, ledger


def useful_heat_no_flow(
    G_eff: float,
    T_amb: float,
    A: float,
    tau_alpha: float,
    U_L: float,
) -> Tuple[float, Dict[str, Any]]:
    """Calculate useful heat when flow is zero (stagnation).

    Returns zero thermal output but allows temperature calculation.
    """
    return 0.0, {
        "component": "pvt_thermal",
        "quantity": "useful_heat",
        "in": 0.0,
        "out": 0.0,
        "generated": 0.0,
        "residual": 0.0,
    }
