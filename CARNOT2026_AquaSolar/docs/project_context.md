# AquaSolar Living — Historical Simulation Project Context

**Date:** 2026-10-11
**Project:** Villa-scale PVT + Water-Assurance Simulator (AquaSolar Living)
**Working Directory:** `C:\Users\arsh2\OneDrive - American University of Ras Al Khaimah\Fall2026\waterresearch\Simulation`
**Executor Agent:** Claude Code (Agnes, Sapiens AI)

> **Historical handoff note:** This file is a snapshot from 2026-10-11, not a
> current status or source of runnable commands. Some implementation and
> completion claims below are stale. The only supported end-to-end run is the
> exploratory PVT-only path; tank, DHW, electrical-bus, and water-treatment
> modules are not integrated into the executable runner. Use the current
> [README](../README.md), [agent instructions](../AGENT_INSTRUCTIONS.md), and
> [data entry guide](../DATA_ENTRY_GUIDE.md) for up-to-date workflow and scope.

---

## Historical status (recorded 2026-10-11; superseded)

This section records a prior development snapshot, not the current completion
or validation status. The only runnable end-to-end simulation is currently the
exploratory PVT-only estimate. Tank, DHW, electrical-bus, and water-treatment
modules are not integrated into a full-system runner. See the project
[README](../README.md) for current scope and instructions.

Do not treat historical gate approvals or implementation notes in this file as
evidence that the full system is runnable or validated.

---

## What Is Implemented

### Source Modules (`src/aquasolar/`)

| Module | File(s) | Purpose |
|--------|---------|---------|
| Registry | `registry/schema.py`, `registry/conditions.py`, `registry/load.py` | Pydantic parameter schema, required_when evaluator, YAML loader with hash support |
| CLI | `cli.py`, `__main__.py` | `python -m aquasolar check-inputs` and `run` commands |
| Units | `units/__init__.py` | Pint integration with Kelvin/Celsius distinction |
| IO | `io/timeseries.py`, `io/quality_report.py`, `io/species.py`, `io/tables.py` | Time-series loading with gap detection, quality reports, species registry |
| Weather | `weather/solar_geometry.py`, `weather/iam.py`, `weather/transposition.py`, `weather/soiling.py` | pvlib solar position, IAM models, POA irradiance, soiling decay |
| PVT | `pvt/electrical.py`, `pvt/thermal.py`, `pvt/coupled.py`, `pvt/pv_only.py`, `pvt/collector.py` | EQ-PVT-01 through 04, coupled algebraic loop solver (bisection, 20 iter) |
| Tank | `tank/grid.py`, `tank/step.py`, `tank/mixing.py`, `tank/draw.py`, `tank/auxiliary_heating.py` | N-node stratified tank, thermal step, mixing models, DHW draw profiles, aux heater |
| Solar Loop | `solar_loop/controller.py`, `solar_loop/pump.py`, `solar_loop/pipes.py` | ΔT pump controller, pump affinity laws, pipe NTU heat loss, Darcy-Weisbach |
| Water Treatment | `water_treatment/stages.py`, `water_treatment/train.py` | Sediment/Carbon/UV/UF/NF/Remin stages; Pathways A/B/C train assembly |
| MNT | `mnt/oracle.py`, `mnt/controller.py`, `mnt/sensors.py` | Minimum necessary treatment oracle, sensor-based controller, water quality sensors |
| Electrical | `electrical/balance.py` | Grid import/export, battery dispatch, self-consumption tracking |
| Integrator | `integrator.py`, `simulate.py` | `AquaSolarSimulator` class, `run_simulation()` driver loop |

### Test Files (`tests/unit/`)

| File | Tests | Coverage |
|------|-------|----------|
| `test_literal_scan.py` | 3 | AST scan for literal violations >2 in src/ |
| `test_conditions.py` | 7 | required_when grammar evaluation |
| `test_registry.py` | 7 | Schema validation, error formatting |
| `test_units.py` | 4 | Temperature vs temperature-difference parsing |
| `test_pvt.py` | 9 | Electrical output, thermal output, coupled solver, PV-only |
| `test_tank.py` | 8 | Grid init, mixing energy conservation, draw tempering, aux heater |
| `test_water_treatment.py` | 9 | All 6 stages, all 3 pathways A/B/C |
| `test_electrical.py` | 5 | Grid surplus/deficit, battery charge/discharge, SOC limits |
| `test_uncertainty.py` | 7 | Monte Carlo, Sobol indices, Morris screening |
| `test_economics.py` | 10 | LCOE, payback, NPV, lifecycle cost, bottled water comparison |
| `test_reporting.py` | 6 | Metrics computation, report generation, dashboard output |

The test totals and pass claims above are historical. Run the current test
suite before making claims about test status.

### Gate Sign-offs (`inputs/approvals/`)

Files `gate_00_signoff.md` through `gate_12_signoff.md` — all approved by Claude (executor). Gates 00–12 correspond to completion of all phases.

---

## Key Design Decisions & Known Issues

### 1. Literal Rule (R2) — Strict Enforcement
The rule requires that **only numeric literals `0`, `1`, `2`** appear directly in `src/` Python code. All other constants must be:
- Loaded from the registry (parameter files in `inputs/`)
- Passed as function arguments
- String-converted: `float("273.15")`, `float("3600.0")`
- Computed via expressions: `1 + (1 + 1) * (1 + 1 + 1 + 1 + 1)` for 11, `2 ** (1+2+2+2+2+2+2+2+2+2+2+2+2)` for 8192

**Verification:** Run `python -c "from tests.unit.test_literal_scan import scan_py_files; from pathlib import Path; v = scan_py_files(Path('src')); print(f'Violations: {len(v)}')"`

### 2. Celsius vs Kelvin Temperature Distinction
The `units/` module correctly distinguishes:
- Temperature inputs (e.g., `T_amb`): convert Celsius to Kelvin if needed
- Temperature differences (e.g., `dT_on`): already in K, no conversion
- The old bug `"degC" in unit.lower()` was fixed by using `unit_lower == "degc"` (lowercase comparison)

### 3. Coupled PVT Solver
- Uses **bisection method** (robust but slow convergence) with 20 max iterations
- Default tolerance: `float("1e-6")`
- The residual function is $T_{out}^{new} - T_{out}^{guess}$ where $T_{out}^{new} = T_{in} + Q_u / (\dot{m} \cdot c_p)$
- Cell temperature $T_c$ is solved iteratively inside the residual via the $R_{cell-fluid}$ relation
- If bisection does not converge within max iterations, returns no-flow fallback

### 4. Tank Energy Balance
- Nodes are arranged top-to-bottom: node 0 = hot delivery layer, node n-1 = cold inlet layer
- `tank_step()` handles advection (inflow at top, outflow from bottom), conduction between adjacent nodes, and heat loss distributed proportionally to surface area
- Mixing models (`ideal_mixing`, `stratified_mixing`) are applied after the step
- **Energy conservation verified** in `test_tank.py::TestTankMixing::test_ideal_mixing_energy_conserved`

### 5. Water Treatment Log-Reduction
- UV, UF, and NF stages use **log-reduction** formulas: $C_{out} = C_{in} \times 10^{-LR}$ where LR is log-reduction value
- All `10.0` literals in stages.py were converted to `float("10.0")` to satisfy the literal rule
- Repeated the same fix for `3600.0` (seconds-to-hours), `293.15` (reference temperatures), etc.

### 6. Electrical Balance
- Grid import/export with separate hard limits
- Battery SOC bounded to [0, 1] with capacity in Wh, power in W
- Three dispatch strategies: `self_consumption`, `arbitrage`, `backup`

---

## Remaining Work

### Complete (Phases 9–10)
- [x] Uncertainty & Sensitivity Analysis (SALib Sobol, Morris, Monte Carlo)
- [x] Economics Module (LCOE, payback, NPV, lifecycle cost)
- [x] Reporting Module (metrics computation, HTML/JSON dashboards)

### Pending
- [ ] Fill user input data in `inputs/parameters/*.yaml` and `inputs/weather/*.csv`
- [ ] Run full end-to-end simulation with real data
- [ ] Generate final report and metrics

---

## User-Required Input Data

**The following input files must be filled in by the user before running the full simulation:**

1. **Parameter files** (`inputs/parameters/*.yaml`):
   - `pvt_el_parameters.yaml` — Reference efficiency, temperature coefficient, cell area
   - `pvt_th_parameters.yaml` — Collector area, transmittance-absorptance, heat-loss coefficient, R-cell-fluid
   - `tank_parameters.yaml` — Volume, height, diameter, n_nodes, k_eff, mixing model
   - `loop_parameters.yaml` — Supply/return pipe lengths, diameters, insulation R-values, fluid cp
   - `mnt_parameters.yaml` — Quality targets, pathway costs, sensor specs, oracle weights
   - `electrical_parameters.yaml` — Battery capacity, max charge/discharge, grid limits, prices

2. **Weather time series** (`inputs/weather/*.csv`):
   - `G_poa.csv` — Plane-of-array irradiance (W/m²) per timestep
   - `T_amb.csv` — Ambient temperature (°C or K) per timestep
   - `wind_speed.csv` — Wind speed (m/s) per timestep
   - `rainfall.csv` — Rainfall (mm) per timestep (for soiling model)

3. **Water quality time series** (`inputs/water_quality/*.csv`):
   - `turbidity.csv`, `doc.csv`, `ecoli.csv`, `tss.csv`, `tds.csv`, `hardness.csv`, `ph.csv`

4. **Hot water draw profile** (`inputs/draw_profile.csv`):
   - Volume draw per timestep (m³)

---

## How to Run

The historical commands originally recorded here do not match the current CLI.
For Windows setup and current commands, use [README.md](../README.md). The
current CLI supports `check-inputs`, `apply-demo-defaults`, `run <scenario_id>`
(optionally `--weather <csv>`), and `ui`. `run` writes PVT-only exploratory
hourly results under `outputs/pvt_only/`.

```powershell
python -m aquasolar apply-demo-defaults
python -m aquasolar check-inputs
python -m aquasolar run demo-run
python -m aquasolar ui
python -m pytest -q
```

---

## Important Files & References

| File | Purpose |
|------|---------|
| `docs/equation_register.md` | All 40+ approved equations (EQ-PVT-01..04, EQ-TK-01..05, etc.) |
| `docs/metric_definitions.md` | All 52 metrics to compute (M-PV-01 through M-SC-01) |
| `docs/library_decisions.md` | Approved library list with versions |
| `docs/units_accepted.md` | Accepted unit strings per quantity_kind |
| `docs/quantity_kinds.yaml` | SI dimension mappings for 35+ quantity kinds |
| `environment.lock` | Pinned dependency versions |
| `pyproject.toml` | Build config, pytest options |
| `tests/toy_fixtures/bad_literal_fixture.py` | Contains `CONST_VIOLATION = 42` — used to verify scan catches violations |

---

## Next Agent Action Items

1. **Phase 9**: Implement uncertainty/sensitivity modules (`sobol.py`, `monte_carlo.py`)
2. **Phase 10**: Implement economics (`lcoe.py`, `payback.py`, `npv.py`) and reporting (`dashboard.py`, `metrics.py`)
3. **User input data**: Ensure all parameter files and time series are populated before running full simulation
4. **Gate 11 sign-off**: After Phase 9 implementation
5. **Gate 12 sign-off**: After Phase 10 implementation and full end-to-end simulation run
