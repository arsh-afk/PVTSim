"""PVT electrical output module.

Per P3-5: P_el from cell temperature, effective irradiance and registry values (EQ-PVT-01).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple


def electrical_output(
    T_cell: float,
    G_eff: float,
    eta_ref: float,
    T_ref: float,
    beta: float,
    phi_soil: float,
    A: float,
    f_irr: float = 1.0,
    f_mpp: float = 1.0,
) -> Tuple[float, Dict[str, Any]]:
    """Calculate PVT electrical output.

    EQ-PVT-01: P_el = eta_ref * [1 - beta * (T_c - T_ref)] * phi_soil * G_eff * A * f_irr * f_mpp

    Args:
        T_cell: Cell temperature (K)
        G_eff: Effective plane-of-array irradiance (W/m²)
        eta_ref: Reference electrical efficiency
        T_ref: Reference cell temperature (K)
        beta: Temperature coefficient of efficiency (1/K)
        phi_soil: Soiling factor
        A: Collector area (m²)
        f_irr: Irradiance correction factor
        f_mpp: MPP tracking factor

    Returns:
        (P_el in W, ledger dict)
    """
    # Calculate electrical efficiency at operating conditions
    eta = eta_ref * (1.0 - beta * (T_cell - T_ref))

    # Ensure efficiency is non-negative
    eta = max(0.0, eta)

    # Calculate electrical power
    P_el = eta * phi_soil * G_eff * A * f_irr * f_mpp

    # Ledger record
    ledger = {
        "component": "pvt_electrical",
        "quantity": "electrical_power",
        "in": G_eff * A,  # incident solar power
        "out": P_el,
        "generated": P_el,
        "residual": 0.0,
    }

    return P_el, ledger


def electrical_output_series(
    T_cell_series: list,
    G_eff_series: list,
    eta_ref: float,
    T_ref: float,
    beta: float,
    phi_soil_series: list,
    A: float,
) -> list:
    """Calculate electrical output for a series of time steps."""
    results = []
    for T_cell, G_eff, phi_soil in zip(T_cell_series, G_eff_series, phi_soil_series):
        P_el, _ = electrical_output(T_cell, G_eff, eta_ref, T_ref, beta, phi_soil, A)
        results.append(P_el)
    return results
