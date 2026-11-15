"""Economics module tests."""

from __future__ import annotations

import pytest

from aquasolar.economics.lcoe import (
    levelized_cost,
    simple_payback,
    discounted_payback,
    npv,
    lifecycle_cost,
    bottled_water_comparison,
    bottlen_water_comparison,
)


class TestLevelizedCost:
    """Tests for LCOE/LCOWh calculation."""

    def test_basic_lcoe(self):
        result = levelized_cost(
            capex=float("10000.0"),
            opex_annual=float("500.0"),
            lifetime=float("20.0"),
            discount_rate=float("0.05"),
            output_annual=float("5000.0"),
        )

        assert result["lcoe"] > 0.0
        assert result["currency"] == "$"

    def test_zero_output(self):
        result = levelized_cost(
            capex=float("10000.0"),
            opex_annual=float("0.0"),
            lifetime=float("20.0"),
            discount_rate=float("0.05"),
            output_annual=float("0.0"),
        )
        assert result["lcoe"] == float("inf")


class TestPayback:
    """Tests for payback period calculations."""

    def test_simple_payback(self):
        result = simple_payback(
            capex=float("10000.0"),
            annual_savings=float("2000.0"),
        )
        assert result["payback_years"] == float("5.0")

    def test_discounted_payback(self):
        cashflows = [float("3000.0")] * 10
        result = discounted_payback(
            capex=float("10000.0"),
            annual_cashflows=cashflows,
            discount_rate=float("0.05"),
        )
        assert result["payback_years"] <= 10

    def test_no_savings(self):
        result = simple_payback(capex=float("10000.0"), annual_savings=float("0.0"))
        assert result["payback_years"] == float("inf")


class TestNPV:
    """Tests for NPV calculation."""

    def test_positive_npv(self):
        cashflows = [float("5000.0")] * 5
        result = npv(
            capex=float("10000.0"),
            annual_cashflows=cashflows,
            discount_rate=float("0.05"),
        )
        assert result["npv"] > 0.0

    def test_negative_npv(self):
        cashflows = [float("1000.0")] * 5
        result = npv(
            capex=float("10000.0"),
            annual_cashflows=cashflows,
            discount_rate=float("0.05"),
        )
        assert result["npv"] < 0.0


class TestLifecycleCost:
    """Tests for lifecycle cost."""

    def test_basic_lcc(self):
        result = lifecycle_cost(
            capex=float("5000.0"),
            opex_annual=float("500.0"),
            replacement_costs={},
            lifetime=float("10.0"),
            discount_rate=float("0.05"),
        )
        assert result["lifecycle_cost"] > float("5000.0")

    def test_with_replacement(self):
        result = lifecycle_cost(
            capex=float("5000.0"),
            opex_annual=float("500.0"),
            replacement_costs={5: float("1000.0")},
            lifetime=float("10.0"),
            discount_rate=float("0.05"),
        )
        assert result["lifecycle_cost"] > float("6000.0")


class TestBottledWater:
    """Tests for bottled water comparison."""

    def test_savings_calculation(self):
        result = bottled_water_comparison(
            system_cost_per_liter=float("0.50"),
            bottled_price_per_liter=float("1.00"),
            annual_volume=float("1000.0"),
        )
        assert result["annual_savings"] > 0.0
        assert result["bottles_avoided"] > 0.0

    def test_legacy_bottlen_alias(self):
        result = bottlen_water_comparison(
            system_cost_per_liter=float("0.50"),
            bottled_price_per_liter=float("1.00"),
            annual_volume=float("1000.0"),
        )
        assert result["annual_savings"] > 0.0
