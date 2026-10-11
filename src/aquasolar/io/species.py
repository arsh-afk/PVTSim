"""Species registry validation for water quality data."""

from __future__ import annotations

from typing import Any, Dict, Set


def validate_species_registry(
    species_registry: pd.DataFrame,
    data_sources: Dict[str, Any],
) -> list[str]:
    """Validate that all species_ids in data sources exist in the registry.

    Args:
        species_registry: DataFrame with species_id column
        data_sources: Dict of {name: DataFrame} for all time series and tables

    Returns:
        List of validation error messages (empty if all valid)
    """
    errors = []

    # Get valid species IDs from registry
    if "species_id" not in species_registry.columns:
        errors.append("species_registry missing 'species_id' column")
        return errors

    valid_species: Set[str] = set(species_registry["species_id"].dropna().unique())

    # Check each data source
    for source_name, df in data_sources.items():
        if "species_id" not in df.columns:
            continue

        found_species = set(df["species_id"].dropna().unique())
        unknown_species = found_species - valid_species

        if unknown_species:
            errors.append(
                f"{source_name}: unknown species_id(s): {sorted(unknown_species)}"
            )

    return errors
