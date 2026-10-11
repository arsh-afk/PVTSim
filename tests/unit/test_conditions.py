"""Tests for required_when condition evaluation."""

from __future__ import annotations

import pytest

from aquasolar.registry.conditions import evaluate_required_when


class TestConditions:
    """Test required_when grammar evaluation."""

    def test_always(self):
        assert evaluate_required_when("always", {}) is True

    def test_missing_param_returns_false(self):
        """Missing referenced params should not crash."""
        result = evaluate_required_when("some.param == true", {})
        assert result is False

    def test_string_equality(self):
        reg = {"site.timezone": "Asia/Dubai"}
        assert evaluate_required_when("site.timezone == Asia/Dubai", reg) is True
        assert evaluate_required_when("site.timezone == America/New_York", reg) is False

    def test_int_equality(self):
        reg = {"tank.node_count": 10}
        assert evaluate_required_when("tank.node_count == 10", reg) is True
        assert evaluate_required_when("tank.node_count == 5", reg) is False

    def test_bool_equality(self):
        reg = {"tank.safety_policy": True}
        assert evaluate_required_when("tank.safety_policy == true", reg) is True
        assert evaluate_required_when("tank.safety_policy == false", reg) is False

    def test_membership(self):
        reg = {"tank.charge_method": "direct_fluid_exchange"}
        assert evaluate_required_when(
            "tank.charge_method in direct_fluid_exchange, immersed_coil_effectiveness",
            reg,
        ) is True
        assert evaluate_required_when("tank.charge_method in external_hx_effectiveness", reg) is False

    def test_inequality(self):
        reg = {"numerics.tank_scheme": "explicit"}
        assert evaluate_required_when("numerics.tank_scheme != substepped_explicit", reg) is True
        assert evaluate_required_when("numerics.tank_scheme == substepped_explicit", reg) is False
