"""Tests for the interactive whole-system screening engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from aquasolar import design


def test_profile_fractions_are_a_normalised_day():
    fractions = design.profile_fractions("household")
    assert len(fractions) == design.PROFILE_HOURS
    assert sum(fractions) == pytest.approx(1.0)
    assert fractions[19] > fractions[9]
    assert max(fractions) < 0.2


def test_peaking_concentrates_the_evening_not_the_total():
    flat = design.profile_fractions("household", 1.0)
    peaked = design.profile_fractions("household", 2.0)
    assert sum(peaked) == pytest.approx(1.0)
    assert peaked[20] > flat[20]
    assert peaked[7] < flat[7]


def test_square_wave_is_even():
    fractions = design.profile_fractions("square_wave")
    assert all(value == pytest.approx(1 / 24) for value in fractions)


def test_validation_rejects_out_of_range_and_unknown_changes():
    with pytest.raises(ValueError, match="screening range"):
        design._validate({"tank_volume": 10.0})
    with pytest.raises(ValueError, match="Unsupported change"):
        design._validate({"ro_magic": 1.0})
    with pytest.raises(ValueError, match="below the delivery temperature"):
        design._validate({"mains_temperature": 40.0, "delivery_temperature": 40.0})
    with pytest.raises(ValueError, match="must be one of"):
        design._validate({"draw_strategy": "unknown"})


def test_validation_accepts_defaults_and_numeric_strings():
    resolved = design._validate({"tank_volume": "200", "ro_recovery": 0.42})
    assert resolved.tank_volume == pytest.approx(200.0)
    assert resolved.ro_recovery == pytest.approx(0.42)
    assert resolved.collector_area == design.DesignInputs().collector_area


def test_annualiser_returns_finite_payback_and_positive_crf():
    result = design._annualise(1000.0, 20.0, 0.06, 50.0, 100.0)
    assert result["simple_payback_years"] == pytest.approx(10.0)
    assert 0 < result["crf"] < 1
    no_savings = design._annualise(1000.0, 20.0, 0.06, 50.0, 0.0)
    assert no_savings["simple_payback_years"] == float("inf")


def _synthetic_weather() -> list[dict]:
    from datetime import datetime, timedelta, timezone

    start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    rows = []
    for hour in range(24):
        daylight = max(0.0, 1.0 - abs(hour - 12) / 7.0)
        rows.append(
            {
                "timestamp": start + timedelta(hours=hour),
                "ghi": 900.0 * daylight,
                "dni": 700.0 * daylight,
                "dhi": 120.0 * daylight,
                "t_ambient": 30.0 + 5.0 * daylight,
                "wind_speed": 2.0,
            }
        )
    return rows


def _registry() -> dict:
    return {
        "pvt_th.collector_area": 6.0,
        "pvt_th.tau_alpha": 0.5,
        "pvt_th.F_R": 0.4922,
        "pvt_th.U_L": 12.0,
        "pvt_th.R_cell_fluid": 0.114,
        "pvt_th.T_fluid_max": 358.15,
        "pvt_el.eta_ref": 0.2,
        "pvt_el.T_ref": 298.15,
        "pvt_el.beta": 0.0037,
        "pvt_el.mpp_assumption": "user_efficiency_factor",
        "pvt_el.mpp_efficiency_factor": 1.0,
        "loop.fluid_cp": 4180.0,
        "loop.mass_flow_fixed": 0.011111111111111112,
    }


def _run(overrides=None, *, hourly=True):
    rows = _synthetic_weather()
    poa = [float(row["ghi"]) for row in rows]
    inputs = design._validate(overrides or {})
    simulated = design._simulate(rows, poa, _registry(), inputs, record_hourly=hourly)
    summary, drivers = design._summarise(simulated, inputs, len(rows))
    return simulated, summary, drivers


def test_simulation_conserves_hot_water_and_serves_the_draw():
    simulated, summary, _ = _run({"daily_draw": 150.0, "tank_heat_loss": 2.0})
    assert simulated["totals"]["hot_water_kwh"] == pytest.approx(
        150 * 4.186 * (50 - 28) / 3600, rel=0.01
    )
    assert summary["tank_supply_fraction"] <= 1.0
    assert summary["solar_heating_fraction"] <= 1.0
    assert summary["annual_backup_kwh"] >= 0.0
    assert summary["annual_pvt_kwh"] >= 0.0


def test_more_area_never_reduces_the_solar_fraction():
    _, small, _ = _run({"collector_area": 3.0})
    _, large, _ = _run({"collector_area": 12.0})
    assert large["solar_heating_fraction"] >= small["solar_heating_fraction"]


def test_battery_improves_self_sufficiency_when_the_array_surplus_exists():
    _, none, _ = _run({"battery_capacity": 0.0, "battery_initial": 0.0})
    _, battery, _ = _run({"battery_capacity": 5.0, "battery_initial": 0.0})
    assert battery["self_sufficiency"] >= none["self_sufficiency"]


def test_grid_tied_mode_imports_less_than_it_exports_and_never_negatives():
    simulated, summary, _ = _run({"battery_capacity": 3.0})
    assert summary["annual_import_kwh"] >= 0
    assert summary["annual_export_kwh"] >= 0
    assert summary["drinking_water_m3_year"] > 0
    assert summary["brine_salinity_mg_l"] > summary["feed_salinity_mg_l"]
    assert simulated["totals"]["ro_kwh"] == pytest.approx(0.105, rel=0.01)


def test_experiment_sweep_is_monotone_in_area():
    rows = _synthetic_weather()
    poa = [float(row["ghi"]) for row in rows]
    points = design.experiment(
        rows, poa, _registry(), design._validate({}), "collector_area"
    )
    fractions = [point["solar_heating_fraction"] for point in points]
    assert fractions == sorted(fractions)


def test_ensemble_is_reproducible_for_the_same_seed():
    rows = _synthetic_weather()
    poa = [float(row["ghi"]) for row in rows]
    inputs = design._validate({})
    first = design.ensemble(rows, poa, _registry(), inputs, runs=3)
    second = design.ensemble(rows, poa, _registry(), inputs, runs=3)
    assert first == second
    assert len(first) == 3


def test_design_screening_requires_a_weather_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        design.run_design_screening(
            tmp_path, tmp_path / "missing.csv", {}, with_experiments=False
        )
