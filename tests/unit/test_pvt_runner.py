"""Tests for the exploratory PVT-only hourly runner."""

from __future__ import annotations

import builtins
import csv
import json

import pytest
import yaml

from aquasolar.pvt.runner import (
    _REQUIRED_PARAMETERS,
    _read_pvt_parameters,
    load_pvt_parameters,
    load_pvt_weather,
    run_pvt_only,
)


def _valid_parameter_entries(
    maximum_temperature: float = float("333.0"),
    maximum_source_ref: str = "test fixture",
) -> list[dict[str, object]]:
    parameter_values = {
        "site.latitude": (float("25.79"), "deg"),
        "site.longitude": (float("55.94"), "deg"),
        "site.elevation": (float("31.1"), "m"),
        "site.collector_tilt": (float("25.0"), "deg"),
        "site.collector_azimuth": (float("0.0"), "deg"),
        "site.azimuth_convention": ("south_zero_east_negative", ""),
        "site.ground_albedo": (float("0.2"), "1"),
        "site.shading_loss_factor": (float("0.0"), "1"),
        "soiling.mode": ("none", ""),
        "pvt_el.eta_ref": (float("0.2"), "1"),
        "pvt_el.T_ref": (float("298.15"), "K"),
        "pvt_el.beta": (float("0.0037"), "1/K"),
        "pvt_el.irradiance_model": ("none", ""),
        "pvt_el.iam_model": ("none", ""),
        "pvt_el.mpp_assumption": ("user_efficiency_factor", ""),
        "pvt_el.mpp_efficiency_factor": (float("0.98"), "1"),
        "pvt_th.collector_area": (float("6.0"), "m2"),
        "pvt_th.thermal_model": ("steady_state_hottel_whillier_form", ""),
        "pvt_th.tau_alpha": (float("0.5"), "1"),
        "pvt_th.F_R": (float("0.8"), "1"),
        "pvt_th.U_L": (float("12.0"), "W/(m2*K)"),
        "pvt_th.U_L_wind_dependence": ("none", ""),
        "pvt_th.R_cell_fluid": (float("0.05"), "K*m2/W"),
        "pvt_th.T_fluid_max": (maximum_temperature, "K"),
        "pvt_th.demo_inlet_temperature": (float("293.15"), "K"),
        "loop.mass_flow_fixed": (float("0.011"), "kg/s"),
        "loop.fluid_cp": (float("4180.0"), "J/(kg*K)"),
    }
    return [
        {
            "id": parameter_id,
            "value": value,
            "unit": unit,
            "status": "confirmed",
            "source_type": "assumption",
            "source_ref": (
                maximum_source_ref
                if parameter_id == "pvt_th.T_fluid_max"
                else "test fixture"
            ),
        }
        for parameter_id, (value, unit) in parameter_values.items()
    ]


def test_pvt_parameter_loader_reports_missing_required_inputs(tmp_path):
    with pytest.raises(ValueError, match="Missing PVT parameters"):
        load_pvt_parameters(tmp_path)


def test_pvt_parameter_loader_captures_value_unit_and_provenance(tmp_path):
    parameter_file = tmp_path / "pvt.yaml"
    parameter_file.write_text(
        yaml.safe_dump({"parameters": _valid_parameter_entries()}),
        encoding="utf-8",
    )

    parameters = load_pvt_parameters(tmp_path)

    assert parameters["_input_snapshot"]["pvt_th.T_fluid_max"] == {
        "value": 333.0,
        "unit": "K",
        "status": "confirmed",
        "source_type": "assumption",
        "source_ref": "test fixture",
    }


def test_pvt_parameter_loader_rejects_placeholder_source_references(tmp_path):
    parameter_file = tmp_path / "pvt.yaml"
    parameter_file.write_text(
        yaml.safe_dump(
            {
                "parameters": _valid_parameter_entries(maximum_source_ref="none")
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError, match="pvt_th.T_fluid_max has no usable source_ref"
    ) as exc_info:
        load_pvt_parameters(tmp_path)
    assert "found 'none'" in str(exc_info.value)


def test_pvt_parameter_loader_rejects_invalid_source_type(tmp_path):
    parameter_file = tmp_path / "pvt.yaml"
    entries = _valid_parameter_entries()
    next(
        entry for entry in entries if entry["id"] == "pvt_th.T_fluid_max"
    )["source_type"] = "invented"
    parameter_file.write_text(
        yaml.safe_dump({"parameters": entries}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid source_type 'invented'"):
        _read_pvt_parameters(tmp_path)


def test_pvt_parameter_loader_rejects_maximum_below_fixed_inlet(
    tmp_path,
):
    parameter_file = tmp_path / "pvt.yaml"
    parameter_file.write_text(
        yaml.safe_dump({"parameters": _valid_parameter_entries(float("273.0"))}),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"T_fluid_max \(273 K\) must be greater than "
        r"pvt_th\.demo_inlet_temperature \(293\.15 K\)",
    ):
        load_pvt_parameters(tmp_path)


def test_pvt_parameter_loader_rejects_example_source_reference(tmp_path):
    parameter_file = tmp_path / "pvt.yaml"
    parameter_file.write_text(
        yaml.safe_dump(
            {
                "parameters": _valid_parameter_entries(
                    maximum_source_ref="example"
                )
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="has no usable source_ref"):
        load_pvt_parameters(tmp_path)


def test_pvt_weather_loader_checks_hourly_intervals(tmp_path):
    weather_path = tmp_path / "weather.csv"
    weather_path.write_text(
        "timestamp,ghi,dni,dhi,t_ambient,wind_speed\n"
        "2025-01-01T10:00:00+00:00,800,600,200,22,2\n"
        "2025-01-01T12:00:00+00:00,500,350,150,23,2\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="hourly"):
        load_pvt_weather(weather_path)


def test_pvt_runner_explains_solar_extra_install_command(tmp_path, monkeypatch):
    original_import = builtins.__import__

    def import_without_pvlib(name, *args, **kwargs):
        if name == "pvlib":
            raise ModuleNotFoundError("No module named 'pvlib'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_pvlib)
    with pytest.raises(RuntimeError) as exc_info:
        run_pvt_only(
            tmp_path / "weather.csv",
            {},
            tmp_path / "results.csv",
            tmp_path / "summary.json",
            "missing-solar-extra",
        )

    assert 'python -m pip install -e ".[solar]"' in str(exc_info.value)


def test_pvt_runner_writes_hourly_results_and_summary(tmp_path):
    pytest.importorskip("pvlib")
    weather_path = tmp_path / "weather.csv"
    weather_path.write_text(
        "timestamp,ghi,dni,dhi,t_ambient,wind_speed\n"
        "2025-01-01T10:00:00+00:00,800,600,200,22,2\n"
        "2025-01-01T11:00:00+00:00,500,350,150,23,2\n",
        encoding="utf-8",
    )
    parameters = {
        "site.latitude": 25.79,
        "site.longitude": 55.94,
        "site.elevation": 31.1,
        "site.collector_tilt": 25.0,
        "site.surface_azimuth": 180.0,
        "site.ground_albedo": 0.2,
        "site.shading_loss_factor": 0.0,
        "pvt_el.eta_ref": 0.2,
        "pvt_el.T_ref": 298.15,
        "pvt_el.beta": 0.0037,
        "pvt_el.mpp_assumption": "user_efficiency_factor",
        "pvt_el.mpp_efficiency_factor": 0.98,
        "pvt_th.collector_area": 6.0,
        "pvt_th.tau_alpha": 0.5,
        "pvt_th.F_R": 0.8,
        "pvt_th.U_L": 12.0,
        "pvt_th.R_cell_fluid": 0.05,
        "pvt_th.T_fluid_max": 318.15,
        "pvt_th.demo_inlet_temperature": 293.15,
        "loop.mass_flow_fixed": 0.011111111111,
        "loop.fluid_cp": 4180.0,
        "_input_snapshot": {
            "pvt_th.U_L": {
                "value": 12.0,
                "unit": "W/(m2*K)",
                "source_type": "datasheet",
                "source_ref": "collector sheet",
            }
        },
    }
    results_path = tmp_path / "results.csv"
    summary_path = tmp_path / "summary.json"

    summary = run_pvt_only(
        weather_path,
        parameters,
        results_path,
        summary_path,
        "unit-test",
    )

    with results_path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    saved_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert all(row["converged"] == "True" for row in rows)
    assert summary["success"] is True
    assert summary["steps"] == 2
    assert saved_summary["metrics"]["M-PV-01"] == summary["metrics"]["M-PV-01"]
    assert summary["electrical_energy_kwh"] > 0
    assert saved_summary["input_parameters"] == parameters["_input_snapshot"]
