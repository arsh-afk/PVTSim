# Input-to-calculation flow

This chart follows the current `aquasolar run <scenario_id>` implementation.
It describes the exploratory PVT-only runner, not the complete AquaSolar
system. The browser workbench and `check-inputs` can validate broader project
inputs, but `run` does not implicitly execute the general input check.

```mermaid
flowchart TD
    U["User values and choices"] --> UI["Browser workbench or parameter YAML"]
    UI --> P["inputs/parameters/*.yaml"]
    D["apply-demo-defaults (optional)"] --> P
    D --> M["inputs/provenance/demo_defaults.yaml"]
    P --> LP["Load PVT parameters<br/>require values, confirmed status,<br/>traceable source, supported units and modes"]

    W["inputs/timeseries/weather.csv"] --> LW["Load hourly weather<br/>timestamp, GHI, DNI, DHI,<br/>ambient temperature, wind speed"]
    WM["Companion metadata<br/>documents units and provenance;<br/>not read by the PVT runner"] -. describes .-> LW
    LW --> WV["Validate required columns,<br/>finite values, ordered regular<br/>one-hour timestamps"]

    LP --> SP["Solar position at each<br/>hourly interval midpoint<br/>(latitude, longitude, elevation)"]
    WV --> SP
    SP --> POA["Plane-of-array irradiance<br/>pvlib isotropic transposition<br/>(GHI, DNI, DHI, tilt, azimuth, albedo)"]
    WV --> POA
    POA --> EFF["Apply fixed shading factor<br/>G_eff = POA × (1 − shading loss)"]
    LP --> EFF

    EFF --> FD["Estimate solar gain and choose flow<br/>positive irradiance and gain → fixed mass flow<br/>otherwise → zero flow"]
    LP --> FD
    WV --> STEP["Hourly weather and inlet conditions<br/>ambient °C converted to K;<br/>fixed demo inlet temperature"]
    LP --> STEP
    FD --> SOLVE{"PVT collector calculation"}
    STEP --> SOLVE
    EFF --> SOLVE

    SOLVE -->|flow is positive|         COUPLED["Coupled solver iterates T_cell and T_f_out<br/>eta = max(0, eta_ref × [1 − beta × (T_cell − T_ref)])<br/>P_el = eta × phi_soil × G_eff × A × f_mpp (phi_soil = 1 in the supported no-soiling mode)<br/>Q_u = A × F_R × [tau_alpha × G_eff − P_el/A − U_L × (T_in − T_ambient)]<br/>T_f_out = T_in + Q_u/(mass_flow × fluid_cp)<br/>outlet bounded by configured fluid maximum"]
    SOLVE -->|zero flow| NOFLOW["Zero-flow branch<br/>outlet equals inlet; useful heat is zero;<br/>estimate cell temperature and electrical power"]
    LP --> COUPLED
    LP --> NOFLOW

    COUPLED --> ROW["Hourly results<br/>P_el, Q_u, T_cell, T_f_out,<br/>flow, POA, convergence"]
    NOFLOW --> ROW
    ROW --> SUM["Accumulate hourly energy<br/>and calculate run averages"]
    ROW --> CSV["outputs/pvt_only/<scenario_id>.csv"]
    SUM --> JSON["outputs/pvt_only/<scenario_id>.summary.json<br/>energy totals, averages, named PVT metrics,<br/>scope and limitations"]

    OTHER["Other registered inputs<br/>tank, DHW, electrical bus,<br/>water treatment, economics, etc."] -. not consumed by this runner .-> OUT["Outside the current PVT-only run"]
    OTHER --> OUT

    classDef boundary fill:#fff3cd,stroke:#9a6700,color:#222;
    class OTHER,OUT boundary;
```

## What drives the current run

The PVT runner reads the following parameter groups from YAML:

- **Site and orientation:** `site.latitude`, `site.longitude`,
  `site.elevation`, `site.collector_tilt`, `site.collector_azimuth`,
  `site.azimuth_convention`, `site.ground_albedo`, and
  `site.shading_loss_factor`.
- **Electrical collector:** `pvt_el.eta_ref`, `pvt_el.T_ref`,
  `pvt_el.beta`, `pvt_el.mpp_assumption`, and
  `pvt_el.mpp_efficiency_factor`.
- **Thermal collector:** `pvt_th.collector_area`, `pvt_th.tau_alpha`,
  `pvt_th.F_R`, `pvt_th.U_L`, `pvt_th.R_cell_fluid`,
  `pvt_th.T_fluid_max`, and `pvt_th.demo_inlet_temperature`.
- **Loop fluid:** `loop.mass_flow_fixed` and `loop.fluid_cp`.
- **Supported model choices:** the runner currently requires no soiling,
  no irradiance or incidence-angle correction, no wind-dependent heat loss,
  and the steady-state Hottel–Whillier-form thermal model.

The current fixed-inlet flow decision uses an estimated gain based on
`(tau_alpha - eta_ref) × G_eff - U_L × (T_in - T_ambient)`. The calculation
does not implement pump hysteresis, tank feedback, or a dynamic inlet
temperature. Although wind speed is required in the weather CSV and passed to
the collector interface, the supported no-wind-dependence mode does not use it
to modify `U_L`.

The coupled solver computes temperature-dependent electrical efficiency, PVT
electrical power, useful heat, cell temperature, and fluid outlet temperature.
Electrical power includes the no-soiling factor (fixed to 1 by the supported
mode) and applies the configured MPP factor only for the user-efficiency
assumption. The zero-flow branch uses the same temperature-adjusted electrical
model but reports zero useful heat and inlet temperature at the outlet. It
reports convergence and stops the run on a solver failure. Hourly power is
integrated over each one-hour interval for the summary energies.

## Module status in the workbench

`inputs/module_registry.yaml` records user-persisted enablement separately from
implementation status. `pvt_runner` is the current operational module.
Enabling another module reveals its associated inputs and preparation
requirements, but does not execute that module or block a PVT-only run.
Disabling `pvt_runner` blocks both CLI and browser PVT runs. Module toggles are
staged and require the same preview and explicit apply flow as other project
input changes; they never delete parameter values.

The general input index contains many additional parameters; their presence or
validation does not mean they participate in this runner. See
[`DATA_ENTRY_GUIDE.md`](../DATA_ENTRY_GUIDE.md) for input editing, validation,
and run instructions. The implementation is in
[`runner.py`](../src/aquasolar/pvt/runner.py),
[`collector.py`](../src/aquasolar/pvt/collector.py), and
[`coupled.py`](../src/aquasolar/pvt/coupled.py).
