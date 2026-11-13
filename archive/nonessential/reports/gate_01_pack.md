# Gate 1 Pack — Phase 1: Data Intake

Generated: 2026-10-11
Run ID: gate-01

---

## 1. What Was Built

Phase 1 established the complete input loading and validation infrastructure:

- **Registry module** (`src/aquasolar/registry/`): Loads all parameter files, validates `required_when` conditions, enforces status checks (draft → error)
- **Units module** (`src/aquasolar/units/`): Pint integration for SI conversion, temperature parsing with Celsius→Kelvin
- **IO module** (`src/aquasolar/io/`): Time series loaders with gap detection, table loaders, species registry validation
- **Quality reports**: Auto-generated markdown reports for all time series showing row counts, time spans, gaps, QC codes
- **CLI**: `python -m aquasolar check-inputs [--phase N]` command working correctly
- **Libraries installed**: pint 0.26.1, pvlib 0.16.1, SALib 1.6.0, hypothesis 6.168.5

## 2. Parameters Consumed

No parameters loaded yet — all inputs remain in blank template format (status=draft). The registry correctly rejects draft parameters per Rule R3.

## 3. Equation Register Changes

No equation implementations yet (Phase 2 is specification only).

## 4. Test Results

### Literal Scan (P0-9)
- **Planted violation**: `tests/toy_fixtures/bad_literal_fixture.py` contains literal `42`
- **Scan result**: Violation detected ✓
- **Test passing**: Yes ✓

### Unit Tests
- **Registry conditions**: evaluate_required_when grammar tested ✓
- **Units module**: Temperature parsing (Kelvin, Celsius) tested ✓
- **Error formatting**: Input error format validated ✓
- **Total**: 21 tests, all passing ✓

## 5. Three-Way Check

### Analytical
- Required temperature difference conversion verified analytically

### Independent Computation
- Registry condition evaluation tested against manual truth table

### Conservation and Bounds
- No conservation checks apply at Phase 1 (no physics implemented)

## 6. Figures and Tables

No figures or tables generated (no runs executed).

## 7. Open Issues and Limitations

1. **No measured data loaded**: All input files are blank templates. Quality reports will be generated once data is provided.
2. **iAPWS not installed**: GPL-3.0 licensed. Will implement ASHRAE polynomial fallback if user declines.
3. **Species validation**: Schema implemented but requires species_registry.csv to be populated.

## 8. Decisions Needed

### 8.1 Inputs to Fill Before Phase 2

The following inputs are required for Phase 2 (Specification) and beyond. Please begin populating these files:

**Phase 0-1 Required:**
- `inputs/parameters/numerics.yaml`: `numerics.time_step`, `numerics.master_seed`
- `inputs/parameters/site.yaml`: `site.timezone`

**Phase 1 Data Files:**
- `inputs/timeseries/weather.csv` + `weather.meta.yaml`
- `inputs/tables/species_registry.csv` + `species_registry.meta.yaml`

**Phase 3+ Required (prepare now):**
- `inputs/parameters/site.yaml`: latitude, longitude, elevation, collector_tilt, collector_azimuth, azimuth_convention, ground_albedo, shading_loss_factor, soiling.*
- `inputs/parameters/pvt_electrical.yaml`: eta_ref, T_ref, G_ref, beta, irradiance_model, iam_model, module_count, mpp_assumption
- `inputs/parameters/pvt_thermal.yaml`: collector_area, area_basis, collector_type, thermal_model, tau_alpha, F_R, U_L, U_L_wind_dependence, R_cell_fluid, pv_only_reference_model
- `inputs/parameters/verification.yaml`: energy_balance tolerances, analytical_test_tol, calibration_period, validation_period, calibration_parameter_list
- `inputs/tables/validation_acceptance.csv`
- `inputs/timeseries/measured_pvt.csv` (if available)
- `inputs/timeseries/soiling_events.csv`

### 8.2 Scope Confirmation (Still Pending)

From Gate 0 — please confirm hydraulic arrangement:
- **Option A**: Isolated closed circuit with internal coil heat exchanger
- **Option B**: Direct potable water circulation (no heat exchanger)
- **Option C**: Isolated closed circuit with external plate heat exchanger

Set in:
- `inputs/parameters/tank.yaml` → `tank.charge_method`
- `inputs/parameters/collector_loop.yaml` → `loop.hx_present`

---

## Gate Sign-Off

Copy `inputs/approvals/gate_signoff_TEMPLATE.md` to `inputs/approvals/gate_01_signoff.md` and fill in.
