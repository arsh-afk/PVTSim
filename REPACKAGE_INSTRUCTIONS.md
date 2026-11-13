# Repackaging Instructions for Carnot 2026

> **Goal:** Restructure the `waterresearch/` directory into a clean submission
> package that satisfies every requirement of the **Carnot 2026** mathematical
> modelling competition (Afkar 2026, IIT Delhi – Abu Dhabi, 15 November 2026).

---

## 1. What the Competition Requires (from `carnot.pdf`)

| Requirement | Where it applies |
|---|---|
| **Choose a real-world energy problem** and develop a **mathematical model** | The AquaSolar PVT + water-assurance system is the chosen topic |
| **Submit a report** describing the problem, model, assumptions, results, interpretation | Deliverable 1 below |
| **Include everything needed to reproduce results** – data, code, tests | Deliverable 2 below |
| **Defend it live** in a 15-min presentation + 5-min Q&A | Deliverable 3 below |
| Model must be the **team's own work** (prior published work by team members allowed if disclosed) | Disclosure section in report |
| **Simplicity with well-justified assumptions** beats poorly-defended complexity | Guides what to keep vs. cut |
| **Not** a literature review, software build without math, or black-box prediction | Report must foreground the math |
| **Novel** and **relevant** topics are rewarded | Frame the unique contribution |

### Evaluation Weights

| Criterion | Weight |
|---|---|
| Submission quality (relevance 10% + novelty 20% + rigour 30%) | 60% |
| Presentation segment (presentation quality 10% + ability to defend 30%) | 40% |

---

## 2. Current State Assessment

### Strengths (keep & showcase)
- **5 tightly-coupled PVT equations** (EQ-PVT-01 through EQ-PVT-05) with bisection solver
- **Equation register** (`docs/equation_register.md`) with 28+ equations across PVT, Loop, Tank, Water, MNT, Electrical, Economics
- **52 named output metrics** (`docs/metric_definitions.md`)
- **End-to-end runnable PVT-only path** with real Abu Dhabi weather data
- **Test suite** (82+ tests) enforcing a numeric-literal traceability rule (R2)
- **Interactive web UI** with parameter editing, validation, run control, and charting
- **Uncertainty/sensitivity analysis** module (Monte Carlo, Sobol, Morris)
- All inputs are externalized in YAML/CSV with provenance tracking

### Weaknesses (address before submission)
- The **full-system runner** (tank → loop → treatment → electrical → economics) is coded but **not wired** into the CLI
- The **assumptions register** is empty
- Many equations have `status: proposed` and `reference: citation needed`
- The report (`PROJECT_REPORT.md`) is an implementation inventory, not a competition-grade narrative
- There is **no presentation deck**
- The directory contains large media files (>1 GB of videos) that must not be submitted

---

## 3. Submission Package Structure

Create a **new directory** (or clean copy) called `CARNOT2026_AquaSolar/` with the
following layout. Everything the judges need must be inside this folder.

```
CARNOT2026_AquaSolar/
├── README.md                          ← Quick start: how to install, run, reproduce
├── REPORT.md (or REPORT.pdf)          ← The competition report (Deliverable 1)
├── PRESENTATION.pptx (or .pdf)        ← The slide deck (Deliverable 3)
├── DISCLOSURE.md                      ← Prior-work disclosure (Sec 3.1 of carnot.pdf)
│
├── model/                             ← The mathematical model (core)
│   ├── equations.md                   ← All equations in LaTeX with derivations
│   ├── assumptions.md                 ← Every assumption, numbered and justified
│   ├── variables.md                   ← Complete variable table (symbol, meaning, unit, source)
│   └── validation.md                  ← Model vs. data comparison, error analysis
│
├── simulation/                        ← The runnable code (Deliverable 2)
│   ├── pyproject.toml
│   ├── src/aquasolar/                 ← Full source tree (copied from Simulation/src/)
│   ├── tests/                         ← Full test suite (copied from Simulation/tests/)
│   ├── inputs/                        ← Parameter & data files (copied from Simulation/inputs/)
│   └── outputs/                       ← Pre-generated results for reference
│
├── data/                              ← Input data with provenance
│   ├── weather/                       ← Weather CSVs + metadata (from inputs/timeseries/)
│   ├── parameters/                    ← Symlink or copy of inputs/parameters/
│   └── sources.md                     ← Where each dataset came from
│
└── references/                        ← Supporting literature
    ├── bibliography.md                ← Formatted citation list
    └── pdfs/                          ← Key reference PDFs (only those you cite)
```

---

## 4. Step-by-Step Repackaging Commands

Run all commands from PowerShell in the `waterresearch/` directory.

### Step 4.1 — Create the submission directory

```powershell
$root = "C:\Users\arsh2\OneDrive - American University of Ras Al Khaimah\Fall2026\waterresearch"
$dest = "$root\CARNOT2026_AquaSolar"

New-Item -ItemType Directory -Path $dest -Force
New-Item -ItemType Directory -Path "$dest\model" -Force
New-Item -ItemType Directory -Path "$dest\simulation" -Force
New-Item -ItemType Directory -Path "$dest\data\weather" -Force
New-Item -ItemType Directory -Path "$dest\data\parameters" -Force
New-Item -ItemType Directory -Path "$dest\references\pdfs" -Force
```

### Step 4.2 — Copy the simulation code (everything needed to reproduce)

```powershell
# Core simulation package
Copy-Item -Recurse "$root\Simulation\src"          "$dest\simulation\src"
Copy-Item -Recurse "$root\Simulation\tests"        "$dest\simulation\tests"
Copy-Item -Recurse "$root\Simulation\inputs"       "$dest\simulation\inputs"
Copy-Item -Recurse "$root\Simulation\outputs"      "$dest\simulation\outputs"
Copy-Item -Recurse "$root\Simulation\docs"         "$dest\simulation\docs"
Copy-Item          "$root\Simulation\pyproject.toml"  "$dest\simulation\pyproject.toml"
Copy-Item          "$root\Simulation\README.md"       "$dest\simulation\README.md"

# Weather data for data/ folder
Copy-Item "$root\Simulation\inputs\timeseries\weather.csv"         "$dest\data\weather\" -ErrorAction SilentlyContinue
Copy-Item "$root\Simulation\inputs\timeseries\weather.meta.yaml"   "$dest\data\weather\" -ErrorAction SilentlyContinue

# Parameters
Copy-Item "$root\Simulation\inputs\parameters\*" "$dest\data\parameters\"
```

### Step 4.3 — Copy cited reference PDFs (only papers you actually reference)

```powershell
# Copy only the papers you cite in the report bibliography
Copy-Item "$root\1-s2.0-S1876610214033001-main.pdf"           "$dest\references\pdfs\"
Copy-Item "$root\1-s2.0-S1944398624116128-main.pdf"           "$dest\references\pdfs\"
Copy-Item "$root\1-s2.0-S1944398624128810-main.pdf"           "$dest\references\pdfs\"
Copy-Item "$root\Performance_analysis_of_solar_cogenerati.pdf" "$dest\references\pdfs\"
Copy-Item "$root\FULLTEXT02.pdf"                               "$dest\references\pdfs\"
```

### Step 4.4 — Exclude large/irrelevant files

Do **NOT** copy:
- `Video/` (1+ GB of lab footage — irrelevant to submission)
- `AquaSolar Living.mp4` (80 MB video)
- `AquaSolar_model_code.zip` (redundant archive of older code)
- `AquaSolar_model_code/` (older code snapshot)
- `.obsidian/` (personal notes app config)
- `carnot.pdf` (the competition rules themselves)
- `White_Paper_Template_1.docx` (blank template)
- Any `__pycache__/`, `.pytest_cache/`, `*.egg-info/` directories

```powershell
# Clean up copied pycache and build artifacts
Get-ChildItem -Path $dest -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $dest -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force
Get-ChildItem -Path $dest -Recurse -Directory -Filter "*.egg-info" | Remove-Item -Recurse -Force
```

---

## 5. Documents to Write

### 5.1 — `REPORT.md` (or export to PDF)

This is 60% of your score. Structure it as follows:

```markdown
# AquaSolar Living: A Mathematical Model for Villa-Scale Solar
  Cogeneration and Water Assurance in the UAE

## 1. Introduction & Problem Statement
   - Energy and water challenges in UAE residential sector
   - Why PVT + water treatment at villa scale is novel and relevant

## 2. System Description
   - Architecture diagram (PVT collector → tank → treatment → grid)
   - What the model does and does not include

## 3. Mathematical Model
   ### 3.1 PVT Coupled Electro-Thermal Model
   - EQ-PVT-01 through EQ-PVT-04 in LaTeX
   - Solver architecture (bisection on T_out, inner T_c iteration)
   - Convergence proof / tolerance analysis

   ### 3.2 Thermal Storage (Stratified Tank)
   - EQ-TNK-01 through EQ-TNK-08
   - Node energy balance, advection, conduction, mixing

   ### 3.3 Water Treatment Pathways
   - Pathway A/B/C stage models
   - Minimum Necessary Treatment (MNT) optimization objective

   ### 3.4 Electrical Balance & Economics
   - EQ-ELC-01, EQ-ECO-01
   - Battery dispatch strategies

## 4. Assumptions
   - Numbered list, each with justification
   - Explicitly state what is NOT modelled

## 5. Input Data & Calibration
   - Weather data source (TMY Abu Dhabi, EPW station 412170)
   - Parameter provenance table
   - Sensitivity analysis results (Sobol/Morris)

## 6. Results & Interpretation
   - PVT-only hourly simulation plots
   - Key metrics: M-PV-01, M-TH-01, M-IN-01
   - Uncertainty bounds

## 7. Limitations & Future Work

## 8. Conclusions

## References
```

> [!IMPORTANT]
> The judges will evaluate whether you **understand everything you submit**.
> Every equation must have a derivation or justification you can defend live.
> Do not include modules you cannot explain in Q&A.

### 5.2 — `model/equations.md`

Convert every equation from `docs/equation_register.md` into proper LaTeX.
Example conversion:

**Before** (current `equation_register.md`):
```
Form: P_el = eta_ref * [1 - beta * (T_c - T_ref)] * phi_soil * G_eff * A * f_irr * f_mpp
```

**After** (for `model/equations.md`):
```latex
$$P_{el} = \eta_{ref} \left[1 - \beta \left(T_c - T_{ref}\right)\right]
           \cdot \varphi_{soil} \cdot G_{eff} \cdot A \cdot f_{irr} \cdot f_{MPP}$$
```

Do this for all 28+ equations. Group them by subsystem.

### 5.3 — `model/assumptions.md`

Populate with every assumption from the code and docs. Currently the
assumptions register in `docs/assumptions_register.md` is **empty**. Extract
assumptions from:

| Source | Examples |
|---|---|
| `equation_register.md` | "Cell temperature is uniform across collector", "Steady-state conditions" |
| `pvt/coupled.py` | Fixed inlet temperature, no pipe loss, no recirculation |
| `tank/step.py` | Ideal mixing model, constant ρ and cp |
| `README.md` | "outputs are not validated engineering results" |
| `defaults.py` | All seeded demo values are assumptions until calibrated |

### 5.4 — `model/variables.md`

Create a complete variable index table:

| Symbol | Name | Unit | Source | Registry ID |
|---|---|---|---|---|
| $\eta_{ref}$ | Reference electrical efficiency | — | Datasheet | `pvt_el.eta_ref` |
| $\beta$ | Temperature coefficient | K⁻¹ | Datasheet | `pvt_el.beta` |
| ... | ... | ... | ... | ... |

Extract from `equation_register.md` variable lists and `inputs/input_index.yaml`.

### 5.5 — `DISCLOSURE.md`

Per Section 3.1 of `carnot.pdf`:

```markdown
# Prior Work Disclosure

This project builds on AquaSolar Living, a research project developed at
the American University of Ras Al Khaimah under CMAT-00184 Theme 5.

## Prior Publications
- AquaSolar Living Final White Paper (AURAK, 2026) — authored by [team members]
- CMAT-00184 Theme 5 Final Report (AURAK, 2026) — authored by [team members]

## New Work for Carnot 2026
- [List specific new contributions: e.g., MNT optimization formulation,
  sensitivity analysis, web-based model explorer, etc.]
```

### 5.6 — `README.md` (submission root)

```markdown
# CARNOT2026 — AquaSolar Living

## Quick Start (Reproduce Results)

### Prerequisites
- Python ≥ 3.10
- pip

### Install & Run
```powershell
cd simulation
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[solar]"
.\.venv\Scripts\python.exe -m aquasolar apply-demo-defaults
.\.venv\Scripts\python.exe -m aquasolar check-inputs
.\.venv\Scripts\python.exe -m aquasolar run demo
```

### Run Tests
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Launch Interactive UI
```powershell
.\.venv\Scripts\python.exe -m aquasolar web-ui
```

## Directory Guide
| Folder | Contents |
|---|---|
| `model/` | Mathematical model documentation (equations, assumptions, variables) |
| `simulation/` | Runnable Python code, inputs, tests, outputs |
| `data/` | Input datasets with provenance |
| `references/` | Cited literature |
```

### 5.7 — `references/bibliography.md`

List every source cited in the report. Mark which ones are included as PDFs
in `references/pdfs/`. Use a consistent format (e.g., APA or IEEE).

---

## 6. Critical Actions Before Submission

### 6.1 — Fill citation gaps

The equation register currently has **"citation needed"** for every equation's
reference field. Before submission, each equation must trace to:
- A textbook (e.g., Duffie & Beckman for Hottel-Whillier)
- A paper (the PDFs already in the repo)
- A datasheet (CoolPV or equivalent)
- Or be marked as a team-derived formulation with justification

### 6.2 — Populate the assumptions register

Every assumption currently scattered in code comments and equation notes must
be collected into `model/assumptions.md` with:
- A unique ID (A-01, A-02, ...)
- The assumption statement
- Why it is necessary
- Its impact if violated

### 6.3 — Run and capture fresh results

```powershell
cd "$dest\simulation"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[solar]"
.\.venv\Scripts\python.exe -m aquasolar apply-demo-defaults
.\.venv\Scripts\python.exe -m aquasolar run carnot-demo
.\.venv\Scripts\python.exe -m pytest -q
```

Commit the output CSV and summary JSON into `simulation/outputs/` so judges
can verify without running the code.

### 6.4 — Verify reproducibility

Clone the submission folder to a different machine (or a fresh directory),
follow the README, and confirm:
- [ ] `pip install -e ".[solar]"` succeeds
- [ ] `python -m aquasolar check-inputs` passes
- [ ] `python -m aquasolar run test-repro` produces identical output
- [ ] `python -m pytest -q` all tests pass

### 6.5 — Prepare the presentation

- **15 minutes maximum** (content past 15 min is not evaluated)
- Ending early leaves more Q&A time → better "ability to defend" score (30%)
- Suggested structure:
  1. Problem & relevance (2 min)
  2. System architecture (2 min)
  3. Core equations + solver (4 min)
  4. Results & sensitivity (3 min)
  5. Limitations & conclusions (2 min)
  6. Live demo of web UI (2 min — optional, time permitting)

### 6.6 — Disclose AI tool usage

Per Section 7.2 of `carnot.pdf`: "Teams may use all tools and resources at
their disposal, as long as proper credit is given. This includes Large Language
Models (LLMs) and other AI tools, the use of which must be properly disclosed.
No marks will be deducted in any way for the use of such tools."

Add a section in the report or DISCLOSURE.md listing tools used (e.g.,
"Claude/GPT used for code generation and documentation drafting").

---

## 7. Submission Checklist

| # | Item | Status |
|---|---|---|
| 1 | `REPORT.md` or `REPORT.pdf` — complete narrative report | ☐ |
| 2 | `model/equations.md` — all equations in LaTeX | ☐ |
| 3 | `model/assumptions.md` — every assumption numbered and justified | ☐ |
| 4 | `model/variables.md` — complete variable table | ☐ |
| 5 | `model/validation.md` — model vs data comparison | ☐ |
| 6 | `simulation/` — full runnable code + inputs + tests + outputs | ☐ |
| 7 | `data/sources.md` — provenance of all input data | ☐ |
| 8 | `references/bibliography.md` — all citations | ☐ |
| 9 | `references/pdfs/` — cited PDFs included | ☐ |
| 10 | `DISCLOSURE.md` — prior work + AI tool disclosure | ☐ |
| 11 | `README.md` — reproduction instructions verified on clean install | ☐ |
| 12 | `PRESENTATION.pptx` — 15-min slide deck ready | ☐ |
| 13 | All `__pycache__`, `.egg-info`, `.pytest_cache` removed | ☐ |
| 14 | No files > 100 MB (videos, zips excluded) | ☐ |
| 15 | Test suite passes on clean install | ☐ |

---

## 8. Submission

**Deadline:** 13 November 2026, 11:59 PM GST

Upload the `CARNOT2026_AquaSolar/` folder to Google Drive or a Git repository.
Email the link to:

- **To:** Joel Jobi — `24A1CSEB0013@iitdabudhabi.ac.ae`
- **Subject:** `CARNOT2026 Final Submission - <TeamName>`

Ensure the link is accessible (set sharing to "Anyone with the link").

---

## 9. Timeline (Working Backward from 13 Nov)

| Date | Task |
|---|---|
| **Now → Nov 11** | Write report, fill assumptions, add citations, LaTeX-ify equations |
| **Nov 11** | Run fresh simulation, capture outputs, run tests |
| **Nov 12** | Reproduce on clean machine, finalize report |
| **Nov 12 evening** | Build presentation slides |
| **Nov 13 morning** | Final review, package directory, test link |
| **Nov 13, before 11:59 PM** | **Submit** |
| **Nov 14** | Confirm attendance if shortlisted |
| **Nov 15** | Present and defend |

