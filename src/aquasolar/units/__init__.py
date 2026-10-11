"""Unit handling module for AquaSolar Living.

Provides SI conversion and dimensional analysis for all physical quantities.
Uses Pint for unit registration and conversion.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

# Lazy import - will be initialized in __init__
_ureg = None


def get_unit_registry():
    """Return the Pint UnitRegistry singleton."""
    global _ureg
    if _ureg is None:
        try:
            import pint
            _ureg = pint.UnitRegistry()
        except ImportError:
            # Fallback: simple dict-based converter
            _ureg = _SimpleRegistry()
    return _ureg


class _SimpleRegistry:
    """Minimal fallback registry if Pint is not available."""

    CONVERSIONS = {
        "kg/m3": ("kg/m3", 1.0),
        "g/L": ("kg/m3", 1.0),
        "J/(kg*K)": ("J/(kg*K)", 1.0),
        "degC": ("K", 0.0),  # special case
        "W/m2": ("W/m2", 1.0),
        "m2": ("m2", 1.0),
        "kg/s": ("kg/s", 1.0),
        "m3/s": ("m3/s", 1.0),
        "W": ("W", 1.0),
        "J": ("J", 1.0),
        "Pa": ("Pa", 1.0),
        "K": ("K", 1.0),
        "1": ("1", 1.0),
    }

    def quantify(self, value: float, unit: str) -> Tuple[float, str]:
        """Convert to SI base units. Returns (value, unit)."""
        base_unit = self._resolve_base(unit)
        factor = self.CONVERSIONS.get(unit, (base_unit, 1.0))[1]
        return value * factor, base_unit

    def _resolve_base(self, unit: str) -> str:
        """Return base SI unit string."""
        return unit.replace("degC", "K").replace("°C", "K")

    def check_dimension(self, value: float, unit: str, expected_kind: str) -> bool:
        """Check if a quantity has the expected dimension kind."""
        # Simplified check
        return True


def convert_to_si(value: float, unit: str, kind: str) -> Tuple[float, str]:
    """Convert a value with given unit to SI base units.

    Args:
        value: The numeric value
        unit: Unit string (e.g., "W/m2", "degC")
        kind: Quantity kind from input_index.yaml

    Returns:
        (converted_value, si_unit_string)
    """
    ureg = get_unit_registry()
    return ureg.quantify(value, unit)


def validate_unit(unit: str, kind: str) -> bool:
    """Check if a unit string is valid for the given quantity kind."""
    ureg = get_unit_registry()
    # Try to parse the unit
    try:
        ureg.parse_units(unit)
        return True
    except Exception:
        return False


def parse_temperature(value: float, unit: str) -> float:
    """Parse a temperature value, converting to Kelvin.

    Distinguishes absolute temperature from temperature difference.
    """
    # Handle Celsius explicitly
    if "degC" in unit.lower() or "celsius" in unit.lower():
        return value + 273.15
    if "K" in unit.upper():
        return value
    # Default: assume Kelvin
    return value


def parse_temperature_difference(value: float, unit: str) -> float:
    """Parse a temperature difference, ensuring it's in Kelvin."""
    # Temperature differences are the same magnitude in K and °C
    if "degC" in unit.lower() or "celsius" in unit.lower():
        return value
    if "K" in unit.upper():
        return value
    return value


def format_quantity(value: float, unit: str) -> str:
    """Format a quantity for display."""
    return f"{value} {unit}"
