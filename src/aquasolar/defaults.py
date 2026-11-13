"""Reproducible, source-labelled exploratory defaults for the AquaSolar model."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


DEMO_SEED = int("20261029")
ENTERED_ON = "2026-10-29"
ENTERED_BY = "User-authorized exploratory demo preset"
DOCUMENT_REF = "../../AquaSolar_TRNSYS_Master_Direction.md#3.2"
DEMO_REF = "../provenance/demo_defaults.yaml"
_NEEDS_AUTHORITATIVE_SOURCE = {
    "pvt_th.T_fluid_max": (
        "No supplied source specifies a maximum fluid outlet temperature for "
        "the modeled PVT collector. Do not infer this from DHW setpoints, tank "
        "temperatures, or controller cutouts."
    )
}

_UNITS = {
    "activation_energy": "J/(mol*K)",
    "angle": "deg",
    "area": "m2",
    "area_thermal_resistance": "K*m2/W",
    "areal_heat_capacity": "J/(m2*K)",
    "concentration": "mg/L",
    "currency": "AED",
    "currency_per_energy": "AED/kWh",
    "currency_per_time": "AED/month",
    "currency_per_volume": "AED/L",
    "density": "kg/m3",
    "dimensionless": "1",
    "emission_per_energy": "g_CO2eq/kWh",
    "emission_per_volume": "kg_CO2eq/m3",
    "energy": "J",
    "energy_per_volume": "J/m3",
    "flow_mass": "kg/s",
    "flow_volumetric": "m3/s",
    "fraction": "1",
    "heat_transfer_coefficient": "W/(m2*K)",
    "irradiance": "W/m2",
    "length": "m",
    "loading_capacity": "kg",
    "mass": "kg",
    "permeability": "m/(s*Pa)",
    "power": "W",
    "pressure": "Pa",
    "rate_per_temperature": "1/K",
    "rate_per_time": "1/year",
    "rate_per_volume": "1/(m3*s)",
    "specific_heat": "J/(kg*K)",
    "temperature": "K",
    "temperature_difference": "K",
    "thermal_conductance": "W/K",
    "thermal_conductivity": "W/(m*K)",
    "time": "s",
    "uv_dose": "J/m2",
    "uv_intensity": "W/m2",
    "volume": "L",
}

_DOCUMENTED: dict[str, tuple[Any, str, str, str]] = {
    "site.elevation": (
        float("31.1"),
        "m",
        "literature",
        "../../ARE_RK_Khaimah.Intl.AP.411840_TMYx.epw#LOCATION",
    ),
    "site.latitude": (float("25.79"), "deg", "literature", DOCUMENT_REF),
    "site.longitude": (float("55.94"), "deg", "literature", DOCUMENT_REF),
    "site.timezone": ("Asia/Dubai", "", "literature", DOCUMENT_REF),
    "site.collector_tilt": (float("25.0"), "deg", "literature", DOCUMENT_REF),
    "site.collector_azimuth": (float("0.0"), "deg", "literature", DOCUMENT_REF),
    "site.azimuth_convention": (
        "south_zero_east_negative",
        "",
        "literature",
        DOCUMENT_REF,
    ),
    "site.ground_albedo": (float("0.2"), "1", "assumption", DEMO_REF),
    "site.shading_loss_factor": (float("0.0"), "1", "assumption", DEMO_REF),
    "soiling.mode": ("none", "", "assumption", DEMO_REF),
    "pvt_el.eta_ref": (float("0.20"), "1", "literature", DOCUMENT_REF),
    "pvt_el.T_ref": (
        float("298.15"),
        "K",
        "assumption",
        DEMO_REF,
    ),
    "pvt_el.G_ref": (
        float("1000.0"),
        "W/m2",
        "standard",
        "IEC 61215-1:2021 standard test conditions",
    ),
    "pvt_el.beta": (float("0.0037"), "1/K", "literature", DOCUMENT_REF),
    "pvt_el.inverter_efficiency": (float("0.96"), "1", "literature", DOCUMENT_REF),
    "pvt_el.module_count": (int("3"), "", "literature", DOCUMENT_REF),
    "pvt_el.irradiance_model": ("none", "", "assumption", DEMO_REF),
    "pvt_el.iam_model": ("none", "", "assumption", DEMO_REF),
    "pvt_el.mpp_assumption": (
        "user_efficiency_factor",
        "",
        "literature",
        DOCUMENT_REF,
    ),
    "pvt_el.mpp_efficiency_factor": (float("0.98"), "1", "literature", DOCUMENT_REF),
    "pvt_th.collector_area": (float("6.0"), "m2", "literature", DOCUMENT_REF),
    "pvt_th.area_basis": ("gross", "", "assumption", DEMO_REF),
    "pvt_th.collector_type": ("unglazed", "", "literature", DOCUMENT_REF),
    "pvt_th.thermal_model": (
        "steady_state_hottel_whillier_form",
        "",
        "assumption",
        DEMO_REF,
    ),
    "pvt_th.tau_alpha": (float("0.50"), "1", "literature", DOCUMENT_REF),
    "pvt_th.U_L": (float("12.0"), "W/(m2*K)", "literature", DOCUMENT_REF),
    "pvt_th.U_L_wind_dependence": ("none", "", "assumption", DEMO_REF),
    "pvt_th.flow_min": (float("0.005"), "kg/s", "assumption", DEMO_REF),
    "pvt_th.flow_max": (float("0.020"), "kg/s", "assumption", DEMO_REF),
    "pvt_th.pv_only_reference_model": (
        "user_named_model_in_equation_register",
        "",
        "assumption",
        DEMO_REF,
    ),
    "pvt_th.demo_inlet_temperature": (
        float("293.15"),
        "K",
        "assumption",
        DEMO_REF,
    ),
    "loop.fluid_type": ("water", "", "assumption", DEMO_REF),
    "loop.fluid_density": (float("997.0"), "kg/m3", "assumption", DEMO_REF),
    "loop.fluid_cp": (float("4180.0"), "J/(kg*K)", "assumption", DEMO_REF),
    "loop.flow_mode": ("fixed", "", "literature", DOCUMENT_REF),
    "loop.mass_flow_fixed": (
        float("40.0") / float("3600.0"),
        "kg/s",
        "literature",
        DOCUMENT_REF,
    ),
    "loop.pump_power_model": ("fixed_when_on", "", "literature", DOCUMENT_REF),
    "loop.pump_power_fixed": (float("6.0"), "W", "literature", DOCUMENT_REF),
    "loop.ctrl_min_irradiance": (
        float("100.0"),
        "W/m2",
        "assumption",
        DEMO_REF,
    ),
    "loop.ctrl_dT_on": (float("4.0"), "K", "literature", DOCUMENT_REF),
    "loop.ctrl_dT_off": (float("1.0"), "K", "literature", DOCUMENT_REF),
    "loop.ctrl_T_tank_max": (float("358.15"), "K", "literature", DOCUMENT_REF),
    "loop.ctrl_use_min_irradiance": (False, "", "assumption", DEMO_REF),
    "loop.ctrl_sensor_nodes": (
        "collector outlet versus tank reference; confirm node convention",
        "",
        "assumption",
        DEMO_REF,
    ),
    "tank.volume": (float("150.0"), "L", "literature", DOCUMENT_REF),
    "tank.node_count": (int("6"), "", "literature", DOCUMENT_REF),
    "tank.loss_distribution": ("by_surface_area", "", "assumption", DEMO_REF),
    "tank.ambient_mode": ("timeseries", "", "assumption", DEMO_REF),
    "tank.charge_method": ("direct_fluid_exchange", "", "assumption", DEMO_REF),
    "tank.conduction_model": ("none", "", "assumption", DEMO_REF),
    "tank.mixing_model": ("instant_inversion_mixing", "", "assumption", DEMO_REF),
    "tank.aux_present": (True, "", "literature", DOCUMENT_REF),
    "tank.aux_power": (float("1200.0"), "W", "literature", DOCUMENT_REF),
    "tank.aux_efficiency": (float("0.95"), "1", "assumption", DEMO_REF),
    "tank.aux_setpoint": (float("326.15"), "K", "literature", DOCUMENT_REF),
    "tank.delivery_temp_min": (float("318.15"), "K", "literature", DOCUMENT_REF),
    "tank.safety_policy": (False, "", "assumption", DEMO_REF),
    "elec.configuration": (
        "grid_connected_with_battery",
        "",
        "literature",
        DOCUMENT_REF,
    ),
    "elec.export_allowed": (True, "", "literature", DOCUMENT_REF),
    "elec.battery_capacity": (float("2.5") * int("3600000"), "J", "literature", DOCUMENT_REF),
    "elec.battery_round_trip_eff": (float("0.92"), "1", "literature", DOCUMENT_REF),
    "elec.battery_min_soc": (float("0.10"), "1", "literature", DOCUMENT_REF),
    "tc.rated_product_flow": (
        float("75.0") * float("0.003785411784") / float("86400.0"),
        "m3/s",
        "literature",
        DOCUMENT_REF,
    ),
    "tc.feed_pressure_available": (float("101325.0"), "Pa", "assumption", DEMO_REF),
    "tc.booster_present": (True, "", "literature", DOCUMENT_REF),
    "tc.booster_pump_efficiency": (float("0.22"), "1", "literature", DOCUMENT_REF),
    "tc.membrane.type": ("low_pressure_ro", "", "literature", DOCUMENT_REF),
    "tc.membrane.recovery": (float("0.50"), "1", "literature", DOCUMENT_REF),
    "tc.membrane.operating_pressure": (float("600000.0"), "Pa", "literature", DOCUMENT_REF),
    "tc.membrane.pump_efficiency": (float("0.22"), "1", "literature", DOCUMENT_REF),
    "tc.membrane.flux_model": (
        "constant_recovery_only",
        "",
        "assumption",
        DEMO_REF,
    ),
    "tc.membrane.temp_correction": ("none", "", "assumption", DEMO_REF),
    "tc.membrane.fouling_model": ("none", "", "assumption", DEMO_REF),
    "tc.remin.enabled": (True, "", "literature", DOCUMENT_REF),
    "tc.remin.method": ("Ca/Mg remineralisation", "", "literature", DOCUMENT_REF),
    "tc.uv.power_basis": ("wall_side", "", "assumption", DEMO_REF),
    "tc.uv.operation_policy": ("on_with_flow", "", "assumption", DEMO_REF),
    "tc.uv.dose_accounting": (False, "", "assumption", DEMO_REF),
    "sq.enabled": (False, "", "assumption", DEMO_REF),
    "sq.treated_storage_enabled": (True, "", "literature", DOCUMENT_REF),
    "sq.treated_storage_volume": (float("30.0"), "L", "literature", DOCUMENT_REF),
    "numerics.time_step": (float("600.0"), "s", "literature", DOCUMENT_REF),
    "numerics.start": (
        "2025-01-01T04:00:00+04:00",
        "",
        "assumption",
        DEMO_REF,
    ),
    "numerics.end": (
        "2026-01-01T04:00:00+04:00",
        "",
        "assumption",
        DEMO_REF,
    ),
    "numerics.property_model": ("constant", "", "assumption", DEMO_REF),
    "numerics.loop_solver": ("bracketing", "", "assumption", DEMO_REF),
    "numerics.tank_scheme": ("substepped_explicit", "", "assumption", DEMO_REF),
    "numerics.initial_tank_temperature": (float("293.15"), "K", "assumption", DEMO_REF),
    "numerics.master_seed": (DEMO_SEED, "", "assumption", DEMO_REF),
    "numerics.ensemble_size": (1, "", "assumption", DEMO_REF),
    "numerics.mc_stopping_rule": ("fixed_size", "", "assumption", DEMO_REF),
    "numerics.sensitivity_method": ("morris_screening", "", "assumption", DEMO_REF),
    "numerics.output_interval": (float("3600.0"), "s", "assumption", DEMO_REF),
    "numerics.gap_policy": ("flag_and_stop", "", "assumption", DEMO_REF),
    "const.rho_water_ref": (float("997.0"), "kg/m3", "assumption", DEMO_REF),
    "const.cp_water_ref": (float("4180.0"), "J/(kg*K)", "assumption", DEMO_REF),
    "const.property_source": ("constant liquid-water properties", "", "assumption", DEMO_REF),
    "econ.horizon": (float("20.0"), "year", "assumption", DEMO_REF),
    "econ.pvt_lifetime": (float("25.0"), "year", "assumption", DEMO_REF),
    "econ.tank_lifetime": (float("15.0"), "year", "assumption", DEMO_REF),
    "econ.baseline_ro_lifetime": (float("5.0"), "year", "assumption", DEMO_REF),
    "env.bottle_volume": (float("1.0"), "L", "assumption", DEMO_REF),
}

_TEXT_VALUES = {
    "econ.currency": "AED",
    "econ.baseline_ro_power": "100 W demo comparator; verify rated basis",
    "elec.priority_order": "critical controls, pumps, water treatment, battery, export",
    "env.system_boundary": "villa PVT collector and listed auxiliaries; demo boundary",
    "mnt.pathway_ids": "A,B,C",
    "mnt.intensity_order": "A,B,C",
    "mnt.lexicographic_order": "quality, energy, cost",
    "numerics.initial_storage_state": "new consumables; zero loading",
    "tc.pathway_stage_lists": (
        "A: sediment,carbon; B: sediment,carbon,UV; "
        "C: sediment,carbon,low_pressure_ro,remineralisation,UV"
    ),
    "tc.uf.backwash_interval": "12 h (demo assumption)",
    "tc.membrane.pretreatment_note": "sediment and carbon filters (demo configuration)",
    "tc.sensor_cost_and_power_note": "sensor and monitoring values are demo assumptions",
    "sq.disinfectant_species_id": "free_chlorine",
    "sq.treated_decay_note": "uses the storage decay assumptions in this demo preset",
    "ver.calibration_period": "not calibrated; exploratory demonstration only",
    "ver.validation_period": "not validated; exploratory demonstration only",
    "ver.calibration_parameter_list": "none; do not calibrate demo defaults",
}

_BOUNDS: dict[str, tuple[float, float]] = {
    "activation_energy": (float("25000.0"), float("65000.0")),
    "angle": (-float("10.0"), float("10.0")),
    "area": (float("0.1"), float("2.0")),
    "area_thermal_resistance": (float("0.01"), float("0.25")),
    "areal_heat_capacity": (float("1000.0"), float("20000.0")),
    "concentration": (float("0.1"), float("2.0")),
    "currency": (float("100.0"), float("5000.0")),
    "currency_per_energy": (float("0.05"), float("0.5")),
    "currency_per_time": (float("5.0"), float("100.0")),
    "currency_per_volume": (float("0.001"), float("0.05")),
    "density": (float("990.0"), float("1010.0")),
    "dimensionless": (float("0.01"), float("0.1")),
    "emission_per_energy": (float("300.0"), float("800.0")),
    "emission_per_volume": (float("0.001"), float("0.02")),
    "energy": (float("100.0"), float("10000.0")),
    "energy_per_volume": (float("100000.0"), float("3000000.0")),
    "flow_mass": (float("0.001"), float("0.03")),
    "flow_volumetric": (float("1e-7"), float("5e-6")),
    "fraction": (float("0.1"), float("0.98")),
    "heat_transfer_coefficient": (float("5.0"), float("25.0")),
    "irradiance": (float("50.0"), float("200.0")),
    "length": (float("0.1"), float("3.0")),
    "loading_capacity": (float("0.1"), float("10.0")),
    "mass": (float("0.01"), float("2.0")),
    "permeability": (float("1e-12"), float("1e-10")),
    "power": (float("1.0"), float("250.0")),
    "pressure": (float("100000.0"), float("800000.0")),
    "rate_per_temperature": (float("0.001"), float("0.006")),
    "rate_per_time": (float("0.001"), float("0.1")),
    "rate_per_volume": (float("0.001"), float("1.0")),
    "specific_heat": (float("4000.0"), float("4200.0")),
    "temperature": (float("285.15"), float("323.15")),
    "temperature_difference": (float("0.2"), float("5.0")),
    "thermal_conductance": (float("0.2"), float("5.0")),
    "thermal_conductivity": (float("0.1"), float("1.0")),
    "time": (float("60.0"), float("86400.0")),
    "uv_dose": (float("10000.0"), float("60000.0")),
    "uv_intensity": (float("0.1"), float("2.0")),
    "volume": (float("0.1"), float("500.0")),
}


def _generated_value(
    parameter: dict[str, Any], rng: random.Random
) -> tuple[Any, str]:
    parameter_id = parameter["id"]
    kind = parameter.get("quantity_kind", "text")
    allowed = parameter.get("allowed_values", [])
    if allowed:
        return rng.choice(allowed), ""
    if kind == "boolean":
        return bool(rng.getrandbits(1)), ""
    if kind == "text":
        return _TEXT_VALUES.get(
            parameter_id, f"Exploratory demo assumption for {parameter_id}; verify."
        ), ""
    if kind == "timestamp":
        return "2025-01-01T04:00:00+04:00", ""
    if kind == "count":
        return rng.randint(1, int("8")), ""
    if kind == "currency":
        return round(rng.uniform(float("100.0"), float("5000.0")), 2), _UNITS[kind]
    low, high = _BOUNDS.get(kind, (float("0.1"), 1.0))
    value = rng.uniform(low, high)
    if kind in {"flow_volumetric", "permeability", "rate_per_volume"}:
        value = round(value, int("12"))
    elif kind in {"fraction", "dimensionless", "rate_per_time"}:
        value = round(value, int("4"))
    else:
        value = round(value, int("3"))
    return value, _UNITS.get(kind, "")


def apply_demo_defaults(root: Path) -> dict[str, Any]:
    """Fill unset values using the AquaSolar design basis and seeded demo assumptions.

    Existing non-null values are retained. The generated defaults are marked
    confirmed only because the user explicitly authorized this demo preset;
    assumptions remain labelled and are not calibrated engineering values.
    """
    rng = random.Random(DEMO_SEED)
    yaml = YAML()
    yaml.preserve_quotes = True
    generated: list[dict[str, Any]] = []
    updated_count = 0
    provenance_path = root / "inputs" / "provenance" / "demo_defaults.yaml"
    previous_manifest = {}
    if provenance_path.exists():
        with provenance_path.open(encoding="utf-8") as stream:
            previous_manifest = yaml.load(stream) or {}
    previously_generated = {
        row["id"]
        for row in previous_manifest.get("parameters", [])
        if row.get("generated_by_this_preset")
    }
    parameters_dir = root / "inputs" / "parameters"
    for path in sorted(parameters_dir.glob("*.yaml")):
        with path.open(encoding="utf-8") as stream:
            data = yaml.load(stream)
        changed = False
        for parameter in data.get("parameters", []):
            parameter_id = parameter["id"]
            if parameter.get("value") is not None:
                generated.append(
                    {
                        "id": parameter_id,
                        "value": parameter["value"],
                        "unit": parameter.get("unit"),
                        "source_type": parameter.get("source_type"),
                        "source_ref": parameter.get("source_ref"),
                        "notes": parameter.get("notes"),
                        "generated_by_this_preset": (
                            parameter_id in previously_generated
                            or str(parameter.get("source_ref", "")).startswith(
                                DEMO_REF
                            )
                        ),
                    }
                )
                continue
            if parameter_id in _NEEDS_AUTHORITATIVE_SOURCE:
                generated.append(
                    {
                        "id": parameter_id,
                        "value": None,
                        "unit": parameter.get("unit"),
                        "source_type": None,
                        "source_ref": None,
                        "notes": _NEEDS_AUTHORITATIVE_SOURCE[parameter_id],
                        "generated_by_this_preset": False,
                    }
                )
                continue
            if parameter_id in _DOCUMENTED:
                value, unit, source_type, source_ref = _DOCUMENTED[parameter_id]
            else:
                value, unit = _generated_value(parameter, rng)
                source_type = "assumption"
                source_ref = f"{DEMO_REF}#{parameter_id}"
            if source_ref == DEMO_REF:
                source_ref = f"{DEMO_REF}#{parameter_id}"
            if unit and not parameter.get("unit"):
                parameter["unit"] = unit
            parameter["value"] = value
            parameter["status"] = "confirmed"
            parameter["source_type"] = source_type
            parameter["source_ref"] = source_ref
            parameter["entered_by"] = ENTERED_BY
            parameter["entered_on"] = ENTERED_ON
            if source_type == "assumption":
                parameter["notes"] = (
                    "User-authorized, reproducible exploratory placeholder; "
                    "not measured, calibrated, or suitable for design decisions. "
                    f"Seed={DEMO_SEED}."
                )
            elif source_ref == DOCUMENT_REF:
                parameter["notes"] = (
                    "Value transcribed from the cited AquaSolar design basis. "
                    "Check interpretation and model-equation compatibility."
                )
            elif parameter_id == "site.elevation":
                parameter["notes"] = (
                    "Elevation copied from the EPW LOCATION header; confirm it "
                    "represents the modeled site."
                )
            elif source_type == "standard":
                parameter["notes"] = (
                    "Standard test-condition reference; not a local weather "
                    "measurement."
                )
            generated.append(
                {
                    "id": parameter_id,
                    "value": value,
                    "unit": parameter.get("unit"),
                    "source_type": source_type,
                    "source_ref": source_ref,
                    "notes": parameter.get("notes"),
                    "generated_by_this_preset": True,
                }
            )
            changed = True
            updated_count += 1
        if changed:
            with path.open("w", encoding="utf-8", newline="") as stream:
                yaml.dump(data, stream)

    provenance = {
        "title": "User-authorized exploratory demo defaults",
        "warning": (
            "Not calibrated engineering inputs. Assumptions are deterministic "
            "seeded placeholders and must be replaced or independently verified "
            "before design, safety, cost, or potable-water decisions."
        ),
        "seed": DEMO_SEED,
        "document_source": "AquaSolar_TRNSYS_Master_Direction.md, section 3.2",
        "unmatched_document_coefficients": [
            "The document's PV derate fd, kc, and knf have no corresponding "
            "registered model fields and were not applied.",
            "The document's MPPT efficiency is represented by the registered "
            "MPP factor; the Python PVT solver applies this factor.",
            "The Type-560 eta0/a1 values are mapped to tau_alpha/U_L only as "
            "an exploratory approximation; this is not equation equivalence.",
        ],
        "parameters": generated,
    }
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    with provenance_path.open("w", encoding="utf-8", newline="") as stream:
        yaml.dump(provenance, stream)
    return {"updated": updated_count, "path": provenance_path, "seed": DEMO_SEED}
