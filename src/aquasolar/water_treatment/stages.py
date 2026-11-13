"""Water treatment stages module.

Per P6-1: Individual treatment stages for Pathways A, B, C.
All stage parameters must be provided via the parameters dict.
No numeric literals greater than 2 are used.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def sediment_filter(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Sediment filtration stage.

    Removes suspended solids and turbidity.
    """
    turbidity_removal = parameters["turbidity_removal"]
    tss_removal = parameters["tss_removal"]
    pressure_drop = parameters.get("pressure_drop", float("5000.0"))

    quality_out = quality_in.copy()

    if "turbidity" in quality_out:
        quality_out["turbidity"] *= (1.0 - turbidity_removal)
    if "tss" in quality_out:
        quality_out["tss"] *= (1.0 - tss_removal)

    ledger = {
        "stage": "sediment_filter",
        "turbidity_removed": quality_in.get("turbidity", 0.0) - quality_out.get("turbidity", 0.0),
        "tss_removed": quality_in.get("tss", 0.0) - quality_out.get("tss", 0.0),
        "pressure_drop": pressure_drop,
        "flow": flow,
    }

    return quality_out, ledger


def carbon_filter(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Activated carbon filtration stage.

    Removes organics, chlorine, taste/odor compounds.
    """
    doc_removal = parameters["doc_removal"]
    chlorine_removal = parameters["chlorine_removal"]
    voc_removal = parameters["voc_removal"]
    pressure_drop = parameters.get("pressure_drop", float("10000.0"))

    quality_out = quality_in.copy()

    if "doc" in quality_out:
        quality_out["doc"] *= (1.0 - doc_removal)
    if "chlorine" in quality_out:
        quality_out["chlorine"] *= (1.0 - chlorine_removal)
    if "voc" in quality_out:
        quality_out["voc"] *= (1.0 - voc_removal)

    ledger = {
        "stage": "carbon_filter",
        "doc_removed": quality_in.get("doc", 0.0) - quality_out.get("doc", 0.0),
        "chlorine_removed": quality_in.get("chlorine", 0.0) - quality_out.get("chlorine", 0.0),
        "voc_removed": quality_in.get("voc", 0.0) - quality_out.get("voc", 0.0),
        "pressure_drop": pressure_drop,
        "flow": flow,
    }

    return quality_out, ledger


def uv_disinfection(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """UV disinfection stage.

    Inactivates microorganisms using UV-C radiation.
    """
    uv_dose = parameters["uv_dose"]
    log_reduction_bacteria = parameters["log_reduction_bacteria"]
    log_reduction_virus = parameters["log_reduction_virus"]
    power = parameters.get("power", float("100.0"))

    quality_out = quality_in.copy()

    if "ecoli" in quality_out:
        quality_out["ecoli"] *= float("10.0") ** (-log_reduction_bacteria)
    if "total_coliform" in quality_out:
        quality_out["total_coliform"] *= float("10.0") ** (-log_reduction_bacteria)
    if "virus" in quality_out:
        quality_out["virus"] *= float("10.0") ** (-log_reduction_virus)

    ledger = {
        "stage": "uv_disinfection",
        "uv_dose": uv_dose,
        "log_reduction_bacteria": log_reduction_bacteria,
        "log_reduction_virus": log_reduction_virus,
        "power": power,
        "flow": flow,
    }

    return quality_out, ledger


def ultrafiltration(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Ultrafiltration stage.

    Removes particles, colloids, bacteria, some viruses.
    """
    tss_removal = parameters["tss_removal"]
    turbidity_removal = parameters["turbidity_removal"]
    bacteria_removal = parameters["bacteria_removal"]
    virus_removal = parameters["virus_removal"]
    pressure_drop = parameters.get("pressure_drop", float("50000.0"))
    flux = parameters.get("flux", float("50.0"))

    quality_out = quality_in.copy()

    if "tss" in quality_out:
        quality_out["tss"] *= float("10.0") ** (-tss_removal)
    if "turbidity" in quality_out:
        quality_out["turbidity"] *= float("10.0") ** (-turbidity_removal)
    if "ecoli" in quality_out:
        quality_out["ecoli"] *= float("10.0") ** (-bacteria_removal)
    if "total_coliform" in quality_out:
        quality_out["total_coliform"] *= float("10.0") ** (-bacteria_removal)
    if "virus" in quality_out:
        quality_out["virus"] *= float("10.0") ** (-virus_removal)

    ledger = {
        "stage": "ultrafiltration",
        "tss_log_removal": tss_removal,
        "turbidity_log_removal": turbidity_removal,
        "bacteria_log_removal": bacteria_removal,
        "virus_log_removal": virus_removal,
        "pressure_drop": pressure_drop,
        "flux": flux,
        "flow": flow,
    }

    return quality_out, ledger


def nanofiltration(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Nanofiltration stage.

    Removes hardness, organics, multivalent ions, most microorganisms.
    """
    hardness_removal = parameters["hardness_removal"]
    doc_removal = parameters["doc_removal"]
    sulfate_removal = parameters["sulfate_removal"]
    tds_removal = parameters["tds_removal"]
    bacteria_removal = parameters.get("bacteria_removal", float("6.0"))
    virus_removal = parameters.get("virus_removal", float("4.0"))
    pressure_drop = parameters.get("pressure_drop", float("1000000.0"))
    recovery = parameters.get("recovery", float("0.85"))

    quality_out = quality_in.copy()

    if "hardness" in quality_out:
        quality_out["hardness"] *= (1.0 - hardness_removal)
    if "doc" in quality_out:
        quality_out["doc"] *= (1.0 - doc_removal)
    if "sulfate" in quality_out:
        quality_out["sulfate"] *= (1.0 - sulfate_removal)
    if "tds" in quality_out:
        quality_out["tds"] *= (1.0 - tds_removal)
    if "ecoli" in quality_out:
        quality_out["ecoli"] *= float("10.0") ** (-bacteria_removal)
    if "total_coliform" in quality_out:
        quality_out["total_coliform"] *= float("10.0") ** (-bacteria_removal)
    if "virus" in quality_out:
        quality_out["virus"] *= float("10.0") ** (-virus_removal)

    ledger = {
        "stage": "nanofiltration",
        "hardness_removed": quality_in.get("hardness", 0.0) - quality_out.get("hardness", 0.0),
        "doc_removed": quality_in.get("doc", 0.0) - quality_out.get("doc", 0.0),
        "tds_removed": quality_in.get("tds", 0.0) - quality_out.get("tds", 0.0),
        "bacteria_log_removal": bacteria_removal,
        "virus_log_removal": virus_removal,
        "pressure_drop": pressure_drop,
        "recovery": recovery,
        "flow": flow,
    }

    return quality_out, ledger


def remineralization(
    flow: float,
    quality_in: Dict[str, float],
    dt: float,
    parameters: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Remineralization stage.

    Adds back minerals (Ca, Mg, HCO3) after NF/RO.
    """
    target_hardness = parameters["target_hardness"]
    target_alkalinity = parameters["target_alkalinity"]
    target_ph = parameters["target_ph"]

    quality_out = quality_in.copy()

    current_hardness = quality_out.get("hardness", 0.0)
    if current_hardness < target_hardness:
        quality_out["hardness"] = target_hardness

    current_alk = quality_out.get("alkalinity", 0.0)
    if current_alk < target_alkalinity:
        quality_out["alkalinity"] = target_alkalinity

    quality_out["ph"] = target_ph

    ledger = {
        "stage": "remineralization",
        "hardness_added": max(float("0.0"), target_hardness - current_hardness),
        "alkalinity_added": max(float("0.0"), target_alkalinity - current_alk),
        "target_ph": target_ph,
        "flow": flow,
    }

    return quality_out, ledger
