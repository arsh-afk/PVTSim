"""Exploratory PVT-only runner for the project's hourly weather input."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


_REQUIRED_PARAMETERS = (
    "site.latitude",
    "site.longitude",
    "site.elevation",
    "site.collector_tilt",
    "site.collector_azimuth",
    "site.azimuth_convention",
    "site.ground_albedo",
    "site.shading_loss_factor",
    "soiling.mode",
    "pvt_el.eta_ref",
    "pvt_el.T_ref",
    "pvt_el.beta",
    "pvt_el.irradiance_model",
    "pvt_el.iam_model",
    "pvt_el.mpp_assumption",
    "pvt_el.mpp_efficiency_factor",
    "pvt_th.collector_area",
    "pvt_th.thermal_model",
    "pvt_th.tau_alpha",
    "pvt_th.F_R",
    "pvt_th.U_L",
    "pvt_th.U_L_wind_dependence",
    "pvt_th.R_cell_fluid",
    "pvt_th.T_fluid_max",
    "pvt_th.demo_inlet_temperature",
    "loop.mass_flow_fixed",
    "loop.fluid_cp",
)

_PVT_REGISTRY_IDS = (
    "pvt_el.eta_ref",
    "pvt_el.T_ref",
    "pvt_el.beta",
    "pvt_el.mpp_assumption",
    "pvt_el.mpp_efficiency_factor",
    "pvt_th.collector_area",
    "pvt_th.tau_alpha",
    "pvt_th.F_R",
    "pvt_th.U_L",
    "pvt_th.R_cell_fluid",
    "pvt_th.T_fluid_max",
    "loop.fluid_cp",
)
_SOURCE_TYPES = {"measured", "datasheet", "literature", "standard", "assumption"}
_SOURCE_REF_PLACEHOLDERS = {
    "",
    "none",
    "null",
    "unknown",
    "example",
    "placeholder",
    "tbd",
    "no source recorded",
    "not provided",
}


def _read_pvt_parameters(parameters_dir: Path) -> dict[str, dict[str, Any]]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "Reading PVT parameters requires PyYAML. Install it with "
            '`python -m pip install pyyaml`.'
        ) from exc
    if not parameters_dir.is_dir():
        raise FileNotFoundError(
            f"PVT parameters directory does not exist: {parameters_dir}"
        )

    parameters: dict[str, dict[str, Any]] = {}
    for path in sorted(parameters_dir.glob("*.yaml")):
        try:
            with path.open(encoding="utf-8") as stream:
                data = yaml.safe_load(stream) or {}
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"PVT parameter file {path.name} is not valid UTF-8 text: {exc}"
            ) from exc
        except yaml.YAMLError as exc:
            raise ValueError(
                f"PVT parameter file {path.name} contains invalid YAML: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"PVT parameter file {path.name} must contain a mapping at the "
                "document root"
            )
        for item in data.get("parameters", []):
            try:
                parameters[item["id"]] = item
            except (KeyError, TypeError) as exc:
                raise ValueError(
                    f"PVT parameter file {path.name} has a parameter entry "
                    "without an 'id' field"
                ) from exc
    missing = [key for key in _REQUIRED_PARAMETERS if key not in parameters]
    if missing:
        raise ValueError(f"Missing PVT parameters: {', '.join(missing)}")
    for key in _REQUIRED_PARAMETERS:
        item = parameters[key]
        if item.get("status") != "confirmed" or item.get("value") is None:
            raise ValueError(
                f"{key} must have a value and status=confirmed before running"
            )
    _validate_fluid_temperature_bound(parameters)
    for key in _REQUIRED_PARAMETERS:
        item = parameters[key]
        source_type = str(item.get("source_type") or "").strip()
        if source_type not in _SOURCE_TYPES:
            raise ValueError(
                f"{key} has invalid source_type {source_type!r}; choose one of "
                f"{', '.join(sorted(_SOURCE_TYPES))}."
            )
        source_ref = str(item.get("source_ref") or "").strip()
        if source_ref.casefold() in _SOURCE_REF_PLACEHOLDERS:
            raise ValueError(
                f"{key} has no usable source_ref (found {source_ref!r}). "
                "Replace it with a traceable source or approved model-boundary "
                "reference, then preview and apply the parameter changes."
            )
    return parameters


def _validate_fluid_temperature_bound(
    parameters: dict[str, dict[str, Any]],
) -> None:
    maximum_temperature = _number(
        parameters, "pvt_th.T_fluid_max", "temperature"
    )
    inlet_temperature = _number(
        parameters, "pvt_th.demo_inlet_temperature", "temperature"
    )
    if maximum_temperature <= inlet_temperature:
        raise ValueError(
            "pvt_th.T_fluid_max "
            f"({maximum_temperature:g} K) must be greater than "
            "pvt_th.demo_inlet_temperature "
            f"({inlet_temperature:g} K). The current outlet-temperature "
            "solver bound is below the collector inlet."
        )


def _number(
    parameters: dict[str, dict[str, Any]], parameter_id: str, expected_unit: str
) -> float:
    entry = parameters[parameter_id]
    value = entry["value"]
    unit = entry.get("unit")
    conversions: dict[str, tuple[str, float, float]] = {
        "deg": ("angle", 1.0, 0.0),
        "degree": ("angle", 1.0, 0.0),
        "rad": ("angle", float("180.0") / math.pi, 0.0),
        "K": ("temperature", 1.0, 0.0),
        "C": ("temperature", 1.0, float("273.15")),
        "degC": ("temperature", 1.0, float("273.15")),
        "m": ("length", 1.0, 0.0),
        "kg/s": ("flow_mass", 1.0, 0.0),
        "kg/h": ("flow_mass", 1.0 / float("3600.0"), 0.0),
        "m2": ("area", 1.0, 0.0),
        "1": ("fraction", 1.0, 0.0),
        "W/(m2*K)": ("heat_transfer_coefficient", 1.0, 0.0),
        "K*m2/W": ("area_thermal_resistance", 1.0, 0.0),
        "J/(kg*K)": ("specific_heat", 1.0, 0.0),
        "1/K": ("rate_per_temperature", 1.0, 0.0),
    }
    entry_kind, factor, offset = conversions.get(
        unit, ("", float("nan"), 0.0)
    )
    expected_kinds = {
        "angle": "angle",
        "temperature": "temperature",
        "length": "length",
        "flow_mass": "flow_mass",
        "area": "area",
        "fraction": "fraction",
        "heat_transfer_coefficient": "heat_transfer_coefficient",
        "area_thermal_resistance": "area_thermal_resistance",
        "specific_heat": "specific_heat",
        "rate_per_temperature": "rate_per_temperature",
    }
    if entry_kind != expected_kinds[expected_unit]:
        raise ValueError(
            f"{parameter_id} unit {unit!r} is not supported as {expected_unit}"
        )
    numeric = float(value)
    converted = numeric * factor + offset
    if not math.isfinite(converted):
        raise ValueError(f"{parameter_id} must be a finite number")
    return converted


def load_pvt_parameters(parameters_dir: Path) -> dict[str, Any]:
    """Load, validate, and convert the inputs needed by the PVT-only runner."""
    entries = _read_pvt_parameters(parameters_dir)
    for parameter_id, expected_unit in (
        ("site.latitude", "angle"),
        ("site.longitude", "angle"),
        ("site.elevation", "length"),
        ("site.collector_tilt", "angle"),
        ("site.collector_azimuth", "angle"),
        ("site.ground_albedo", "fraction"),
        ("site.shading_loss_factor", "fraction"),
        ("pvt_el.eta_ref", "fraction"),
        ("pvt_el.T_ref", "temperature"),
        ("pvt_el.beta", "rate_per_temperature"),
        ("pvt_el.mpp_efficiency_factor", "fraction"),
        ("pvt_th.collector_area", "area"),
        ("pvt_th.tau_alpha", "fraction"),
        ("pvt_th.F_R", "fraction"),
        ("pvt_th.U_L", "heat_transfer_coefficient"),
        ("pvt_th.R_cell_fluid", "area_thermal_resistance"),
        ("pvt_th.T_fluid_max", "temperature"),
        ("pvt_th.demo_inlet_temperature", "temperature"),
        ("loop.mass_flow_fixed", "flow_mass"),
        ("loop.fluid_cp", "specific_heat"),
    ):
        _number(entries, parameter_id, expected_unit)

    supported_choices = {
        "pvt_th.thermal_model": "steady_state_hottel_whillier_form",
        "pvt_th.U_L_wind_dependence": "none",
        "pvt_el.irradiance_model": "none",
        "pvt_el.iam_model": "none",
        "soiling.mode": "none",
    }
    for parameter_id, supported in supported_choices.items():
        if entries[parameter_id]["value"] != supported:
            raise ValueError(
                f"PVT-only runner currently supports {parameter_id}={supported!r}"
            )

    convention = entries["site.azimuth_convention"]["value"]
    if convention == "south_zero_east_negative":
        surface_azimuth = (
            float("180.0")
            + _number(entries, "site.collector_azimuth", "angle")
        ) % float("360.0")
    elif convention == "north_zero_clockwise":
        surface_azimuth = (
            _number(entries, "site.collector_azimuth", "angle") % float("360.0")
        )
    else:
        raise ValueError(
            "PVT-only runner requires a supported site.azimuth_convention"
        )
    values = {
        key: entry["value"] for key, entry in entries.items()
    }
    values["_input_snapshot"] = {
        parameter_id: {
            "value": entries[parameter_id]["value"],
            "unit": entries[parameter_id].get("unit"),
            "status": entries[parameter_id].get("status"),
            "source_type": entries[parameter_id].get("source_type"),
            "source_ref": entries[parameter_id].get("source_ref"),
        }
        for parameter_id in _REQUIRED_PARAMETERS
    }
    for parameter_id, expected_unit in (
        ("site.latitude", "angle"),
        ("site.longitude", "angle"),
        ("site.elevation", "length"),
        ("site.collector_tilt", "angle"),
        ("site.ground_albedo", "fraction"),
        ("site.shading_loss_factor", "fraction"),
        ("pvt_el.eta_ref", "fraction"),
        ("pvt_el.T_ref", "temperature"),
        ("pvt_el.beta", "rate_per_temperature"),
        ("pvt_el.mpp_efficiency_factor", "fraction"),
        ("pvt_th.collector_area", "area"),
        ("pvt_th.tau_alpha", "fraction"),
        ("pvt_th.F_R", "fraction"),
        ("pvt_th.U_L", "heat_transfer_coefficient"),
        ("pvt_th.R_cell_fluid", "area_thermal_resistance"),
        ("pvt_th.T_fluid_max", "temperature"),
        ("pvt_th.demo_inlet_temperature", "temperature"),
        ("loop.mass_flow_fixed", "flow_mass"),
        ("loop.fluid_cp", "specific_heat"),
    ):
        values[parameter_id] = _number(entries, parameter_id, expected_unit)
    values["site.surface_azimuth"] = surface_azimuth
    return values


def load_pvt_weather(weather_path: Path) -> tuple[list[dict[str, Any]], float]:
    """Load and validate hourly weather records used by the PVT-only runner."""
    if not weather_path.is_file():
        raise FileNotFoundError(f"Weather CSV does not exist: {weather_path}")
    rows: list[dict[str, Any]] = []
    try:
        weather_stream = weather_path.open(encoding="utf-8", newline="")
    except OSError as exc:
        raise RuntimeError(
            f"Could not open weather CSV {weather_path}: {exc}"
        ) from exc
    with weather_stream as stream:
        try:
            reader = csv.DictReader(stream)

            required_columns = {
                "timestamp",
                "ghi",
                "dni",
                "dhi",
                "t_ambient",
                "wind_speed",
            }
            missing_columns = required_columns - set(reader.fieldnames or [])
            if missing_columns:
                raise ValueError(
                    f"Weather CSV missing columns: {', '.join(sorted(missing_columns))}"
                )
            for line_number, row in enumerate(reader, start=2):
                try:
                    timestamp = datetime.fromisoformat(row["timestamp"])
                    if timestamp.tzinfo is None:
                        raise ValueError("timestamp needs an explicit UTC offset")
                    weather_row = {
                        "timestamp": timestamp,
                        "ghi": float(row["ghi"]),
                        "dni": float(row["dni"]),
                        "dhi": float(row["dhi"]),
                        "t_ambient": float(row["t_ambient"]),
                        "wind_speed": float(row["wind_speed"]),
                    }
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid required weather value on CSV line {line_number}: {exc}"
                    ) from exc
                if not all(
                    math.isfinite(weather_row[key])
                    for key in ("ghi", "dni", "dhi", "t_ambient", "wind_speed")
                ):
                    raise ValueError(f"Non-finite weather value on line {line_number}")
                if any(
                    weather_row[key] < 0
                    for key in ("ghi", "dni", "dhi", "wind_speed")
                ):
                    raise ValueError(f"Negative radiation or wind speed on line {line_number}")
                rows.append(weather_row)
        except UnicodeDecodeError as exc:
            raise ValueError(
                f"Weather CSV {weather_path.name} is not valid UTF-8 text: {exc}"
            ) from exc
        except csv.Error as exc:
            raise ValueError(
                f"Malformed weather CSV {weather_path.name}: {exc}"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"Could not read weather CSV {weather_path}: {exc}"
            ) from exc

    if len(rows) < 2:
        raise ValueError("At least two consecutive weather records are required")
    timestamps = [row["timestamp"] for row in rows]
    intervals = [
        (timestamps[index + 1] - timestamps[index]).total_seconds()
        for index in range(len(timestamps) - 1)
    ]
    if any(interval <= 0 for interval in intervals):
        raise ValueError("Weather timestamps must be strictly increasing")
    if len(set(intervals)) != 1:
        raise ValueError("Weather timestamps must have a regular interval")
    interval_seconds = intervals[0]
    if interval_seconds != int("3600"):
        raise ValueError("PVT-only runner currently requires hourly weather records")
    return rows, interval_seconds


def run_pvt_only(
    weather_path: Path,
    parameters: dict[str, Any],
    output_path: Path,
    summary_path: Path,
    scenario_id: str,
) -> dict[str, Any]:
    """Run a fixed-inlet PVT estimate with flow enabled for positive estimated gain."""
    try:
        import pandas as pd
        import pvlib
    except ImportError as exc:
        raise RuntimeError(
            "PVT-only solar calculations require pvlib. From the project root, "
            "install the solar extra in the same Python environment as the "
            'web UI with `python -m pip install -e ".[solar]"`.'
        ) from exc

    from aquasolar.pvt.collector import pvt_solve

    if output_path.exists() or summary_path.exists():
        raise FileExistsError(
            "Refusing to overwrite an existing PVT result; choose another scenario ID."
        )
    rows, interval_seconds = load_pvt_weather(weather_path)
    timestamps = [row["timestamp"] for row in rows]
    interval_centers = pd.DatetimeIndex(
        [stamp + timedelta(seconds=interval_seconds / 2) for stamp in timestamps]
    )
    ghi = pd.Series([row["ghi"] for row in rows], index=interval_centers)
    dni = pd.Series([row["dni"] for row in rows], index=interval_centers)
    dhi = pd.Series([row["dhi"] for row in rows], index=interval_centers)
    solar_position = pvlib.solarposition.get_solarposition(
        interval_centers,
        parameters["site.latitude"],
        parameters["site.longitude"],
        altitude=parameters["site.elevation"],
    )
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=parameters["site.collector_tilt"],
        surface_azimuth=parameters["site.surface_azimuth"],
        solar_zenith=solar_position["apparent_zenith"],
        solar_azimuth=solar_position["azimuth"],
        dni=dni,
        ghi=ghi,
        dhi=dhi,
        albedo=parameters["site.ground_albedo"],
        model="isotropic",
    )["poa_global"].fillna(0.0).clip(lower=0.0)

    registry = {key: parameters[key] for key in _PVT_REGISTRY_IDS}
    output_rows = []
    energy_electric_wh = 0.0
    energy_heat_wh = 0.0
    nonconverged_steps = 0
    for index, row in enumerate(rows):
        irradiance = float(poa.iloc[index]) * (
            1.0 - parameters["site.shading_loss_factor"]
        )
        ambient_k = row["t_ambient"] + float("273.15")
        inlet_temperature = parameters["pvt_th.demo_inlet_temperature"]
        estimated_solar_gain = (
            parameters["pvt_th.tau_alpha"] - parameters["pvt_el.eta_ref"]
        ) * irradiance - parameters["pvt_th.U_L"] * (
            inlet_temperature - ambient_k
        )
        flow = (
            parameters["loop.mass_flow_fixed"]
            if irradiance > 0 and estimated_solar_gain > 0
            else 0.0
        )
        result = pvt_solve(
            T_in=inlet_temperature,
            m_dot=flow,
            G_eff=irradiance,
            T_amb=ambient_k,
            wind_speed=row["wind_speed"],
            registry=registry,
        )
        if not result.converged:
            nonconverged_steps += 1
            reason = (
                "no energy-balance solution exists within pvt_th.T_fluid_max"
                if result.iterations == 0
                else "the nonlinear energy-balance solver did not converge"
            )
            raise RuntimeError(
                f"PVT solver failed at {row['timestamp'].isoformat()}: {reason}"
            )
        electrical_wh = result.P_el * interval_seconds / float("3600.0")
        thermal_wh = result.Q_u * interval_seconds / float("3600.0")
        energy_electric_wh += electrical_wh
        energy_heat_wh += thermal_wh
        output_rows.append(
            {
                "timestamp": row["timestamp"].isoformat(),
                "GHI_W_m2": row["ghi"],
                "DNI_W_m2": row["dni"],
                "DHI_W_m2": row["dhi"],
                "POA_W_m2": irradiance,
                "T_ambient_K": ambient_k,
                "wind_speed_m_s": row["wind_speed"],
                "mass_flow_kg_s": flow,
                "P_el_W": result.P_el,
                "Q_u_W": result.Q_u,
                "T_f_out_K": result.T_f_out,
                "T_cell_K": result.T_cell,
                "converged": result.converged,
                "E_el_Wh": electrical_wh,
                "E_heat_Wh": thermal_wh,
            }
        )

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]))
            writer.writeheader()
            writer.writerows(output_rows)
    except OSError as exc:
        raise RuntimeError(
            f"Could not write PVT results CSV {output_path}: {exc}"
        ) from exc
    summary = {
        "scenario_id": scenario_id,
        "scope": "PVT-only exploratory",
        "success": True,
        "steps": len(output_rows),
        "weather_interval_seconds": interval_seconds,
        "duration_hours": len(output_rows) * interval_seconds / float("3600.0"),
        "electrical_energy_kwh": energy_electric_wh / float("1000.0"),
        "useful_heat_kwh": energy_heat_wh / float("1000.0"),
        "electrical_energy_joules": energy_electric_wh * float("3600.0"),
        "useful_heat_joules": energy_heat_wh * float("3600.0"),
        "average_electrical_power_w": energy_electric_wh / len(output_rows),
        "average_useful_heat_w": energy_heat_wh / len(output_rows),
        "energy_summary": {
            "P_pvt_total": energy_electric_wh * float("3600.0"),
            "Q_u_total": energy_heat_wh * float("3600.0"),
            "P_pvt_avg": energy_electric_wh / len(output_rows),
            "Q_u_avg": energy_heat_wh / len(output_rows),
        },
        "metrics": {
            "M-PV-01": energy_electric_wh * float("3600.0"),
            "M-TH-01": energy_heat_wh * float("3600.0"),
        },
        "nonconverged_steps": nonconverged_steps,
        "weather_source": str(weather_path.relative_to(weather_path.parents[2])),
        "input_parameters": parameters.get("_input_snapshot"),
        "results_csv": str(output_path.relative_to(output_path.parents[2])),
        "limitations": [
            "No tank, pump hysteresis controller, DHW demand, electrical bus, or water treatment is simulated.",
            "Constant fluid inlet temperature and fixed flow without hysteresis are exploratory assumptions.",
            "POA uses pvlib isotropic diffuse transposition and the supplied GHI/DNI/DHI.",
            "Thermal equation and selected Type-560 parameter mapping are not validated.",
            "Generated demo assumptions are not suitable for design or safety decisions.",
        ],
    }
    try:
        with summary_path.open("x", encoding="utf-8") as stream:
            json.dump(summary, stream, indent=2)
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError(
            f"Could not write PVT summary JSON {summary_path}: {exc}"
        ) from exc
    return summary
