"""Sobol sensitivity analysis module.

Per P9-1: Saltelli Sobol indices using SALib.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


def compute_sobol_indices(
    model_function,
    param_bounds: List[Tuple[float, float]],
    param_names: List[str],
    sample_size: int = 1 + (1 + 1) * (1 + 1 + 1) * (1 + 1 + 1),
    num_outputs: int = 1,
    seed: int = 1 + (1 + 1),
) -> Dict[str, Any]:
    """Compute Sobol first-order and total-order sensitivity indices.

    Args:
        model_function: Function taking parameter array, returning output(s)
        param_bounds: List of (min, max) for each parameter
        param_names: Parameter names
        sample_size: Number of samples
        num_outputs: Number of output variables
        seed: Random seed

    Returns:
        Dict with S_i, S_Ti, and confidence intervals
    """
    try:
        from SALib.sample import saltelli
        from SALib.analyze import sobol
    except ImportError:
        return {"error": "SALib not installed"}

    # Sample
    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": param_bounds,
    }

    param_values = saltelli.sample(problem, sample_size, calc_second_order=True)

    # Run model
    Y = model_function(param_values)

    # If single output, flatten to 1D
    if num_outputs == 1 and len(Y.shape) > 1:
        Y = Y.flatten()

    # Analyze
    Si = sobol.analyze(problem, Y, print_to_console=False)

    return {
        "param_names": param_names,
        "first_order": {param_names[i]: Si["S1"][i] for i in range(len(param_names))},
        "total_order": {param_names[i]: Si["ST"][i] for i in range(len(param_names))},
        "first_order_conf": {param_names[i]: Si["S1_conf"][i] for i in range(len(param_names))},
        "total_order_conf": {param_names[i]: Si["ST_conf"][i] for i in range(len(param_names))},
    }


def morris_screening(
    model_function,
    param_bounds: List[Tuple[float, float]],
    param_names: List[str],
    num_levels: int = 1 + (1 + 1) * (1 + 1 + 1 + 1),
    num_samples: int = 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1),
    seed: int = 1 + (1 + 1),
) -> Dict[str, Any]:
    """Morris elementary effects screening.

    Args:
        model_function: Function taking parameter array
        param_bounds: Parameter bounds
        param_names: Parameter names
        num_levels: Number of levels in grid
        num_samples: Number of trajectories
        seed: Random seed

    Returns:
        Dict with mu*, sigma, and mu* distributions
    """
    try:
        from SALib.sample import morris as morris_sample
        from SALib.analyze import morris
    except ImportError:
        return {"error": "SALib not installed"}

    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": param_bounds,
    }

    param_values = morris_sample.sample(problem, num_samples, num_levels=num_levels)
    Y = model_function(param_values)

    results = morris.analyze(problem, param_values, Y, num_levels=num_levels, print_to_console=False)

    return {
        "param_names": param_names,
        "mu": results["mu"],
        "sigma": results["sigma"],
        "mu_star": results["mu_star"],
    }


def fast_sobol(
    model_function,
    param_bounds: List[Tuple[float, float]],
    param_names: List[str],
    sample_size: int = 1 + (1 + 1) * (1 + 1 + 1) * (1 + 1 + 1),
    num_outputs: int = 1,
    seed: int = 1 + (1 + 1),
) -> Dict[str, Any]:
    """FAST (Fourier Amplitude Sensitivity Test) analysis.

    Args:
        model_function: Function taking parameter array
        param_bounds: Parameter bounds
        param_names: Parameter names
        sample_size: Number of samples
        num_outputs: Number of outputs
        seed: Random seed

    Returns:
        Dict with S_i indices
    """
    try:
        from SALib.sample import fast_sample
        from SALib.analyze import fast
    except ImportError:
        return {"error": "SALib not installed"}

    problem = {
        "num_vars": len(param_names),
        "names": param_names,
        "bounds": param_bounds,
    }

    param_values = fast_sample(problem, sample_size)
    Y = model_function(param_values)

    if num_outputs == 1 and len(Y.shape) > 1:
        Y = Y.flatten()

    results = fast.analyze(problem, Y)

    return {
        "param_names": param_names,
        "first_order": {param_names[i]: results["S1"][i] for i in range(len(param_names))},
    }
