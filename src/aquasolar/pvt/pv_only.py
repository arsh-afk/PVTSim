"""PV-only reference module.

Per P3-7: PV-only reference with same weather, no heat extraction.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .electrical import electrical_output


def pv_only_reference(
    G_eff: float,
    T_amb: float,
    wind_speed: float,
    eta_ref: float,
    T_ref: float,
    beta: float,
    phi_soil: float,
    A: float,
    pv_only_model: str = "simple",
    **params,
) -> Tuple[float, float, Dict[str, Any]]:
    """Calculate PV-only reference output.

    Uses pv_only_reference_model to estimate cell temperature without heat extraction.

    Args:
        G_eff: Effective plane-of-array irradiance (W/m²)
        T_amb: Ambient temperature (K)
        wind_speed: Wind speed (m/s)
        eta_ref: Reference electrical efficiency
        T_ref: Reference cell temperature (K)
        beta: Temperature coefficient
        phi_soil: Soiling factor
        A: Collector area (m²)
        pv_only_model: Model for PV-only cell temperature
        **params: Additional model parameters

    Returns:
        (T_cell_pv_only, P_el_pv_only, ledger)
    """
    # Simple PV-only cell temperature model
    if pv_only_model == "simple":
        # T_cell = T_amb + G_eff * (1 - eta_ref) / (U_L_pv_only)
        # where U_L_pv_only is an effective loss coefficient
        U_L_pv = params.get("U_L_pv_only", float("10.0"))
        T_cell = T_amb + G_eff * (1.0 - eta_ref) / U_L_pv
    elif pv_only_model == "faiman":
        # Faiman model: T_cell = T_amb + G_eff / (alpha + beta * wind)
        alpha = params.get("alpha", float("25.0"))
        beta_wind = params.get("beta_wind", 1.0)
        T_cell = T_amb + G_eff / (alpha + beta_wind * wind_speed)
    else:
        # Default: use ambient temperature
        T_cell = T_amb

    # Calculate PV-only electrical output
    P_el, ledger = electrical_output(
        T_cell=T_cell,
        G_eff=G_eff,
        eta_ref=eta_ref,
        T_ref=T_ref,
        beta=beta,
        phi_soil=phi_soil,
        A=A,
    )

    return T_cell, P_el, ledger
