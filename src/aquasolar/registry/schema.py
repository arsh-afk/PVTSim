"""Pydantic schemas for input validation."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class UncertaintySpec(BaseModel):
    kind: str = "none"  # absolute, relative, none
    value: Optional[float] = None
    distribution: str = "none"  # normal, uniform, triangular, lognormal, none


class ValidRange(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None


class ParameterEntry(BaseModel):
    """Single parameter entry from a YAML parameter file."""

    id: str
    value: Any
    unit: str
    source_type: str  # measured, datasheet, literature, standard, assumption
    source_ref: str
    uncertainty: UncertaintySpec = Field(default_factory=UncertaintySpec)
    valid_range: Optional[ValidRange] = None
    status: str = "draft"  # draft or confirmed
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
    def source_type_must_be_valid(cls, v: str) -> str:
        allowed = {"measured", "datasheet", "literature", "standard", "assumption"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}, got '{v}'")
        return v


class RegistryError(Exception):
    """Raised when registry consistency checks fail."""

    pass
