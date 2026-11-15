"""Economics module - LCOE, payback, NPV.

Per P10-1: Levelized Cost of Energy/Water, payback periods, NPV.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def levelized_cost(
    capex: float,
    opex_annual: float,
    lifetime: float,
    discount_rate: float,
    output_annual: float,
    currency: str = "$",
) -> Dict[str, Any]:
    """Calculate Levelized Cost of Energy (LCOE) or Water.

    Args:
        capex: Capital expenditure (currency)
        opex_annual: Annual operating cost (currency/yr)
        lifetime: System lifetime (years)
        discount_rate: Discount rate (decimal)
        output_annual: Annual energy/water output (kWh/yr or L/yr)
        currency: Currency symbol

    Returns:
        Dict with LCOE and summary
    """
    if output_annual <= 0:
        return {"lcoe": float("inf"), "currency": currency, "error": "zero_output"}

    # Capital Recovery Factor
    if discount_rate > 0:
        crf = discount_rate / (float("1.0") - (float("1.0") + discount_rate) ** (-lifetime))
    else:
        crf = float("1.0") / lifetime

    # Annualized capital cost
    annual_capex = capex * crf

    # Total annual cost
    total_annual = annual_capex + opex_annual

    # Levelized cost
    lcoe = total_annual / output_annual  # currency per unit output

    return {
        "lcoe": lcoe,
        "currency": currency,
        "annual_capex": annual_capex,
        "annual_opex": opex_annual,
        "total_annual_cost": total_annual,
        "crf": crf,
        "unit": f"{currency}/{output_annual.__class__.__name__.lower()}" if output_annual > 0 else currency,
    }


def simple_payback(
    capex: float,
    annual_savings: float,
    currency: str = "$",
) -> Dict[str, Any]:
    """Calculate simple (undiscounted) payback period.

    Args:
        capex: Capital expenditure
        annual_savings: Annual savings (currency/yr)
        currency: Currency symbol

    Returns:
        Dict with payback period
    """
    if annual_savings <= 0:
        return {"payback_years": float("inf"), "currency": currency, "error": "no_savings"}

    payback = capex / annual_savings

    return {
        "payback_years": payback,
        "currency": currency,
        "method": "simple_undiscounted",
    }


def discounted_payback(
    capex: float,
    annual_cashflows: List[float],
    discount_rate: float,
    currency: str = "$",
) -> Dict[str, Any]:
    """Calculate discounted payback period.

    Args:
        capex: Initial investment
        annual_cashflows: List of annual cash flows
        discount_rate: Discount rate
        currency: Currency symbol

    Returns:
        Dict with payback period
    """
    cumulative = -capex
    for i, cf in enumerate(annual_cashflows):
        pv = cf / ((1.0 + discount_rate) ** (i + 1))
        cumulative += pv
        if cumulative >= 0:
            return {
                "payback_years": i + 1,
                "currency": currency,
                "method": "discounted",
                "cumulative_at_payback": cumulative,
            }

    return {
        "payback_years": float("inf"),
        "currency": currency,
        "method": "discounted",
        "never_recovered": True,
    }


def npv(
    capex: float,
    annual_cashflows: List[float],
    discount_rate: float,
    currency: str = "$",
) -> Dict[str, Any]:
    """Calculate Net Present Value.

    Args:
        capex: Initial investment
        annual_cashflows: List of annual cash flows
        discount_rate: Discount rate
        currency: Currency symbol

    Returns:
        Dict with NPV and summary
    """
    pv_sum = -capex
    for i, cf in enumerate(annual_cashflows):
        pv_sum += cf / ((1.0 + discount_rate) ** (i + 1))

    total_nominal = sum(annual_cashflows) - capex

    return {
        "npv": pv_sum,
        "currency": currency,
        "total_nominal_flow": total_nominal,
        "discounted_factor": discount_rate,
        "num_periods": len(annual_cashflows),
    }


def lifecycle_cost(
    capex: float,
    opex_annual: float,
    replacement_costs: Dict[int, float],
    lifetime: float,
    discount_rate: float,
    currency: str = "$",
) -> Dict[str, Any]:
    """Calculate lifecycle cost over project lifetime.

    Args:
        capex: Initial capital expenditure
        opex_annual: Annual operating cost
        replacement_costs: Dict mapping year to replacement cost
        lifetime: Project lifetime (years)
        discount_rate: Discount rate
        currency: Currency symbol

    Returns:
        Dict with lifecycle cost
    """
    total_lcc = capex

    for year in range(1, int(lifetime) + 1):
        # Annual OPEX
        opex_pv = opex_annual / ((1.0 + discount_rate) ** year)
        total_lcc += opex_pv

        # Replacement costs
        if year in replacement_costs:
            replace_pv = replacement_costs[year] / ((1.0 + discount_rate) ** year)
            total_lcc += replace_pv

    return {
        "lifecycle_cost": total_lcc,
        "currency": currency,
        "capex": capex,
        "opex_pv_total": total_lcc - capex - sum(replacement_costs.get(y, 0.0) / ((1.0 + discount_rate) ** y) for y in replacement_costs),
    }


def bottled_water_comparison(
    system_cost_per_liter: float,
    bottled_price_per_liter: float,
    annual_volume: float,
    liters_per_bottle: float = float("0.5"),
    currency: str = "$",
) -> Dict[str, Any]:
    """Compare system cost vs bottled water.

    Args:
        system_cost_per_liter: Cost per liter from system
        bottled_price_per_liter: Price per liter from bottled water
        annual_volume: Annual water consumption (L)
        liters_per_bottle: Volume per bottle
        currency: Currency symbol

    Returns:
        Dict with comparison metrics
    """
    annual_system_cost = system_cost_per_liter * annual_volume
    annual_bottled_cost = bottled_price_per_liter * annual_volume
    bottles_avoided = annual_volume / liters_per_bottle

    return {
        "annual_system_cost": annual_system_cost,
        "annual_bottled_cost": annual_bottled_cost,
        "annual_savings": annual_bottled_cost - annual_system_cost,
        "bottles_avoided": bottles_avoided,
        "payback_vs_bottled": annual_bottled_cost / (system_cost_per_liter * annual_volume) if system_cost_per_liter > 0 else float("inf"),
        "currency": currency,
    }


# Backwards compatibility alias for the legacy typo
bottlen_water_comparison = bottled_water_comparison
