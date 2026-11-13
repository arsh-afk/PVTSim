"""Reporting module tests."""

from __future__ import annotations

import json

from aquasolar.reporting.metrics import compute_metrics, generate_report, summary_dashboard
from aquasolar.reporting.dashboard import generate_html_dashboard, generate_json_report


class TestComputeMetrics:
    """Tests for metrics computation."""

    def test_compute_metrics_basic(self):
        results = {
            "energy_summary": {"P_pvt_total": 100.0, "Q_u_total": 500.0},
            "electrical_summary": {"self_consumption": 0.8, "P_pvt_sum": 90.0, "P_grid_import_sum": 10.0},
            "tank_history": [{"top_T": 293.15}, {"top_T": 298.15}],
            "duration": 100.0,
            "treatment_summary": {"pathway_counts": {"A": 10, "B": 5}},
        }
        registry = {}
        metrics = compute_metrics(results, registry)
        assert "M-PV-01" in metrics
        assert metrics["M-PV-01"] == 100.0

    def test_all_metrics_returned(self):
        results = {}
        registry = {}
        metrics = compute_metrics(results, registry)
        assert len(metrics) > 0


class TestGenerateReport:
    """Tests for report generation."""

    def test_generate_report_json(self):
        results = {"duration": 100.0, "total_steps": 10, "energy_summary": {}}
        metrics = {"M-PV-01": 100.0}
        registry = {}

        report = generate_report(results, metrics, registry, format="json")
        data = json.loads(report)
        assert "simulation" in data

    def test_generate_report_text(self):
        results = {"duration": 100.0, "total_steps": 10}
        metrics = {"M-PV-01": 100.0}
        registry = {}

        report = generate_report(results, metrics, registry, format="text")
        assert "Duration:" in report


class TestDashboard:
    """Tests for dashboard generation."""

    def test_summary_dashboard(self):
        results = {"treatment_summary": {"pathway_counts": {"A": 10}}}
        metrics = {"M-PV-01": 100.0, "M-TH-01": 500.0, "M-TH-03": 5.0, "M-EL-03": 0.8}
        dashboard = summary_dashboard(results, metrics)
        assert dashboard["electrical_energy_j"] == 100.0
        assert dashboard["thermal_energy_j"] == 500.0

    def test_html_dashboard(self):
        results = {"duration": 100.0, "total_steps": 10}
        metrics = {"M-PV-01": 100.0}
        html = generate_html_dashboard(results, metrics)
        assert "<html" in html
        assert "100.00 J" in html

    def test_json_report(self):
        results = {"duration": 100.0}
        metrics = {"M-PV-01": 100.0}
        registry = {}
        report = generate_json_report(results, metrics, registry)
        data = json.loads(report)
        assert "simulation" in data
