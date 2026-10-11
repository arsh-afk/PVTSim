"""Unit tests for the units module."""

from __future__ import annotations

import pytest

from aquasolar.units import parse_temperature, parse_temperature_difference


class TestTemperatureParsing:
    """Test temperature and temperature difference parsing."""

    def test_parse_kelvin(self):
        """Test Kelvin input."""
        assert parse_temperature(298.15, "K") == pytest.approx(298.15)

    def test_parse_celsius(self):
        """Test Celsius input."""
        assert parse_temperature(25.0, "degC") == pytest.approx(298.15)

    def test_parse_temperature_difference_celsius(self):
        """Test that temperature differences are preserved."""
        assert parse_temperature_difference(10.0, "degC") == pytest.approx(10.0)

    def test_parse_temperature_difference_kelvin(self):
        """Test temperature difference in Kelvin."""
        assert parse_temperature_difference(10.0, "K") == pytest.approx(10.0)
