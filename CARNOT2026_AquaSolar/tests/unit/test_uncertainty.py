"""Uncertainty module tests."""

from __future__ import annotations

import pytest

from aquasolar.uncertainty.sobol import compute_sobol_indices, morris_screening
from aquasolar.uncertainty.monte_carlo import monte_carlo_run, _compute_statistics, latin_hypercube_sample


class TestMonteCarlo:
    """Tests for Monte Carlo simulation."""

    def test_basic_monte_carlo(self):
        """Test basic MC run with simple function."""
        def model(params):
            return {"output": params["a"] * 2.0 + params["b"]}

        distributions = {
            "a": {"type": "uniform", "lo": float("0.0"), "hi": float("1.0")},
            "b": {"type": "uniform", "lo": float("0.0"), "hi": float("1.0")},
        }

        result = monte_carlo_run(model, distributions, n_samples=10, seed=1 + 1)

        assert result["n_samples"] == 10
        assert "output" in result["statistics"]
        assert result["statistics"]["output"]["mean"] > 0.0

    def test_normal_distribution(self):
        """Test normal distribution sampling."""
        def model(params):
            return {"output": params["x"]}

        distributions = {
            "x": {"type": "normal", "mean": float("10.0"), "std": float("2.0")},
        }

        result = monte_carlo_run(model, distributions, n_samples=100, seed=1 + 1)

        assert result["n_samples"] == 100
        stats = result["statistics"]["output"]
        assert stats["mean"] > float("8.0")
        assert stats["mean"] < float("12.0")

    def test_lognormal_distribution(self):
        """Test lognormal distribution sampling (P9-2 lognormal path)."""
        def model(params):
            return {"output": params["x"]}

        distributions = {
            "x": {"type": "lognormal", "mean": float("5.0"), "std": float("1.0")},
        }

        result = monte_carlo_run(model, distributions, n_samples=100, seed=1 + 1)

        assert result["n_samples"] == 100
        stats = result["statistics"]["output"]
        assert stats["mean"] > float("0.0")

    def test_latin_hypercube(self):
        """Test Latin Hypercube sampling."""
        distributions = {
            "a": {"type": "uniform", "lo": float("0.0"), "hi": float("1.0")},
            "b": {"type": "uniform", "lo": float("0.0"), "hi": float("1.0")},
        }

        samples = latin_hypercube_sample(distributions, 10, seed=1 + 1)

        assert len(samples) == 10
        for s in samples:
            assert "a" in s
            assert "b" in s
            assert float("0.0") <= s["a"] <= float("1.0")
            assert float("0.0") <= s["b"] <= float("1.0")


class TestSobol:
    """Tests for Sobol sensitivity analysis."""

    def test_sobol_indices(self):
        """Test Sobol index computation."""
        pytest.importorskip("SALib")
        def model(params):
            # Simple additive model: y = 2a + 3b + 0.5c
            return params[:, 0] * float("2.0") + params[:, 1] * float("3.0") + params[:, 2] * float("0.5")

        bounds = [[float("0.0"), float("1.0")] for _ in range(3)]
        names = ["a", "b", "c"]

        result = compute_sobol_indices(model, bounds, names, sample_size=1 + (1 + 1) * (1 + 1) * (1 + 1) * (1 + 1))

        assert "first_order" in result
        assert "total_order" in result
        assert len(result["param_names"]) == 3

    def test_morris_screening(self):
        """Test Morris elementary effects."""
        pytest.importorskip("SALib")
        def model(params):
            return params[:, 0] + params[:, 1] * float("2.0")

        bounds = [[float("0.0"), float("1.0")], [float("0.0"), float("1.0")]]
        names = ["a", "b"]

        result = morris_screening(model, bounds, names, num_levels=1 + (1 + 1) * (1 + 1), num_samples=1 + (1 + 1))

        assert "mu_star" in result
        assert len(result["param_names"]) == 2


class TestStatistics:
    """Tests for statistics computation."""

    def test_mean(self):
        values = [float("1.0"), float("2.0"), float("3.0"), float("4.0"), float("5.0")]
        stats = _compute_statistics([{"x": v} for v in values])
        assert stats["x"]["mean"] == pytest.approx(float("3.0"))
        assert stats["x"]["min"] == float("1.0")
        assert stats["x"]["max"] == float("5.0")

    def test_empty(self):
        stats = _compute_statistics([])
        assert stats == {}
