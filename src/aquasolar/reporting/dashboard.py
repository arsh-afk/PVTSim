"""Reporting dashboard module."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def generate_html_dashboard(
    simulation_results: Dict[str, Any],
    metrics: Dict[str, Any],
    title: str = "AquaSolar Living Simulation",
) -> str:
    """Generate HTML dashboard for simulation results.

    Args:
        simulation_results: Simulation output
        metrics: Computed metrics
        title: Report title

    Returns:
        HTML string
    """
    summary = metrics.get("M-SC-01", {}) or {}

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2c3e50; }}
        .metric {{ background: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
        .metric-label {{ font-size: 14px; color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #34495e; color: white; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="metric">
        <div class="metric-value">{simulation_results.get('duration', 0):.1f} s</div>
        <div class="metric-label">Simulation Duration ({simulation_results.get('total_steps', 0)} steps)</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.get('M-PV-01', 0):.2f} J</div>
        <div class="metric-label">Electrical Energy Generated (M-PV-01)</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.get('M-TH-01', 0):.2f} J</div>
        <div class="metric-label">Useful Thermal Energy (M-TH-01)</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.get('M-TH-03', 0):.4f} K</div>
        <div class="metric-label">Tank Temperature Rise (M-TH-03)</div>
    </div>
    <div class="metric">
        <div class="metric-value">{metrics.get('M-EL-03', 0):.4f}</div>
        <div class="metric-label">Self-Consumption Fraction (M-EL-03)</div>
    </div>
    <h2>Pathway Distribution</h2>
    <table>
        <tr><th>Pathway</th><th>Steps</th></tr>
"""

    pathway_counts = simulation_results.get("treatment_summary", {}).get("pathway_counts", {})
    for path, count in pathway_counts.items():
        html += f"<tr><td>{path}</td><td>{count}</td></tr>\n"

    html += """
    </table>
    <h2>Full Metrics</h2>
    <table>
        <tr><th>Metric ID</th><th>Value</th></tr>
"""

    for metric_id, value in sorted(metrics.items()):
        html += f"<tr><td>{metric_id}</td><td>{value:.6f}</td></tr>\n"

    html += """
    </table>
</body>
</html>"""

    return html


def generate_json_report(
    simulation_results: Dict[str, Any],
    metrics: Dict[str, Any],
    registry: Dict[str, Any],
) -> str:
    """Generate JSON report.

    Args:
        simulation_results: Simulation output
        metrics: Computed metrics
        registry: Parameter registry

    Returns:
        JSON string
    """
    import json

    report = {
        "title": "AquaSolar Living Simulation Report",
        "simulation": {
            "duration_s": simulation_results.get("duration", 0.0),
            "total_steps": simulation_results.get("total_steps", 0),
            "success": simulation_results.get("success", False),
        },
        "energy": simulation_results.get("energy_summary", {}),
        "electrical": simulation_results.get("electrical_summary", {}),
        "treatment": simulation_results.get("treatment_summary", {}),
        "metrics": metrics,
        "parameters": registry,
    }

    return json.dumps(report, indent=2)
