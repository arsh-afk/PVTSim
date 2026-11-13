"""Presentation metadata for the calculations executed by the PVT-only runner."""

from __future__ import annotations

from typing import Any

from aquasolar.pvt.runner import _REQUIRED_PARAMETERS


_PARAMETER_GROUPS = (
    {
        "id": "site",
        "label": "Site and orientation",
        "parameter_ids": (
            "site.latitude",
            "site.longitude",
            "site.elevation",
            "site.collector_tilt",
            "site.collector_azimuth",
            "site.azimuth_convention",
            "site.ground_albedo",
            "site.shading_loss_factor",
        ),
    },
    {
        "id": "electrical",
        "label": "PVT electrical model",
        "parameter_ids": (
            "pvt_el.eta_ref",
            "pvt_el.T_ref",
            "pvt_el.beta",
            "pvt_el.irradiance_model",
            "pvt_el.iam_model",
            "pvt_el.mpp_assumption",
            "pvt_el.mpp_efficiency_factor",
        ),
    },
    {
        "id": "thermal",
        "label": "PVT thermal model",
        "parameter_ids": (
            "pvt_th.collector_area",
            "pvt_th.thermal_model",
            "pvt_th.tau_alpha",
            "pvt_th.F_R",
            "pvt_th.U_L",
            "pvt_th.U_L_wind_dependence",
            "pvt_th.R_cell_fluid",
            "pvt_th.T_fluid_max",
            "pvt_th.demo_inlet_temperature",
        ),
    },
    {
        "id": "loop",
        "label": "Flow and fluid",
        "parameter_ids": ("loop.mass_flow_fixed", "loop.fluid_cp"),
    },
    {
        "id": "mode_gates",
        "label": "Supported-mode checks",
        "parameter_ids": ("soiling.mode",),
    },
)

_WEATHER_COLUMNS = (
    {
        "id": "timestamp",
        "label": "Interval timestamp",
        "unit": "ISO 8601",
        "note": "Time zone must be explicit; records must be ordered hourly.",
    },
    {"id": "ghi", "label": "Global horizontal irradiance", "unit": "W/m2"},
    {"id": "dni", "label": "Direct normal irradiance", "unit": "W/m2"},
    {"id": "dhi", "label": "Diffuse horizontal irradiance", "unit": "W/m2"},
    {"id": "t_ambient", "label": "Ambient temperature", "unit": "C"},
    {
        "id": "wind_speed",
        "label": "Wind speed",
        "unit": "m/s",
        "note": "Required and passed to the collector interface; the current no-wind-loss mode does not use it to modify output.",
    },
)

_STEPS = (
    {
        "id": "parameter-validation",
        "label": "Validate and load inputs",
        "formula": "Required values must be confirmed, have traceable sources, use supported units, and select supported PVT modes.",
        "description": "Numeric values are converted to the runner's calculation units. The selected thermal/electrical options and no-soiling mode are compatibility gates, not separate calculations.",
        "input_groups": ("site", "electrical", "thermal", "loop", "mode_gates"),
        "depends_on": (),
        "parameter_ids": _REQUIRED_PARAMETERS,
        "outputs": ("normalized_inputs",),
        "source": "src/aquasolar/pvt/runner.py · load_pvt_parameters()",
        "unit": "declared parameter units to runner units",
    },
    {
        "id": "azimuth-mapping",
        "label": "Map collector azimuth",
        "formula": "south_zero_east_negative: (180 + collector_azimuth) mod 360; north_zero_clockwise: collector_azimuth mod 360.",
        "description": "The declared azimuth convention is converted to the north-zero, clockwise convention expected by the solar-position calculation.",
        "input_groups": ("site",),
        "depends_on": ("parameter-validation",),
        "parameter_ids": ("site.collector_azimuth", "site.azimuth_convention"),
        "outputs": ("surface_azimuth",),
        "source": "src/aquasolar/pvt/runner.py · load_pvt_parameters()",
        "unit": "degrees",
    },
    {
        "id": "solar-position",
        "label": "Calculate solar position",
        "formula": "pvlib.solarposition.get_solarposition(interval_midpoint, latitude, longitude, altitude=elevation).",
        "description": "Solar zenith and azimuth are evaluated at the midpoint of each hourly weather interval.",
        "input_groups": ("site", "weather"),
        "depends_on": ("parameter-validation",),
        "parameter_ids": ("site.latitude", "site.longitude", "site.elevation"),
        "outputs": ("solar_position",),
        "source": "src/aquasolar/pvt/runner.py · run_pvt_only()",
        "unit": "degrees",
    },
    {
        "id": "irradiance-transposition",
        "label": "Transpose irradiance to collector plane",
        "formula": "pvlib.irradiance.get_total_irradiance(..., dni, ghi, dhi, albedo, model='isotropic').poa_global",
        "description": "Uses site orientation, solar position, and the three horizontal irradiance components to estimate plane-of-array irradiance.",
        "input_groups": ("site", "weather"),
        "depends_on": ("azimuth-mapping", "solar-position"),
        "parameter_ids": (
            "site.collector_tilt",
            "site.ground_albedo",
        ),
        "outputs": ("poa",),
        "source": "src/aquasolar/pvt/runner.py · run_pvt_only()",
        "unit": "W/m2",
    },
    {
        "id": "effective-irradiance",
        "label": "Apply shading and normalize ambient temperature",
        "formula": "G_eff = POA * (1 - shading_loss_factor); T_ambient_K = t_ambient_C + 273.15.",
        "description": "The runner records the shading-adjusted irradiance as POA_W_m2 in its result CSV.",
        "input_groups": ("site", "weather"),
        "depends_on": ("irradiance-transposition",),
        "parameter_ids": ("site.shading_loss_factor",),
        "outputs": ("effective_irradiance", "ambient_temperature"),
        "source": "src/aquasolar/pvt/runner.py · run_pvt_only()",
        "unit": "W/m2; K",
    },
    {
        "id": "flow-selection",
        "label": "Select fixed or zero flow",
        "formula": "estimated_gain = (tau_alpha - eta_ref) * G_eff - U_L * (T_in - T_ambient); m_dot = mass_flow_fixed when G_eff > 0 and estimated_gain > 0, otherwise 0.",
        "description": "The inlet temperature is the configured fixed demo temperature. This is not a pump controller or tank-feedback model.",
        "input_groups": ("electrical", "thermal", "loop"),
        "depends_on": ("effective-irradiance",),
        "parameter_ids": (
            "pvt_el.eta_ref",
            "pvt_th.tau_alpha",
            "pvt_th.U_L",
            "pvt_th.demo_inlet_temperature",
            "loop.mass_flow_fixed",
        ),
        "outputs": ("mass_flow",),
        "source": "src/aquasolar/pvt/runner.py · run_pvt_only()",
        "unit": "kg/s",
    },
    {
        "id": "coupled-pvt",
        "label": "Solve the flowing PVT collector",
        "formula": "T_m = (T_in + T_out) / 2; eta = max(0, eta_ref * [1 - beta * (T_cell - T_ref)]); P_el = eta * phi_soil * G_eff * A * f_mpp (phi_soil = 1 in no-soiling mode); Q_u = A * F_R * [tau_alpha * G_eff - P_el / A - U_L * (T_in - T_ambient)]; T_cell = T_m + R_cell_fluid * Q_u / A; T_out = T_in + Q_u / (m_dot * fluid_cp).",
        "description": "Inner cell-temperature iteration and outer bisection solve are bounded by T_fluid_max. f_mpp uses the configured factor only when the supported user-efficiency assumption is selected.",
        "input_groups": ("electrical", "thermal", "loop"),
        "depends_on": ("flow-selection", "effective-irradiance"),
        "parameter_ids": (
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
        ),
        "outputs": ("pvt_outputs",),
        "source": "src/aquasolar/pvt/coupled.py · coupled_solve()",
        "unit": "W; K",
    },
    {
        "id": "zero-flow-pvt",
        "label": "Use the zero-flow branch",
        "formula": "m_dot = 0; T_out = T_in; Q_u = 0; T_cell = T_ambient + G_eff / max(U_L, 0.1); eta = max(0, eta_ref * [1 - beta * (T_cell - T_ref)]); P_el = eta * phi_soil * G_eff * A * f_mpp (phi_soil = 1 in no-soiling mode).",
        "description": "The branch reports zero useful heat and inlet temperature at the outlet while still estimating cell temperature and electrical power.",
        "input_groups": ("electrical", "thermal", "loop"),
        "depends_on": ("flow-selection", "effective-irradiance"),
        "parameter_ids": (
            "pvt_el.eta_ref",
            "pvt_el.T_ref",
            "pvt_el.beta",
            "pvt_el.mpp_assumption",
            "pvt_el.mpp_efficiency_factor",
            "pvt_th.collector_area",
            "pvt_th.U_L",
            "pvt_th.demo_inlet_temperature",
        ),
        "outputs": ("pvt_outputs",),
        "source": "src/aquasolar/pvt/collector.py · pvt_solve(); src/aquasolar/pvt/electrical.py · electrical_output()",
        "unit": "W; K",
    },
    {
        "id": "hourly-energy",
        "label": "Integrate each hourly step",
        "formula": "E_el_Wh = P_el_W * interval_seconds / 3600; E_heat_Wh = Q_u_W * interval_seconds / 3600.",
        "description": "Each hourly row contains weather drivers, irradiance, temperatures, flow, power, useful heat, convergence, and per-step energy.",
        "input_groups": (),
        "depends_on": ("coupled-pvt", "zero-flow-pvt"),
        "parameter_ids": (),
        "outputs": ("hourly_csv",),
        "source": "src/aquasolar/pvt/runner.py · run_pvt_only()",
        "unit": "Wh",
    },
    {
        "id": "run-summary",
        "label": "Summarize the run",
        "formula": "energy_kWh = sum(step_energy_Wh) / 1000; average_power_W = sum(step_energy_Wh) / number_of_steps.",
        "description": "Writes energy totals, averages, named PVT metrics, weather source, parameter snapshot, scope, and limitations to the JSON summary.",
        "input_groups": (),
        "depends_on": ("hourly-energy",),
        "parameter_ids": (),
        "outputs": ("summary_json",),
        "source": "src/aquasolar/pvt/runner.py · run_pvt_only()",
        "unit": "kWh; W",
    },
)

_OUTPUTS = (
    {
        "id": "hourly_csv",
        "label": "Hourly result CSV",
        "description": "One row per hourly weather interval.",
        "produced_by": ("hourly-energy", "coupled-pvt", "zero-flow-pvt"),
        "fields": (
            ("timestamp", "ISO 8601"),
            ("GHI_W_m2", "W/m2"),
            ("DNI_W_m2", "W/m2"),
            ("DHI_W_m2", "W/m2"),
            ("POA_W_m2", "W/m2"),
            ("T_ambient_K", "K"),
            ("wind_speed_m_s", "m/s"),
            ("mass_flow_kg_s", "kg/s"),
            ("P_el_W", "W"),
            ("Q_u_W", "W"),
            ("T_f_out_K", "K"),
            ("T_cell_K", "K"),
            ("converged", "boolean"),
            ("E_el_Wh", "Wh"),
            ("E_heat_Wh", "Wh"),
        ),
    },
    {
        "id": "summary_json",
        "label": "Run summary JSON",
        "description": "Run totals, averages, PVT metric values, input snapshot, source, and model limitations.",
        "produced_by": ("run-summary",),
        "fields": (
            ("electrical_energy_kwh", "kWh"),
            ("useful_heat_kwh", "kWh"),
            ("average_electrical_power_w", "W"),
            ("average_useful_heat_w", "W"),
            ("metrics.M-PV-01", "J"),
            ("metrics.M-TH-01", "J"),
            ("input_parameters", "values, units, status, and provenance"),
        ),
    },
)


def calculation_trace() -> dict[str, Any]:
    """Return a JSON-serializable map of the supported PVT-only calculation."""
    inputs = [
        {
            "id": group["id"],
            "label": group["label"],
            "kind": "parameters",
            "parameter_ids": list(group["parameter_ids"]),
        }
        for group in _PARAMETER_GROUPS
    ]
    inputs.append(
        {
            "id": "weather",
            "label": "Hourly weather CSV",
            "kind": "weather",
            "parameter_ids": [],
            "columns": list(_WEATHER_COLUMNS),
        }
    )
    steps = [
        {
            **step,
            "input_groups": list(step["input_groups"]),
            "depends_on": list(step["depends_on"]),
            "parameter_ids": list(step["parameter_ids"]),
            "outputs": list(step["outputs"]),
        }
        for step in _STEPS
    ]
    outputs = [
        {
            **output,
            "produced_by": list(output["produced_by"]),
            "fields": [
                {"id": field, "unit": unit}
                for field, unit in output["fields"]
            ],
        }
        for output in _OUTPUTS
    ]
    output_ids = {output["id"] for output in outputs}
    step_ids = {step["id"] for step in steps}
    edges = [
        {"source": group_id, "target": step["id"]}
        for step in steps
        for group_id in step["input_groups"]
    ] + [
        {"source": dependency, "target": step["id"]}
        for step in steps
        for dependency in step["depends_on"]
        if dependency in step_ids
    ] + [
        {"source": step_id, "target": output["id"]}
        for output in outputs
        for step_id in output["produced_by"]
        if step_id in step_ids and output["id"] in output_ids
    ]
    return {
        "scope": "PVT-only exploratory runner",
        "required_parameter_ids": list(_REQUIRED_PARAMETERS),
        "inputs": inputs,
        "steps": steps,
        "outputs": outputs,
        "edges": edges,
    }
