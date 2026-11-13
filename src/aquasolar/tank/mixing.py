"""Tank mixing module.

Per P4-3: Mixing models for tank stratification.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def ideal_mixing(
    T: List[float],
    m: List[float],
) -> List[float]:
    """Ideal mixing - uniform temperature across all nodes with mass.

    Args:
        T: Temperature array (K)
        m: Mass array (kg)

    Returns:
        New temperature array after mixing
    """
    total_mass = sum(m)
    if total_mass == 0:
        return T
    total_energy = sum(m[i] * T[i] for i in range(len(T)))
    T_uniform = total_energy / total_mass
    return [T_uniform if m[i] > 0 else T[i] for i in range(len(T))]


def stratified_mixing(
    T: List[float],
    m: List[float],
    node_height: float,
    cp: float = float("4180.0"),
) -> List[float]:
    """Stratified mixing - only mix adjacent nodes if unstable (hotter below cooler).

    Args:
        T: Temperature array (K)
        m: Mass array (kg)
        node_height: Height of each node (m)
        cp: Specific heat capacity (J/(kg·K))

    Returns:
        New temperature array after mixing
    """
    n = len(T)
    new_T = T.copy()

    # Check each adjacent pair from top to bottom
    for i in range(n - 1):
        # If lower node is hotter than upper node (unstable stratification), mix them
        if new_T[i + 1] > new_T[i] and m[i] > 0 and m[i + 1] > 0:
            total_m = m[i] + m[i + 1]
            mixed_T = (m[i] * T[i] + m[i + 1] * T[i + 1]) / total_m
            new_T[i] = new_T[i + 1] = mixed_T

    return new_T


def partial_mixing(
    T: List[float],
    m: List[float],
    mixing_fraction: float,
) -> List[float]:
    """Partial mixing - mix a fraction towards uniform temperature.

    Args:
        T: Temperature array (K)
        m: Mass array (kg)
        mixing_fraction: Fraction of ideal mixing to apply (0-1)

    Returns:
        New temperature array after partial mixing
    """
    total_mass = sum(m)
    if total_mass == 0:
        return T
    total_energy = sum(m[i] * T[i] for i in range(len(T)))
    T_uniform = total_energy / total_mass

    new_T = []
    for i in range(len(T)):
        if m[i] > 0:
            new_T.append(T[i] + mixing_fraction * (T_uniform - T[i]))
        else:
            new_T.append(T[i])

    return new_T


def no_mixing(
    T: List[float],
    m: List[float],
) -> List[float]:
    """No mixing - return temperatures unchanged.

    Args:
        T: Temperature array (K)
        m: Mass array (kg)

    Returns:
        Original temperature array
    """
    return T.copy()


def apply_mixing_model(
    T: List[float],
    m: List[float],
    model: str,
    **params,
) -> List[float]:
    """Apply specified mixing model.

    Args:
        T: Temperature array (K)
        m: Mass array (kg)
        model: Mixing model name ("ideal", "stratified", "partial", "none")
        **params: Model-specific parameters

    Returns:
        New temperature array after mixing
    """
    if model == "ideal":
        return ideal_mixing(T, m)
    elif model == "stratified":
        return stratified_mixing(T, m, params.get("node_height", float("0.1")), params.get("cp", float("4180.0")))
    elif model == "partial":
        return partial_mixing(T, m, params.get("mixing_fraction", float("0.1")))
    elif model == "none":
        return no_mixing(T, m)
    else:
        # Default to stratified
        return stratified_mixing(T, m, params.get("node_height", float("0.1")), params.get("cp", float("4180.0")))


def mixing_energy_check(
    T_before: List[float],
    T_after: List[float],
    m: List[float],
    cp: float = float("4180.0"),
) -> Dict[str, float]:
    """Check energy conservation during mixing.

    Args:
        T_before: Temperatures before mixing (K)
        T_after: Temperatures after mixing (K)
        m: Mass array (kg)
        cp: Specific heat capacity (J/(kg·K))

    Returns:
        Dict with energy_before, energy_after, difference
    """
    energy_before = sum(m[i] * cp * T_before[i] for i in range(len(T_before)))
    energy_after = sum(m[i] * cp * T_after[i] for i in range(len(T_after)))
    return {
        "energy_before": energy_before,
        "energy_after": energy_after,
        "difference": energy_after - energy_before,
        "relative_error": abs(energy_after - energy_before) / energy_before if energy_before > 0 else 0.0,
    }
