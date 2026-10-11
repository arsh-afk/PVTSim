"""Pydantic schemas for input validation."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class UncertaintySpec(BaseModel):
    kind: Optional[str] = None  # absolute, relative, none
    value: Optional[float] = None
    distribution: Optional[str] = None  # normal, uniform, triangular, lognormal, none


class ValidRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class ParameterEntry(BaseModel):
    """Single parameter entry from a YAML parameter file."""

    id: str
    value: Any = None
    unit: Optional[str] = None
    source_type: Optional[str] = None  # measured, datasheet, literature, standard, assumption
    source_ref: Optional[str] = None
    uncertainty: Optional[UncertaintySpec] = None
    valid_range: Optional[ValidRange] = None
    status: str = "draft"  # draft or confirmed or not_applicable
    entered_by: Optional[str] = None
    entered_on: Optional[str] = None

    @field_validator("status")
    @classmethod
    def status_must_be_valid(cls, v: str) -> str:
        if v not in ("draft", "confirmed", "not_applicable"):
            raise ValueError(
                f"status must be 'draft', 'confirmed', or 'not_applicable', got '{v}'"
            )
        return v

    @field_validator("source_type")
    @classmethod
    def source_type_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        allowed = {"measured", "datasheet", "literature", "standard", "assumption"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}, got '{v}'")
        return v


class RegistryError(Exception):
    """Raised when registry consistency checks fail."""

    pass
