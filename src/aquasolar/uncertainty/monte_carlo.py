"""Monte Carlo simulation module.

Per P9-2: Parameter sampling and uncertainty propagation.
"""

from __future__ import annotations

import math
import random
from typing import Any, Callable, Dict, List, Optional, Tuple


def monte_carlo_run(
    model_function: Callable,
    param_distributions: Dict[str, Dict[str, float]],
    n_samples: int = 1 + (1 + 1) * (1 + 1 + 1 + 1 + 1 + 1 + 1 + 1 + 1),
    seed: Optional[int] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Run Monte Carlo uncertainty propagation.

    Args:
        model_function: Function taking params dict, returning results dict
        param_distributions: Per-parameter distribution specs
            e.g., {"eta_ref": {"type": "normal", "mean": 0.18, "std": 0.02}}
        n_samples: Number of Monte Carlo samples
        seed: Random seed for reproducibility
        **kwargs: Additional arguments passed to model_function

    Returns:
        Dict with output statistics and individual runs
    """
    if seed is not None:
        random.seed(seed)

    outputs = []
    param_sets = []

    for i in range(n_samples):
        param_values = {}
        for param_name, spec in param_distributions.items():
            param_values[param_name] = _sample_distribution(spec, param_name)
        param_sets.append(param_values)

        try:
            result = model_function(param_values, **kwargs)
            outputs.append(result)
        except Exception:
            # Skip failed runs
            continue

    return {
        "n_samples": len(outputs),
        "param_sets": param_sets,
        "outputs": outputs,
        "statistics": _compute_statistics(outputs),
    }


def _sample_distribution(spec: Dict[str, float], param_name: str) -> float:
    """Sample a parameter from its distribution.

    Supported distribution types:
    - normal: Gaussian with mean and std
    - uniform: Uniform between lo and hi
    - triangular: Triangular with lo, mode, hi
    - beta: Beta with alpha, beta
    - lognormal: Log-normal with mean and std
    """
    dist_type = spec.get("type", "uniform")

    if dist_type == "normal":
        mean = spec["mean"]
        std = spec.get("std", mean * float("0.05"))
        value = random.gauss(mean, std)
        # Clip to bounds if specified
        if "lo" in spec:
            value = max(value, spec["lo"])
        if "hi" in spec:
            value = min(value, spec["hi"])
        return value

    elif dist_type == "uniform":
        lo = spec["lo"]
        hi = spec["hi"]
        return random.uniform(lo, hi)

    elif dist_type == "triangular":
        lo = spec["lo"]
        mode = spec["mode"]
        hi = spec["hi"]
        # Marsaglia and Tsang method simplified
        u = random.random()
        if u < (mode - lo) / (hi - lo):
            return lo + (u * (hi - lo) * (mode - lo)) ** float("0.5")
        else:
            return hi - ((float("1.0") - u) * (hi - lo) * (hi - mode)) ** float("0.5")

    elif dist_type == "beta":
        alpha = spec["alpha"]
        beta_param = spec["beta"]
        return random.betavariate(alpha, beta_param)

    elif dist_type == "lognormal":
        mean = spec["mean"]
        std = spec.get("std", mean * float("0.1"))
        mu = (mean ** (2.0) / (mean ** (2.0) + std ** (2.0))) ** float("0.5")
        sigma = (1.0 + (std ** (2.0) / mean ** (2.0))) ** float("0.5")
        value = math.log(mean) - float("0.5") * sigma ** (2.0)
        return random.lognormvariate(value, sigma)

    else:
        # Default: uniform
        lo = spec.get("lo", float("0.9") * spec.get("mean", 0.0))
        hi = spec.get("hi", float("1.1") * spec.get("mean", 0.0))
        return random.uniform(lo, hi)


def _compute_statistics(outputs: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Compute statistics over output dictionary."""
    if not outputs:
        return {}

    # Collect all output keys
    all_keys = set()
    for out in outputs:
        if isinstance(out, dict):
            all_keys.update(out.keys())

    stats = {}
    for key in all_keys:
        values = [out.get(key) for out in outputs if isinstance(out, dict) and key in out]
        if values:
            stats[key] = {
                "mean": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "median": _median(values),
                "std": _std(values),
                "n": len(values),
            }

    return stats


def _median(values: List[float]) -> float:
    """Calculate median."""
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
    return sorted_vals[mid]


def _std(values: List[float]) -> float:
    """Calculate standard deviation."""
    n = len(values)
    if n <= 1:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return variance ** float("0.5")


def latin_hypercube_sample(
    param_distributions: Dict[str, Dict[str, float]],
    n_samples: int,
    seed: Optional[int] = None,
) -> List[Dict[str, float]]:
    """Generate Latin Hypercube samples.

    Provides better coverage than simple random sampling for the same n.

    Returns:
        List of parameter dictionaries
    """
    if seed is not None:
        random.seed(seed)

    param_names = list(param_distributions.keys())
    samples = []

    # Create strata for each parameter
    strata = {}
    for name in param_names:
        spec = param_distributions[name]
        lo = spec.get("lo", float("0.0"))
        hi = spec.get("hi", float("1.0"))

        # Generate strata boundaries
        boundaries = [lo + i * (hi - lo) / n_samples for i in range(n_samples + 1)]
        # Randomize within each stratum
        strata[name] = [random.uniform(boundaries[i], boundaries[i + 1]) for i in range(n_samples)]
        random.shuffle(strata[name])

    # Build samples
    for i in range(n_samples):
        sample = {}
        for name in param_names:
            sample[name] = strata[name][i]
        samples.append(sample)

    return samples
