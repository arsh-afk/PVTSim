# AquaSolar Living Simulation

AquaSolar is a research prototype for a villa-scale photovoltaic-thermal (PVT)
and water-assurance system. **The only end-to-end runnable simulation is an
exploratory, fixed-inlet PVT-only estimate.** Tank dynamics, DHW demand,
electrical-bus dispatch, and water treatment are not integrated into a
runnable full-system simulation. Outputs are not validated engineering,
cost, safety, or potable-water results.

## Setup on Windows

From PowerShell:

```powershell
Set-Location "C:\path\to\waterresearch\Simulation"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[solar]"
```

Use the actual path to this `Simulation` directory on your computer. The
`solar` extra installs pvlib, required by the PVT calculation.

## Run the desktop interface

```powershell
.\.venv\Scripts\python.exe -m aquasolar ui
```

In the UI, use **Run & plots** to choose a unique scenario ID and compatible
weather CSV, start a run, inspect saved runs, and view power, irradiance,
temperature, cumulative-energy, or power-duration plots. The Matplotlib toolbar
can zoom, pan, and save figures.

## Run the browser workbench

```powershell
.\.venv\Scripts\python.exe -m aquasolar web-ui
```

If a run reports that `pvlib` is missing, from the project root install the
solar extra into the same Python environment used to launch the workbench:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[solar]"
```

Restart the workbench after installing dependencies.

Open the printed `http://127.0.0.1:8765` address. The workbench searches
parameters, data files and columns, outputs, metrics, saved runs, and
validation findings. Parameter edits and replacement CSV/metadata files remain
staged until you preview validation and explicitly apply them. The service
binds to localhost and writes only registered project inputs.

The Validation view checks parameter types, requiredness, configured ranges,
allowed values, units and provenance; paired CSV/metadata contracts; required
cells and numeric values; timezone-aware ordered timestamps, sampling gaps,
declared quality codes, and metadata-declared key/cross-field constraints.
Undeclared physical limits are not inferred. Errors block a PVT run; warnings
remain visible for review.

The browser and desktop UIs use the same local project files. Use one editor at
a time to avoid overwriting changes from another open UI or external editor.

## Deploy a public read-only showcase to Render

The root `render.yaml` defines a public Render web service for exploring the
project inputs, validation report, model trace, and any saved results. The
hosted service is read-only: it rejects edits, uploads, and PVT runs, while
allowing read-only whole-system screening calculations. It does not require
persistent storage.

1. Push this repository, including `render.yaml` and `.python-version`, to
   GitHub. The Python version file should contain `3.12`.
2. In Render, choose **New +** → **Blueprint**, connect the repository, and
   deploy the `aquasolar-readonly` service defined in `render.yaml`.
3. Open the public URL Render provides. The first build installs the project
   and its `solar` extra.

The service is public, so treat all committed project inputs and metadata as
public information. Render deploys the committed branch contents; local,
uncommitted files are not uploaded.

## Run from the command line

Apply the optional seeded exploratory preset if inputs are blank, then validate
and run:

```powershell
.\.venv\Scripts\python.exe -m aquasolar apply-demo-defaults
.\.venv\Scripts\python.exe -m aquasolar check-inputs
.\.venv\Scripts\python.exe -m aquasolar run my-scenario
```

The preset preserves existing values and labels generated assumptions. It
does not establish a safe maximum outlet temperature for this PVT collector;
a PVT run requires a verified limit and a real source reference before it can
proceed. Review
`inputs/provenance/demo_defaults.yaml` and the parameter sources; “confirmed”
does not mean measured or calibrated.

If run preflight reports that `pvt_th.T_fluid_max` has no usable `source_ref`,
check the saved parameter in `inputs/parameters/pvt_thermal.yaml`. A value
typed in the browser remains staged until it has been previewed and explicitly
applied; the literal `none` is a placeholder, not a source reference. Do not
invent a citation for this safety-relevant limit.

The PVT-only output column `T_f_out_K` is the collector-fluid outlet, not a
pipe outlet. This runner resets the inlet to the fixed
`pvt_th.demo_inlet_temperature` for every weather interval; it does not model
pipe heat loss, tank storage, recirculation, or temperature accumulation.
`pvt_th.T_fluid_max` is a solver upper bound, not a requested outlet
temperature. It must also be greater than the fixed inlet temperature or the
temperature solver has no valid interval. A reference such as `example` is
also a placeholder, not a traceable source. Thus, entering a higher limit alone
will not make the simulated outlet hotter.

To select another compatible weather file:

```powershell
.\.venv\Scripts\python.exe -m aquasolar run another-scenario --weather inputs/timeseries/other_weather.csv
```

The weather CSV must contain hourly `timestamp`, `ghi`, `dni`, `dhi`,
`t_ambient`, and `wind_speed` columns. Scenario IDs must be unique; a run
refuses to overwrite existing results.

Results are written to `outputs/pvt_only/<scenario_id>.csv` and
`outputs/pvt_only/<scenario_id>.summary.json`.

## Convert a TRNSYS TM2 weather file

The supported TRNSYS TM2 input uses a fixed-width TMY2 record layout; its
values are not named columns that can be reordered. `convert-tm2` validates the
station header, every record's exact width and fields, date sequence, flags,
sentinels, and full 8,760-hour non-leap year before writing a CSV and metadata
sidecar. It also validates the current PVT parameters first and never edits
them. Unsupported TM2 layouts are rejected rather than guessed.

For the supplied Abu Dhabi station file, run this from the `Simulation`
directory:

```powershell
.\.venv\Scripts\python.exe -m aquasolar convert-tm2 `
  ..\AE-Abu-Dhabi-Intl-412170.tm2 `
  inputs\timeseries\weather_abu_dhabi_2025.csv `
  --calendar-year 2025 --site-timezone Asia/Dubai
```

The converter records the TM2 station's fixed UTC offset and warns if its
coordinates differ from the existing PVT site parameters. It does not change
the modeled site. Use the resulting weather with the existing parameter set:

```powershell
.\.venv\Scripts\python.exe -m aquasolar run abu-dhabi-2025 `
  --weather inputs\timeseries\weather_abu_dhabi_2025.csv
```

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The complete suite passes with `python -m pytest -q`. The auxiliary tank-heating
module is named `aquasolar.tank.auxiliary_heating` so it can be tracked on
Windows without colliding with the reserved `AUX` device name.

## Project references

- [Data entry guide](DATA_ENTRY_GUIDE.md): input conventions, UI, and weather conversion.
- [Agent instructions](AGENT_INSTRUCTIONS.md): current scope and project-specific rules.
- [Project report](PROJECT_REPORT.md): subsystem inventory and current integration limits.
- `inputs/parameters/` and `inputs/input_index.yaml`: parameter values, requirements, and provenance.
- `docs/`: equations, assumptions, limitations, and metric definitions.

Treat all inputs as data, and keep measured values, literature values, and
assumptions distinct.
