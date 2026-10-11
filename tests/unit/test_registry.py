"""Unit tests for the registry module."""

from __future__ import annotations

import pytest
from pathlib import Path

from aquasolar.registry import Registry, ParameterEntry, evaluate_required_when
from aquasolar.registry.errors import (
    InputError,
    MissingInputError,
    DraftInputError,
    InvalidInputError,
    format_input_error,
)


class TestEvaluateRequiredWhen:
    """Test required_when expression evaluation."""

    def test_always(self):
        """Test 'always' expression."""
        assert evaluate_required_when("always", {}) is True

    def test_equal_true(self):
        """Test equality with boolean."""
        registry = {"tank.aux_present": True}
        assert evaluate_required_when("tank.aux_present == true", registry) is True
        assert evaluate_required_when("tank.aux_present == false", registry) is False

    def test_equal_string(self):
        """Test equality with string."""
        registry = {"site.timezone": "Asia/Dubai"}
        assert evaluate_required_when("site.timezone == Asia/Dubai", registry) is True
        assert evaluate_required_when("site.timezone == America/New_York", registry) is False

    def test_not_equal(self):
        """Test inequality."""
        registry = {"numerics.tank_scheme": "explicit"}
        assert evaluate_required_when("numerics.tank_scheme != substepped_explicit", registry) is True
        assert evaluate_required_when("numerics.tank_scheme == substepped_explicit", registry) is False

    def test_in_list(self):
        """Test membership in list."""
        registry = {"tank.charge_method": "direct_fluid_exchange"}
        assert evaluate_required_when(
            "tank.charge_method in direct_fluid_exchange,immersed_coil_effectiveness",
            registry,
        ) is True
        assert evaluate_required_when("tank.charge_method in external_hx_effectiveness", registry) is False

    def test_missing_param(self):
        """Test when referenced parameter is missing."""
        registry = {}
        # Should return False to avoid hard failures
        assert evaluate_required_when("missing.param == true", registry) is False


class TestInputErrorFormat:
    """Test error message formatting."""

    def test_format_input_error(self):
        """Test the mandated error format from Section 3.4."""
        msg = format_input_error(
            file_path="inputs/parameters/site.yaml",
            location="site.latitude",
            problem="Missing required parameter",
            expected="confirmed value with unit",
            found="empty",
            fix="Add site.latitude to inputs/parameters/site.yaml with status=confirmed",
        )
        assert "INPUT ERROR" in msg
        assert "file:" in msg
        assert "location:" in msg
        assert "problem:" in msg
        assert "expected:" in msg
        assert "found:" in msg
        assert "fix:" in msg
