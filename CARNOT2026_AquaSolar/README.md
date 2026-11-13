# AquaSolar Living — Carnot 2026 Submission

The package root is also the runnable simulation project root. Install, run the
CLI, open the browser UI, and run tests from this directory; there is no need to
change into a nested simulation folder.

## Requirements

- Python 3.12 is the validated setup (the package metadata permits Python 3.10+)
- pip

## Install

Run these commands from `CARNOT2026_AquaSolar/`:

```bash
# macOS/Linux
python3.12 -m venv .venv

# Windows PowerShell
py -3.12 -m venv .venv
```

Activate the virtual environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Then install the project and its solar-weather dependency:

```bash
python --version  # Confirm this reports Python 3.12.x
python -m pip install -e ".[solar]"
```

## Run the simulation

The only end-to-end runnable model is an exploratory, fixed-inlet PVT-only
simulation. Tank dynamics, DHW demand, electrical-bus dispatch, and water
treatment are not integrated into a runnable full-system simulation.

Validate registered inputs:

```bash
python -m aquasolar check-inputs
```

Run the included weather scenario:

```bash
python -m aquasolar run carnot-reproduction --weather inputs/timeseries/weather.csv
```

Results are written under `outputs/pvt_only/`. The packaged reference results
are in `outputs/pvt_only/` under the `carnot-demo` scenario ID. Scenario IDs
must be unique; use a different ID for a fresh run rather than overwriting the
packaged reference.

The command `python -m aquasolar apply-demo-defaults` can populate blank
exploratory settings, but does not make assumptions into measured or calibrated
values. A PVT run requires a supported maximum fluid-temperature parameter and
traceable source. Review the input provenance before interpreting results.
Outputs are exploratory estimates, not validated engineering, cost, safety, or
potable-water results.

## Launch the browser UI

From the package root, run:

```bash
python -m aquasolar web-ui
```

Open the localhost URL printed by the command (normally
`http://127.0.0.1:8765`). The web UI and command-line tools use the same local
inputs and outputs. Use one editor at a time to avoid overwriting changes.

## Run tests

```bash
python -m pytest -q
```

## Package map

| Path | Contents |
|---|---|
| `src/aquasolar/` | Simulation package and command-line/browser interfaces |
| `tests/` | Test suite |
| `inputs/` | Parameters, time series, tables, provenance, and validation status |
| `outputs/` | Pre-generated reference results |
| `docs/` | Equation, assumption, limitation, and metric registers |
| `model/` | Submission-facing model equations, assumptions, variables, and validation |
| `data/` | Weather data and source notes |
| `references/` | Bibliography and supporting references |

Treat all inputs as data, and keep measured values, literature-derived values,
and assumptions distinct.
