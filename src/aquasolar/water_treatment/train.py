"""Water treatment train module.

Per P6-2: Assemble stages into complete treatment trains for Pathways A/B/C.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .stages import (
    sediment_filter,
    carbon_filter,
    uv_disinfection,
    ultrafiltration,
    nanofiltration,
    remineralization,
)


def pathway_a(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, Any],
) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """Pathway A: Sediment + Carbon + UV.

    For relatively good source water requiring basic treatment.
    """
    ledgers = []
    quality = quality_in.copy()

    # Stage 1: Sediment filter
    quality, ledger = sediment_filter(flow, quality, dt, parameters.get("sediment", {}))
    ledgers.append(ledger)

    # Stage 2: Carbon filter
    quality, ledger = carbon_filter(flow, quality, dt, parameters.get("carbon", {}))
    ledgers.append(ledger)

    # Stage 3: UV disinfection
    quality, ledger = uv_disinfection(flow, quality, dt, parameters.get("uv", {}))
    ledgers.append(ledger)

    return quality, ledgers


def pathway_b(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, Any],
) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """Pathway B: Sediment + Carbon + UF + UV.

    For source water with higher turbidity/microbial risk.
    """
    ledgers = []
    quality = quality_in.copy()

    # Stage 1: Sediment filter
    quality, ledger = sediment_filter(flow, quality, dt, parameters.get("sediment", {}))
    ledgers.append(ledger)

    # Stage 2: Carbon filter
    quality, ledger = carbon_filter(flow, quality, dt, parameters.get("carbon", {}))
    ledgers.append(ledger)

    # Stage 3: Ultrafiltration
    quality, ledger = ultrafiltration(flow, quality, dt, parameters.get("uf", {}))
    ledgers.append(ledger)

    # Stage 4: UV disinfection
    quality, ledger = uv_disinfection(flow, quality, dt, parameters.get("uv", {}))
    ledgers.append(ledger)

    return quality, ledgers


def pathway_c(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, Any],
) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """Pathway C: NF + Remineralization + UV.

    For source water with high dissolved solids/hardness/contaminants.
    """
    ledgers = []
    quality = quality_in.copy()

    # Stage 1: Nanofiltration
    quality, ledger = nanofiltration(flow, quality, dt, parameters.get("nf", {}))
    ledgers.append(ledger)

    # Stage 2: Remineralization
    quality, ledger = remineralization(flow, quality, dt, parameters.get("remin", {}))
    ledgers.append(ledger)

    # Stage 3: UV disinfection
    quality, ledger = uv_disinfection(flow, quality, dt, parameters.get("uv", {}))
    ledgers.append(ledger)

    return quality, ledgers


def run_treatment_train(
    pathway: str,
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, Any],
) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
    """Run specified treatment pathway.

    Args:
        pathway: Pathway name ("A", "B", "C", "pathway_a", etc.)
        flow: Flow rate (m³/s)
        quality_in: Influent water quality
        dt: Time step (s)
        parameters: All stage parameters

    Returns:
        (effluent_quality, list_of_stage_ledgers)
    """
    pathway_lower = pathway.lower()

    if pathway_lower in ("a", "pathway_a"):
        return pathway_a(flow, quality_in, dt, parameters)
    elif pathway_lower in ("b", "pathway_b"):
        return pathway_b(flow, quality_in, dt, parameters)
    elif pathway_lower in ("c", "pathway_c"):
        return pathway_c(flow, quality_in, dt, parameters)
    else:
        raise ValueError(f"Unknown pathway: {pathway}")


def treatment_train_series(
    pathway: str,
    flow_series: list,
    quality_series: list,
    dt: float,
    parameters: Dict[str, Any],
) -> Tuple[List[Dict[str, float]], List[List[Dict[str, Any]]]]:
    """Run treatment train over a time series."""
    effluent_quality = []
    all_ledgers = []

    for flow, quality_in in zip(flow_series, quality_series):
        quality_out, ledgers = run_treatment_train(pathway, flow, quality_in, dt, parameters)
        effluent_quality.append(quality_out)
        all_ledgers.append(ledgers)

    return effluent_quality, all_ledgers
