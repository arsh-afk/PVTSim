# AquaSolar Living — Full Project Report

**Date:** 2026-10-29
**Project:** Villa-scale PVT + Water-Assurance Simulator (AquaSolar Living)
**Working Directory:** `C:\Users\arsh2\OneDrive - American University of Ras Al Khaimah\Fall2026\waterresearch\Simulation`

---

## What This Simulation Is

AquaSolar Living is a **villa-scale PVT (photovoltaic-thermal) + water-assurance simulator** designed for a residential building in Ras Al Khaimah, UAE. It models how a combined solar collector that produces both electricity and hot water can serve domestic hot-water demand, treat drinking water via minimum-necessary pathways, and interact with the electrical grid and battery storage.

**Current runnable scope:** Only the **PVT-only exploratory path** works end-to-end today (`python -m aquasolar run <id>`). The tank, DHW, electrical-bus, and water-treatment modules exist as code but are not wired into an executable full-system runner yet.

**Status note (2026-11-10):** This report contains an earlier implementation
inventory; use [README.md](README.md), [AGENT_INSTRUCTIONS.md](AGENT_INSTRUCTIONS.md),
and [DATA_ENTRY_GUIDE.md](DATA_ENTRY_GUIDE.md) for current run instructions.
The desktop UI now has a **Run & plots** tab with selectable scenario IDs and
compatible weather CSVs, saved-run browsing, and Matplotlib post-processing.
All PVT results remain exploratory and unvalidated.

---

## Directory Structure Overview

```
Simulation/
├── pyproject.toml              # Package config, deps, entry points
├── AGENT_INSTRUCTIONS.md       # Agent working rules
├── DATA_ENTRY_GUIDE.md         # Input format documentation
├── docs/                       # Equation register, metrics, units, assumptions
├── inputs/                     # ALL user-supplied data lives here
│   ├── input_index.yaml        # Master list of every registered input id
│   ├── parameters/*.yaml       # Single-value YAML params (14 files)
│   ├── timeseries/*.csv+.meta  # Time-indexed CSVs (weather, demand, etc.)
│   ├── tables/*.csv+.meta      # Lookup tables (removal rates, costs, curves)
│   ├── approvals/gate_*.md     # Phase gate sign-offs
│   └── provenance/             # Evidence files for parameter values
├── outputs/pvt_only/           # Generated hourly CSVs + JSON summaries
├── reports/                    # Gate pack reports
├── src/aquasolar/              # THE SIMULATION CODE
│   ├── cli.py                  # Command-line interface
│   ├── __main__.py             # python -m aquasolar entry
│   ├── ui.py                   # Tkinter desktop GUI
│   ├── defaults.py             # Seeded demo-default generator
│   ├── integrator.py           # AquaSolarSimulator class (full system)
│   ├── simulate.py             # run_simulation() time-stepping driver
│   ├── registry/               # Input loading & validation
│   ├── io/                     # Weather converters, table/timeseries loaders
│   ├── units/                  # Pint-based unit handling
│   ├── weather/                # Solar geometry, IAM, transposition, soiling
│   ├── pvt/                    # PVT collector physics (the core engine)
│   ├── tank/                   # Stratified thermal storage
│   ├── solar_loop/             # Pump, controller, pipes between collector↔tank
│   ├── water_treatment/        # Stage models + pathway trains A/B/C
│   ├── mnt/                    # Minimum Necessary Treatment oracle/controller
│   ├── electrical/             # Grid import/export, battery dispatch
│   ├── economics/              # LCOE, NPV, payback, lifecycle cost
│   ├── uncertainty/            # Monte Carlo, Sobol, Morris sensitivity
│   ├── reporting/              # Metrics computation, HTML/JSON dashboards
│   └── integration/            # Run manifest for reproducibility
└── tests/unit/                 # 82+ pytest tests including literal-scan enforcement
```

---

## How Data Flows Through the System

### Step 0: Input Loading (`registry/`, `io/`)

Every number the simulation uses comes from `inputs/`. Nothing is hardcoded.

| Layer | File(s) | Role |
|-------|---------|------|
| Index | `input_index.yaml` | Declares every param id, its kind, phase requirement, conditional trigger |
| Schema | `registry/schema.py` | Pydantic model: `ParameterEntry(id, value, unit, source_type, source_ref, status, uncertainty, valid_range)` |
| Loader | `registry/load.py` | Reads all YAML parameter files, validates required_when conditions, loads CSVs paired with `.meta.yaml`, computes SHA-256 hashes for reproducibility |
| Conditions | `registry/conditions.py` | Evaluates mini-expressions like `loop.flow_mode == fixed` to decide which params are mandatory |
| Errors | `registry/errors.py` | Typed exceptions: `MissingInputError`, `DraftInputError`, `InvalidInputError` with structured fix messages |
| Units | `units/__init__.py` | Wraps Pint; converts °C→K for absolute temps but NOT for ΔT; fallback `_SimpleRegistry` if Pint absent |
| IO | `io/timeseries.py` | Loads CSVs with gap detection (policy: flag_and_stop / interpolate), duplicate check, QC-flag validation |
| IO | `io/quality_report.py` | Writes Markdown quality reports per dataset — never repairs data |
| Converters | `io/epw.py`, `io/nasa_power.py` | Transform EnergyPlus TMYx EPW or NASA POWER JSON → project weather.csv schema |

The CLI command `aquasolar check-inputs` runs this entire chain and writes `inputs/STATUS.md`.

### Step 1: Weather Processing (`weather/`)

Given raw GHI/DNI/DHI + ambient temp + wind speed at each hour:

```
solar_geometry.py          → pvlib NREL algorithm → zenith, azimuth, equation_of_time
transposition.py           → pvlib Perez/isotropic/Haydavies → POA global irradiance
iam.py                     → Klucher/Preiss/user-curve → incidence-angle modifier f(θ)
soiling.py                 → rainfall-driven accumulation → φ_soil ∈ [0,1]
```

Final effective irradiance: `G_eff = POA_global × IAM × (1 − shading_loss) × φ_soil`

#### File-by-file detail

**`weather/solar_geometry.py`**
- `solar_position(timestamp, latitude, longitude, elevation=0.0, pressure=None) -> Dict[str, float]` — Uses pvlib's NREL SPA-equivalent algorithm. Returns dict with keys `solar_zenith`, `solar_azimuth`, `equation_of_time`.
- `calculate_incident_angle(solar_zenith, solar_azimuth, collector_tilt, collector_azimuth) -> float` — Geometric incidence angle on tilted surface.

**`weather/transposition.py`**
- `get_poa_irradiance(ghi, dni=None, dhi=None, solar_zenith=None, solar_azimuth=None, collector_tilt=0.0, collector_azimuth=0.0, ground_albedo=0.2, transposition_model="perez") -> Dict[str, float]` — Supports "perez", "isotropic", "haydavies". Zenith threshold ~88° (0.0349 rad). Returns `poa_direct`, `poa_diffuse`, `poa_global`.

**`weather/iam.py`**
- `iam_none(incident_angle) -> float` — Returns 1.0 always.
- `iam_klucher(incident_angle, F1_coeff, F2_coeff, Fb_coeff, theta_b=0.0) -> float` — Klucher reflection model.
- `iam_preiss(incident_angle, A) -> float` — Preiss/Ashrae-style model with tolerance `1e-6`.
- `calculate_iam(incident_angle, model="none", params=None) -> float` — Dispatcher supporting "none", "klucher", "preiss", "user_curve_table".
- `_interpolate_iam(incident_angle, curve) -> float` — Linear interpolation over user-supplied (angle, iam) pairs.

**`weather/soiling.py`**
- `soiling_factor(days_since_rain, max_soiling, decay_rate, rainfall_factor=0.0, last_rainfall=0.0) -> float` — Formula: `soil_level = max_soiling * (1 - (1 - decay_rate)^days_since_rain)`. Clamped to [0, 1].
- `soiling_factor_series(rainfall_series, days_since_rain_series, max_soiling, decay_rate, rainfall_factor=0.0) -> list` — Vectorized variant.

### Step 2: PVT Collector Physics (`pvt/`) — The Heart

This is where the coupled electro-thermal problem is solved every timestep. Four equations form an algebraic loop:

| Eq ID | Formula | Module |
|-------|---------|--------|
| EQ-PVT-01 | `P_el = η_ref·[1−β(T_c−T_ref)]·φ_soil·G_eff·A·f_MPP` | `electrical.py` |
| EQ-PVT-02 | `Q_u = A·F_R·[τα·G_eff − P_el/A − U_L·(T_f_in − T_amb)]` | `thermal.py` |
| EQ-PVT-03 | `T_out = T_in + Q_u/(ṁ·c_p)` | implicit in `coupled.py` residual |
| EQ-PVT-04 | `T_c = T_m + R_cf · Q_u/A` (cell↔fluid resistance) | inner iteration in `coupled.py` |

#### Solver architecture (`coupled.py`)

1. Outer loop: bisection on `T_out` over `[T_in, T_fluid_max]`
2. At each trial `T_out`: compute mean fluid temp `T_m = (T_in+T_out)/2`
3. Inner loop (~15 iterations): iterate `T_c ↔ P_el ↔ Q_u` until convergence within tolerance `1e-6`
4. Residual: `r = T_in + Q_u/(ṁ·c_p) − T_out_trial`
5. Converge when `|r| < tol` or bracket width `< tol`; max 15 outer iterations

If flow ṁ = 0 (nighttime/stagnation), falls back to no-flow calculation.

#### File-by-file detail

**`pvt/electrical.py`**
- `electrical_output(T_cell, G_eff, eta_ref, T_ref, beta, phi_soil, A, f_irr=1.0, f_mpp=1.0) -> Tuple[float, Dict[str, Any]]` — Implements EQ-PVT-01. Returns `(P_el, ledger)`.
- `electrical_output_series(T_cell_series, G_eff_series, eta_ref, T_ref, beta, phi_soil_series, A) -> list` — Iterating variant.

**`pvt/thermal.py`**
- `useful_heat(T_f_in, m_dot, G_eff, P_el, T_amb, wind_speed, A, tau_alpha, F_R, U_L, U_L_wind_dep=None) -> Tuple[float, Dict[str, Any]]` — Implements EQ-PVT-02. Wind dependence: `U_L_effective = U_L * (1 + wind_coeff * wind_speed)`.
- `useful_heat_no_flow(G_eff, T_amb, A, tau_alpha, U_L) -> Tuple[float, Dict[str, Any]]` — Stagnation case returning zero heat.

**`pvt/coupled.py`**
- `coupled_solve(T_in, m_dot, G_eff, T_amb, wind_speed, registry, solver="bracketing", tolerance=1e-6, max_iterations=15) -> Tuple[float, float, float, float, bool, int]` — Main solver. Returns `(T_f_out, T_c, P_el, Q_u, converged, iterations)`.
- `_fixed_point_solve(func, x0, x_max, tol, max_iter) -> Tuple[float, bool, int]` — Alternative solver.
- `_bracket_solve(func, a, b, tol, max_iter) -> Tuple[float, bool, int]` — Bisection solver with automatic bracket expansion.
- Class `OutsideValidityRange(Exception)` — Raised when inputs leave validity range.

**`pvt/collector.py`**
- Class `PVTCoupledResult` — Container with properties `eta_el` and `eta_th`. Constructor takes `(T_f_out, T_cell, P_el, Q_u, converged, iterations, T_f_in, m_dot, registry)`.
- `pvt_solve(T_in, m_dot, G_eff, T_amb, wind_speed, registry, use_coupled=True) -> PVTCoupledResult` — Top-level dispatcher.
- `pvt_series_solve(...) -> List[PVTCoupledResult]` — Time-series variant.

**`pvt/pv_only.py`**
- `pv_only_reference(G_eff, T_amb, wind_speed, eta_ref, T_ref, beta, phi_soil, A, pv_only_model="simple", **params) -> Tuple[float, float, Dict[str, Any]]` — Supports "simple" (loss-coefficient model, default U_L_pv=10.0) and "faiman" (α=25.0, β_wind=1.0). Returns `(T_cell, P_el, ledger)`.

**`pvt/runner.py`**
- `load_pvt_parameters(parameters_dir) -> dict[str, Any]` — Validates 27 required parameters, checks status/source fields, applies unit conversions, resolves azimuth convention to surface_azimuth.
- `run_pvt_only(weather_path, parameters, output_path, summary_path, scenario_id) -> dict[str, Any]` — Drives hourly simulation using pvlib for solar geometry and isotropic transposition. Refuses to overwrite existing results. Emits CSV + JSON summary with explicit limitations array.
- `_read_pvt_parameters(parameters_dir) -> dict[str, dict[str, Any]]` — Private YAML reader.
- `_number(parameters, parameter_id, expected_unit) -> float` — Private unit-conversion helper with conversion table mapping unit strings to (kind, factor, offset) tuples.

Registry keys consumed by the coupled solver: `pvt_el.eta_ref`, `pvt_el.T_ref`, `pvt_el.beta`, `soiling_factor`, `pvt_el.mpp_efficiency_factor`, `pvt_el.mpp_assumption`, `pvt_th.collector_area`, `pvt_th.tau_alpha`, `pvt_th.F_R`, `pvt_th.U_L`, `pvt_th.R_cell_fluid`, `loop.fluid_cp`, `pvt_th.T_fluid_max`.

### Step 3: Tank Thermal Storage (`tank/`) *(coded, not yet in runnable path)*

Stratified multi-node vertical tank (default 11 nodes for 150 L cylinder). Node ordering: index 0 = top (hot delivery), index n−1 = bottom (cold inlet). Charge enters at configurable node; return exits from another.

#### File-by-file detail

**`tank/grid.py`**
- Class `TankGrid(n_nodes, volume_total, height, diameter)` — Stores per-node temperature list `T[]`, mass list `m[]`, quality list. Attributes: `node_height`, `node_volume`, `node_area`. Defaults: initial T = 293.15 K, ρ = 997.0 kg/m³, cp = 4180.0 J/(kg·K). Methods: `get_temperature(node)`, `set_temperature(node, T)`, `get_mass(node)`, `set_mass(node, m)`, `get_volume(node)`, `get_energy(node, cp=4180.0)`, `total_energy(cp=4180.0)`, `average_temperature()`, `top_temperature()`, `bottom_temperature()`.
- `create_tank_grid(registry) -> TankGrid` — Builds from registry keys `tank.n_nodes`, `tank.volume_total`, `tank.height`, `tank.diameter`.
- `tank_grid_state(grid) -> Dict[str, Any]` — Serializes state for logging/checkpointing.

**`tank/step.py`**
- `tank_step(grid, dt, Q_in, T_in, m_dot_in, Q_out, m_dot_out, Q_loss, T_amb, U_loss, A_loss, cp=4180.0, rho=997.0, mixing_model="ideal", registry=None) -> Tuple[TankGrid, Dict[str, Any]]` — Per-timestep advection, conduction, loss, then mixing. Effective conductivity `k_eff` from registry key `tank.k_eff` (default 0.6). Mixing models: "ideal", "stratified".
- `tank_series_step(grid, time_series, dt, registry) -> Tuple[List[TankGrid], List[Dict[str, Any]]]` — Iterating variant.
- Private helpers: `_ideal_mixing(T, m)`, `_stratified_mixing(T, m, node_height, cp)`.

**`tank/mixing.py`**
- `ideal_mixing(T, m) -> List[float]` — Uniform average weighted by mass.
- `stratified_mixing(T, m, node_height, cp=4180.0) -> List[float]` — Buoyancy-driven inversion when upper layers cooler than lower.
- `partial_mixing(T, m, mixing_fraction) -> List[float]` — Blend fraction toward ideal.
- `no_mixing(T, m) -> List[float]` — Identity passthrough.
- `apply_mixing_model(T, m, model, **params) -> List[float]` — Dispatcher supporting "ideal", "stratified", "partial", "none".
- `mixing_energy_check(T_before, T_after, m, cp=4180.0) -> Dict[str, float]` — Verifies energy conservation across mixing step.

**`tank/draw.py`**
- `draw_profile(time, profile_type, params) -> Tuple[float, float]` — Profile types: "constant", "daily" (peaks hours 6–8 and 18–20), "schedule".
- `draw_from_tank(grid, draw_volume, target_temp, T_cold, cp=4180.0, rho=997.0) -> Tuple[float, float, Dict[str, Any]]` — Tempering logic blends hot outlet with cold makeup to reach target. Default target = 323.15 K (50°C).
- `draw_series(grid, time_series, profile_type, profile_params, T_cold, dt, cp=4180.0, rho=997.0) -> Tuple[List[float], List[float], List[Dict[str, Any]]]` — Iterating variant.

### Step 4: Solar Loop (`solar_loop/`) *(coded, not yet in runnable path)*

Connects collector outlet → tank inlet → tank outlet → collector inlet.

#### File-by-file detail

**`solar_loop/controller.py`**
- `differential_controller(T_collector, T_tank_bottom, dT_on, dT_off, state) -> bool` — Basic ON/OFF hysteresis.
- `solar_controller(T_collector, T_tank_bottom, T_tank_top, dT_on, dT_off, state, max_tank_temp=353.15, freeze_protection=False, T_freeze_on=277.15, T_freeze_off=283.15) -> Tuple[bool, str]` — Adds overheat cutoff and freeze-protection band. Reason strings: "overheat_protection", "freeze_protection", "freeze_protection_off", "differential_on", "differential_off", "steady".
- `controller_series(T_collector_series, T_tank_bottom_series, T_tank_top_series, dT_on, dT_off, initial_state=False, **params) -> Tuple[list, list]` — Iterating variant.

**`solar_loop/pump.py`**
- `pump_flow_rate(speed, speed_max, flow_max, curve_type="linear", **curve_params) -> float` — Curve types: "linear", "quadratic", "custom" (polynomial coefficients a0..a3).
- `pump_power(speed, speed_max, power_max, curve_type="cubic", **curve_params) -> float` — Affinity law P ∝ N³ default.
- `pump_speed_from_flow(flow_target, flow_max, speed_max, curve_type="linear", **curve_params) -> float` — Inverse lookup.
- `pump_ledger(speed, speed_max, flow_max, power_max, **params) -> Dict[str, float]` — Audit record.

**`solar_loop/pipes.py`**
- `pipe_heat_loss(m_dot, T_in, T_amb, length, diameter, insulation_R, cp=4180.0) -> Tuple[float, float]` — NTU-effectiveness formulation along pipe length.
- `pipe_pressure_drop(m_dot, length, diameter, roughness=0.0, rho=997.0, mu=0.001) -> float` — Darcy-Weisbach. Laminar Re<2300 → f=64/Re; turbulent → Swamee-Jain approximation placeholder. Constants: PI = 3.141592653589793.
- `pipe_energy_ledger(m_dot, T_in, T_out, cp=4180.0) -> Dict[str, float]` — Audit record.
- `collector_loop_thermal(T_collector_out, m_dot, T_tank_in, T_amb, registry) -> Tuple[float, float, Dict[str, float]]` — Combined supply+return loss. Registry keys: `loop.supply_length` (default 10.0), `loop.supply_diameter` (default 0.02), `loop.supply_R` (default 1.0); same pattern for return pipe.

### Step 5: Water Treatment (`water_treatment/`) *(coded, not yet in runnable path)*

Six individual stage models assembled into three pathway trains. Each stage returns `(quality_out_dict, ledger_dict)` tracking mass balance.

#### File-by-file detail

**`water_treatment/stages.py`**
- `sediment_filter(flow, quality_in, dt, parameters) -> Tuple[Dict[str, float], Dict[str, Any]]` — Required params: `turbidity_removal`, `tss_removal`. Optional: `pressure_drop` (default 5000 Pa).
- `carbon_filter(flow, quality_in, dt, parameters) -> ...` — Params: `doc_removal`, `chlorine_removal`, `voc_removal`. Optional: `pressure_drop` (default 10000 Pa).
- `uv_disinfection(flow, quality_in, dt, parameters) -> ...` — Params: `uv_dose`, `log_reduction_bacteria`, `log_reduction_virus`. Optional: `power` (default 100 W). Log-reduction formula: `C_out = C_in × 10^(−LR)`.
- `ultrafiltration(flow, quality_in, dt, parameters) -> ...` — Params: `tss_removal`, `turbidity_removal`, `bacteria_removal`, `virus_removal`. Optional: `pressure_drop` (default 50000 Pa), `flux` (default 50).
- `nanofiltration(flow, quality_in, dt, parameters) -> ...` — Params: `hardness_removal`, `doc_removal`, `sulfate_removal`, `tds_removal`. Optional: `bacteria_removal` (default 6.0), `virus_removal` (default 4.0), `pressure_drop` (default 1000000 Pa), `recovery` (default 0.85).
- `remineralization(flow, quality_in, dt, parameters) -> ...` — Params: `target_hardness`, `target_alkalinity`, `target_ph`.

Water quality species handled: turbidity, tss, doc, chlorine, voc, ecoli, total_coliform, virus, hardness, sulfate, tds, alkalinity, ph.

**`water_treatment/train.py`**
- `pathway_a(flow, quality_in, dt, parameters) -> Tuple[Dict[str, float], List[Dict[str, Any]]]` — Sediment → Carbon → UV.
- `pathway_b(flow, quality_in, dt, parameters) -> ...` — Sediment → Carbon → UF → UV.
- `pathway_c(flow, quality_in, dt, parameters) -> ...` — NF → Remineralization → UV.
- `run_treatment_train(pathway, flow, quality_in, dt, parameters) -> ...` — Dispatcher accepting "a"/"pathway_a", "b"/"pathway_b", "c"/"pathway_c".
- `treatment_train_series(pathway, flow_series, quality_series, dt, parameters) -> Tuple[List[Dict[str, float]], List[List[Dict[str, Any]]]]` — Iterating variant.

### Step 6: MNT Decision Engine (`mnt/`) *(coded, not yet in runnable path)*

Selects the least-intensive pathway that still meets product-quality limits.

#### File-by-file detail

**`mnt/oracle.py`**
- `water_quality_index(quality, parameters) -> float` — Score range 0–100.
- `pathway_cost(pathway, flow, parameters) -> Dict[str, float]` — Components: `capital_per_m3h`, `energy_per_m3`, `consumable_per_m3`, `maintenance_per_m3`. Flow conversion: m³/s → m³/h via ×3600.
- `mnt_oracle(quality, flow, pathways_available, parameters) -> Tuple[str, Dict[str, Any]]` — Picks cheapest feasible pathway; falls back to most advanced (last in list) if none feasible. Lazy-imports `aquasolar.water_treatment.train.run_treatment_train`.
- `mnt_oracle_series(quality_series, flow_series, pathways_available, parameters) -> Tuple[List[str], List[Dict[str, Any]]]` — Iterating variant.

**`mnt/controller.py`**
- `sensor_readings(quality, sensor_config) -> Dict[str, float]` — Applies noise_percent (default 0.0).
- `sensor_based_controller(sensor_data, flow, pathways_available, parameters) -> Tuple[str, Dict[str, Any]]` — Immediate switching.
- `hysteresis_controller(sensor_data, current_pathway, flow, pathways_available, parameters) -> Tuple[str, Dict[str, Any]]` — Cost threshold 0.1 prevents chatter.
- `adaptive_controller(sensor_data, current_pathway, flow, pathways_available, parameters, performance_history) -> Tuple[str, Dict[str, Any]]` — Looks back 10 periods. Min quality score default 80.0.
- `controller_ledger(decision, flow, pathway) -> Dict[str, Any]` — Audit record.

**`mnt/sensors.py`**
- Class `WaterQualitySensor(parameter, detection_limit, noise_percent, range_min=0.0, range_max=1000.0, drift_per_day=0.0)` — Methods: `read(true_value) -> float`, `calibrate(reference_value) -> None`, `advance_time(dt_days) -> None`. Below detection limit returns half DL. Drift formula: `bias += drift_per_day * days_since_calibration / 365`.
- `create_sensor_suite(config) -> Dict[str, WaterQualitySensor]` — Defaults: noise_percent=5.0, drift_per_day=0.01, range_max=1000.0.
- `read_sensor_suite(sensors, true_quality) -> Dict[str, float]`
- `calibrate_sensor_suite(sensors, reference_quality) -> Dict[str, float]`
- `sensor_health_check(sensors, thresholds) -> Dict[str, Dict[str, Any]]` — Defaults: max_days=30.0, max_bias=0.1.
- `simulate_sensor_fouling(sensor, quality, dt_days, fouling_rate=0.001) -> None`

### Step 7: Electrical Balance (`electrical/`) *(coded, not yet in runnable path)*

Per-timestep power accounting:

```
Sources:    P_pvt (from collector) + P_battery_discharge + P_grid_import
Sinks:      P_load + P_aux_heater + P_pump + P_battery_charge + P_grid_export + P_curtailment
```

**`electrical/balance.py`**
- `electrical_balance(P_pvt, P_aux_heater, P_pump, P_load, P_battery_charge=0.0, P_battery_discharge=0.0, grid_import_limit=inf, grid_export_limit=inf, battery_soc=0.5, battery_capacity=0.0, battery_max_charge=0.0, battery_max_discharge=0.0) -> Tuple[Dict[str, float], Dict[str, Any]]` — Power flows dict keys: `P_pvt`, `P_aux_heater`, `P_pump`, `P_load`, `P_battery_charge`, `P_battery_discharge`, `P_grid_import`, `P_grid_export`, `P_curtailment`, `P_net`, `battery_soc`. SOC clamped to [0, 1]. Energy change uses 3600 s/h conversion.
- `electrical_balance_series(...) -> Tuple[List[Dict[str, float]], List[Dict[str, Any]]]` — Iterating variant.
- `battery_dispatch(P_pvt, P_load, battery_soc, battery_capacity, battery_max_charge, battery_max_discharge, grid_import_price, grid_export_price, strategy="self_consumption") -> Tuple[float, float, str]` — Strategies: "self_consumption", "arbitrage" (charge when export_price < 0.8×import_price), "backup".

### Step 8: Economics (`economics/lcoe.py`) *(standalone functions, awaiting integration)*

| Function | Purpose |
|----------|---------|
| `levelized_cost(capex, opex_annual, lifetime, discount_rate, output_annual, currency="$") -> Dict[str, Any]` | CRF-based LCOE: `(capex×CRF + opex) / annual_output`. Capital Recovery Factor: `crf = discount_rate / (1 - (1+discount_rate)^(-lifetime))`. |
| `simple_payback(capex, annual_savings, currency="$") -> Dict[str, Any]` | capex / annual_savings |
| `discounted_payback(capex, annual_cashflows, discount_rate, currency="$") -> Dict[str, Any]` | Cumulative discounted cashflow crossing zero |
| `npv(capex, annual_cashflows, discount_rate, currency="$") -> Dict[str, Any]` | Standard net present value |
| `lifecycle_cost(capex, opex_annual, replacement_costs, lifetime, discount_rate, currency="$") -> Dict[str, Any]` | Capex + Σ(opex/(1+r)^t) + replacement events |
| `bottlen_water_comparison(system_cost_per_liter, bottled_price_per_liter, annual_volume, liters_per_bottle=0.5, currency="$") -> Dict[str, Any]` | Cost-per-liter vs bottled baseline × annual volume. ⚠️ Typo in name ("bottlen" missing 'd'). |

### Step 9: Uncertainty & Sensitivity (`uncertainty/`) *(standalone functions)*

**`uncertainty/monte_carlo.py`**
- `monte_carlo_run(model_function, param_distributions, n_samples=19, seed=None, **kwargs) -> Dict[str, Any]` — Samples from normal/uniform/triangular/beta/lognormal distributions; propagates through any callable; returns mean/std/median/min/max/n statistics.
- `latin_hypercube_sample(param_distributions, n_samples, seed=None) -> List[Dict[str, float]]` — LHS alternative to random sampling.
- Private helpers: `_sample_distribution(spec, param_name)`, `_compute_statistics(outputs)`, `_median(values)`, `_std(values)`.
- Historical audit note: the lognormal branch references `math.log` without a module-level `math` import; this branch is outside the current PVT-only run path.

**`uncertainty/sobol.py`**
- `compute_sobol_indices(model_function, param_bounds, param_names, sample_size=25, num_outputs=1, seed=3) -> Dict[str, Any]` — SALib variance decomposition → S1 (first-order), ST (total-order) with confidence intervals. Returns `{"error": "SALib not installed"}` if missing.
- `morris_screening(model_function, param_bounds, param_names, num_levels=9, num_samples=11, seed=3) -> Dict[str, Any]` — Elementary-effects method → μ*, σ rankings.
- `fast_sobol(model_function, param_bounds, param_names, sample_size=25, num_outputs=1, seed=3) -> Dict[str, Any]` — Fourier Amplitude Sensitivity Test alternative.

### Step 10: Reporting (`reporting/`) *(standalone functions)*

**`reporting/metrics.py`**
- `compute_metrics(simulation_results, registry) -> Dict[str, Any]` — Computes ~52 named metrics: M-PV-01..03, M-TH-01..07, M-IN-01, M-EL-01..07, M-WQ-01..06, M-MNT-01..05, M-EC-01..07, M-EN-01..02, M-SC-01. Many currently stubbed to 0.0 pending full-system run.
- `generate_report(simulation_results, metrics, registry, format="json") -> str` — Formats: "json", "text".
- `summary_dashboard(simulation_results, metrics) -> Dict[str, Any]`

**`reporting/dashboard.py`**
- `generate_html_dashboard(simulation_results, metrics, title="AquaSolar Living Simulation") -> str` — Self-contained HTML with inline CSS (Arial font; colors #2c3e50, #ecf0f1, #27ae60, #7f8c8d, #34495e). Displays headline KPIs: M-PV-01, M-TH-01, M-TH-03, M-EL-03.
- `generate_json_report(simulation_results, metrics, registry) -> str` — Machine-readable report keyed to registry hashes.

### Reproducibility Layer (`integration/manifest.py`)

Every run produces a `manifest.json` capturing: git commit hash (truncated to 8 chars), environment fingerprint (currently "placeholder"), SHA-256 of every input file, gate sign-off hashes, solver settings, seeds, scenario id, timestamps. Enables bit-for-bit reproduction later.

- Class `Manifest(run_id, code_commit, environment_hash, input_hashes, gate_signoff_hashes, seeds, solver_settings, scenario_id, start_time, end_time=None, test_summary=None)` — Methods: `to_dict()`, `write(output_path)`.
- `write_manifest(run_id, output_dir, input_hashes, seeds, solver_settings, scenario_id, gate_signoff_hashes=None, test_summary=None) -> Manifest` — Uses `git.Repo(search_parent_directories=True)` for commit info. Writes to `output_dir / "manifest.json"`.

---

## Top-Level Orchestration Files

| File | Role |
|------|------|
| `cli.py` | Argparse dispatcher: `check-inputs`, `run <id>`, `ui`, `apply-demo-defaults`. Routes `run` to `pvt.runner.run_pvt_only()` only. Scenario ID validated against regex `[A-Za-z0-9._-]+`. |
| `__main__.py` | Thin wrapper enabling `python -m aquasolar`. |
| `ui.py` | Tkinter app with Parameters, Data inputs, Outputs, and Run & plots tabs. Supports scenario/weather selection and graphical post-processing of saved PVT-only results. |
| `defaults.py` | One-shot seeder: fills eligible unset params from `_DOCUMENTED` table (design-basis citations) or seeded RNG within quantity-kind bounds. Generated values receive source metadata and are marked `confirmed`. Deliberately leaves `pvt_th.T_fluid_max` unset/draft because the supplied sources establish no maximum for this PVT collector. Writes provenance manifest to `inputs/provenance/demo_defaults.yaml`. Seed = `20261029`. Preserves existing non-null values; idempotent across reruns. |
| `integrator.py` | `AquaSolarSimulator` class wiring all subsystem imports; `simulate_step()` chains PVT → loop → tank → MNT → treatment → electrical sequentially. Currently unused by CLI but structurally complete. Helper functions: `_simulate_pvt`, `_simulate_loop`, `_simulate_tank`, `_simulate_mnt`, `_simulate_treatment`, `_simulate_electrical` — each wraps the corresponding module call with try/except fallback. |
| `simulate.py` | `run_simulation(registry, weather_series, initial_tank_state, initial_water_quality, draw_series, dt=300.0, max_steps=..., verbose=False) -> Dict[str, Any]` — Driver iterating weather series, calling `simulator.simulate_step()` per tick, accumulating energy/pathway/electrical summaries. Has `__main__` smoke-test block with synthetic registry/weather/quality/draw arrays. |

---

## Coding Conventions Enforced by Tests

### Numeric Literal Rule (R2)

Only literals `0`, `1`, `2` may appear directly in `src/**/*.py`. Everything else must be:
- From registry: `registry["pvt_th.U_L"]`
- Passed as argument
- String-wrapped float: `float("273.15")`, `float("1e-6")`
- Arithmetic expression: `1 + (1+1)*(1+1+1+1+1)` = 11; `2**(1+2+2+2+2+2+2+2+2+2+2+2+2)` = 8192

Enforced by `tests/unit/test_literal_scan.py` which AST-parses every source file. Violation fixture lives at `tests/toy_fixtures/bad_literal_fixture.py` containing `CONST_VIOLATION = 42`.

**Rationale:** Forces every physical constant to trace back to a documented source (datasheet, literature, standard, or labelled assumption) rather than being silently baked into code. Makes provenance auditable and prevents accidental reuse of wrong values across scenarios.

**Tradeoff:** Significantly reduces readability. New contributors should expect arithmetic-obfuscated constants throughout and refer to the registry / equation register for actual numeric meanings.

### Ledger Pattern

Nearly every physics function returns `(primary_result, ledger_dict)` where ledger records component name, quantity, energy/mass in/out, generated amount, and residual for audit trails. Example keys: `component`, `quantity`, `in`, `out`, `generated`, `residual`.

### Series Variants

Most single-step functions have a companion `_series()` iterator accepting lists and returning lists, avoiding repeated boilerplate in time-loop drivers.

---

## Testing Suite (`tests/unit/`)

| Test file | Covers | Approx count |
|-----------|--------|-------------|
| `test_literal_scan.py` | AST violation detector + toy fixture catch | 3 |
| `test_conditions.py` | required_when grammar parsing/evaluation | 7 |
| `test_registry.py` | Schema validation, error formatting, load cycle | 7 |
| `test_units.py` | Temp vs ΔT parsing, Pint/fallback equivalence | 4 |
| `test_pvt.py` | electrical_output, useful_heat, coupled solver convergence, pv_only | 9 |
| `test_pvt_runner.py` | Parameter loading, unit conversion, azimuth convention handling | several |
| `test_tank.py` | Grid init, mixing energy conservation, draw tempering | 8 |
| `test_water_treatment.py` | All 6 stages individually + pathways A/B/C assembly | 9 |
| `test_electrical.py` | Surplus/deficit routing, battery SOC bounds, dispatch modes | 5 |
| `test_uncertainty.py` | MC stats, Sobol/Morris/FAST graceful absence of SALib | 7 |
| `test_economics.py` | LCOE/payback/NPV/lifecycle/bottled comparison edge cases | 10 |
| `test_reporting.py` | Metric computation, JSON/text report generation | 6 |
| `test_epw.py` | EPW header parsing, data-row mapping, sentinel handling | several |
| `test_nasa_power.py` | JSON field mapping, UTC enforcement, consecutive-timestamp check | several |
| `test_ui_catalog.py` | Catalog loaders read real project files without crashing | several |
| `test_defaults.py` | Seeder idempotency, provenance writing, preservation of existing values | several |

The test totals in this inventory are historical. The auxiliary tank-heating
module is now named `aquasolar.tank.auxiliary_heating`; the shorter `aux`
filename conflicted with a reserved Windows device name and could not be
tracked. The full test suite now passes.

---

## Historical Bugs & Technical Debt Notes

These audit findings are retained as historical context and have not all been
reverified. The unused `InvalidInputError` import in `registry/load.py` and
late `Tuple` import in `solar_loop/controller.py` were removed or normalized
during the 2026-11-10 cleanup. The CLI still routes `run` to the PVT-only
runner; full-system integration remains future work.

---

## Running the Simulation Today

```powershell
# From repo root
pip install -e ".[solar,dev]"     # installs aquasolar + pvlib + pytest

# Option A: Fill inputs manually, validate, run
python -m aquasolar check-inputs
python -m aquasolar run my-scenario-001

# Option B: Apply seeded demo defaults first (exploratory only!)
python -m aquasolar apply-demo-defaults
python -m aquasolar check-inputs
python -m aquasolar run demo-run

# GUI mode
python -m aquasolar ui

# Tests
python -m pytest tests/unit/ -v

# Literal scan verification
python -c "from tests.unit.test_literal_scan import scan_py_files; from pathlib import Path; v = scan_py_files(Path('src')); print(f'Violations: {len(v)}')"
```

Output lands in `outputs/pvt_only/<scenario_id>.csv` (hourly rows) and `<scenario_id>.summary.json` (aggregates + metrics + limitations array).

---

## Dependencies

Core (`pyproject.toml`):
- numpy ≥ 1.23.2
- pandas ≥ 1.5.0
- pyyaml ≥ 6.0
- pydantic ≥ 2.0
- scipy ≥ 1.9.2
- matplotlib ≥ 3.5
- hypothesis ≥ 6.0
- ruamel.yaml ≥ 0.18

Optional extras:
- `[units]`: pint ≥ 0.23
- `[solar]`: pvlib[all] ≥ 0.15 (required for PVT-only runner)
- `[sensitivity]`: SALib ≥ 1.4 (for Sobol/Morris/FAST)
- `[properties]`: iapws ≥ 1.5 (temperature-dependent fluid properties)
- `[dev]`: pytest ≥ 7.0, pytest-cov ≥ 4.0

Python: ≥ 3.10 (developed/tested on 3.14).

---

## Design References

| Document | Role |
|----------|------|
| `AquaSolar_TRNSYS_Master_Direction.md` §3.2 | Primary design basis; source of many `_DOCUMENTED` parameter values |
| `coolpv_technical_data_sheet.md` | Corrected summary of two conventional solar-thermal cogeneration papers; neither specifies this PVT collector's outlet limit |
| `ARE_RK_Khaimah.Intl.AP.411840_TMYx.epw` | Typical meteorological year for Ras Al Khaimah airport station; provides site elevation (31.1 m) and weather series |
| `docs/equation_register.md` | All approved equations (EQ-PVT-01..04, EQ-TK-01..05, etc.) with IDs referenced in code comments |
| `docs/metric_definitions.md` | All 52 output metrics (M-PV-01 through M-SC-01) with numerator/denominator/time-base definitions |
| `docs/library_decisions.md` | Approved third-party library list with rationale |
| `docs/units_accepted.md` | Accepted unit strings per quantity_kind |
| `docs/quantity_kinds.yaml` | SI dimension mappings for 35+ quantity kinds |
| `environment.lock` | Pinned dependency versions for reproducibility |

---

## Current Summary

This report is an inventory of intended and implemented modules, not evidence
that the complete system has been scientifically validated. The supported
end-to-end path is the exploratory PVT-only runner; the other subsystem
modules are not orchestrated by the CLI. The PVT path uses explicit fixed-flow
and fixed-inlet assumptions, so its outputs need calibration and validation
before engineering interpretation. See [README.md](README.md) for the current
setup, UI, and command-line workflow.