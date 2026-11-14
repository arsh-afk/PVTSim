# AquaSolar — Pre-Submission Critique Report (Carnot 2026)

**Date:** 2026-11-14 · **Prepared for:** competition presentation tomorrow
**Scope:** full audit of the `Simulation/` folder against the Carnot 2026 rules
(`Simulation/carnot.pdf`): reproducibility, transparency, verification,
team capability, simple-defensible models, and the submission package itself.

**Verdict up front:** the project is genuinely strong on provenance,
assumption honesty, and equation transparency — those are Carnot's core
criteria and you should lead with them. But there are **blocking defects** in
both code trees that a judge running the commands will hit immediately, plus a
broken claim in the packaged validation statement. All are fixable tonight.

**Confidence tags:** ✅ verified by running it just now · ⚠️ likely issue ·
ℹ️ polish/judgement call.

---

## 1. BLOCKING — fix before anything else

### 1.1 The competition package fails its own test suite ✅
`CARNOT2026_AquaSolar` (the folder you present as the submission) fails
verification exactly the way Carnot says judges will try it:

```
python -m pytest tests -q
→ ERROR collecting tests/unit/test_weather_converter.py
  ModuleNotFoundError: No module named 'aquasolar.io.weather_converter'
→ 3 failed, 134 passed (with that file ignored)
```

- `tests/unit/test_weather_converter.py` imports a module that does not exist
  in the package's `src/aquasolar/io/`. Either ship the converter module or
  delete the test — a collection **error** aborts the whole run, so judges see
  zero results.
- After ignoring it, three tests still fail:
  - `test_epw.py::test_rejects_missing_runner_required_irradiance[14-DNI]`
  - `test_epw.py::test_rejects_missing_runner_required_irradiance[15-DHI]`
  - `test_web.py::test_evaluator_navigation_and_model_diagrams_explain_execution_scope`

`REPORT.md` §10 and `README.md` both promise `python -m pytest -q` as part of
the reproduction workflow. Carnot explicitly rewards reproducibility and
penalizes unverifiable claims — a judge running this and seeing failures is
the worst-case scenario. **Fix or remove the failing tests tonight.**

### 1.2 The dev tree fails too (different failures) ✅
Outer `Simulation/` tree: `6 failed, 145 passed`. Root causes:

| Failure | Cause | Fix |
|---|---|---|
| `test_design.py::test_ensemble_is_reproducible_for_the_same_seed` (also out-of-range test) | `design.py:126` does `int("7fffffff")` — a **hex** string passed to base-10 `int()` → `ValueError: invalid literal` | use `int("7fffffff", 16)` in all 4 places (lines 126–130) |
| `test_literal_scan.py` (2 tests) | the scan no longer detects `42` in the toy fixture — the enforcement test of your R2 convention silently regressed | check the scanner's regex/AST walk against `tests/toy_fixtures/bad_literal_fixture.py`; likely a path/glob regression |
| `test_web.py::test_run_preflight_blocks_missing_pvt_requirements` | preflight returns 400, test expects 409 — an API-contract drift after the recent preflight work | align status code or update the test intentionally |
| `test_web.py::test_module_toggles_require_preview_and_disable_pvt_runs` | same area of `web.py` | inspect and reconcile |

Both PROJECT_REPORT.md and README.md contain the literal sentence *"The
complete suite passes with `python -m pytest -q`"* — that is now a false
claim in your submitted docs. Fix the code or soften the sentence; don't
leave both broken.

### 1.3 The package's own validation claim references nonexistent files ✅
`CARNOT2026_AquaSolar/model/validation.md` says the packaged scenario
`carnot-demo` "result files are retained at `outputs/`". **The
`CARNOT2026_AquaSolar/outputs/` directory does not exist at all** ✅ (verified
with `Test-Path`). README.md:76 repeats the claim. This is precisely the
"reproducibility artifact" a judge will look for first. Either:

- run the demo inside the package and commit `outputs/pvt_only/carnot-demo.csv`
  + `.summary.json`, **or**
- change the wording to "regenerate with `python -m aquasolar run carnot-demo`"
  and say explicitly that outputs are not bundled.

Related ✅: running the package's documented workflow (`check-inputs` then
`run`) **works** — the runner wrote results to the **outer** `Simulation/outputs/`
folder, not into `CARNOT2026_AquaSolar/outputs/`. That means the package
resolves the project root to the parent tree on your machine (likely via a
hardcoded/upward search). On a clean clone of just the package this either
fails or writes outside the package — test on a fresh clone/folder copy
before presenting. (I cleaned up my probe outputs.)

### 1.4 Root-path resolution / dual-tree confusion ✅ (structural)
You have two nearly identical trees: outer `Simulation/src/aquasolar` and
`Simulation/CARNOT2026_AquaSolar/src/aquasolar`, which have already drifted
(one has `runner.py` error-handling and `module_registry.py` differences; the
package has `io/weather_converter.py` referenced but missing, and a
`tests/test_analysis.cjs`-style stray). Risks: editing the wrong tree before
the presentation; judges diffing the package against the white paper. **Pick
one canonical tree for tomorrow (the package) and say so.**

---

## 2. HIGH — credibility & compliance risks

### 2.1 Overclaiming in the competition report ⚠️
Carnot rewards *honest* scoping; the package mostly does this well (§12 of
REPORT.md is good). But watch these specific sentences:

- REPORT.md §11: *"validation path includes … test suite execution"* — the
  suite currently fails (1.1). This sentence becomes false tomorrow.
- REPORT.md §10: implies metrics `M-IN-01`, water-quality and economics
  metrics are produced by the run. ✅ Verified: a real run's summary contains
  **only** `M-PV-01` and `M-TH-01`; everything else is not computed in the
  runnable path. Add one sentence: "only M-PV-01 and M-TH-01 are produced by
  the runnable path; the remaining 50 metric definitions are specified but not
  yet populated."
- README (outer): *"The complete suite passes…"* — see 1.2.
- `inputs/STATUS.md` marks every parameter `'confirmed'`, including seeded
  demo assumptions. Your own README warns "'confirmed' does not mean measured
  or calibrated" — a judge skimming STATUS.md will see 100% confirmed and may
  conclude provenance theatre. Consider a `source` column in STATUS.md, or at
  least a header note.

### 2.2 Physics inconsistencies a sharp judge can poke ✅
- **Soiling factor is wired nowhere.** EQ-PVT-01 (both `REPORT.md` and
  `model/equations.md`) includes φ_soil; the runner uses
  `poa × (1 − shading_loss)` only and never reads a soiling parameter
  (`soiling.mode = none` is enforced). Present the equation with φ_soil or
  state "φ_soil = 1 in the exploratory configuration".
- **IAM missing too:** `pvt_el.iam_model = none` enforced; G_eff in REPORT §6
  includes IAM. Same fix — one sentence of honesty.
- **`T_fluid_max` provenance:** package STATUS shows `pvt_th.T_fluid_max =
  358.15 K, confirmed`. The outer tree deliberately leaves it unset because
  "no supplied source establishes a safe limit". If the package sourced
  358.15 K from a real reference, cite it in the defence; if it is a demo
  assumption, say so *before* a judge asks.
- **Reported energies vs. expectations:** package demo gives 2,143 kWh_el /
  3,560 kWh_th per year for the collector; outer demo 2,218/2,550. Prepare a
  one-line sanity argument (per-m² yield, collector area) so numbers don't
  look invented. Also note `useful_heat` uses the fixed-inlet assumption
  (A-03), so it *will* overstate deliverable heat — that's already in your
  limitations, keep it on a slide.

### 2.3 Reproducibility gaps ⚠️
- `integration/manifest.py` exists but the PVT-only runner (`run_pvt_only`)
  writes **no manifest** — PROJECT_REPORT advertises manifest.json per run as
  a reproducibility pillar. Either wire it in (small: hash inputs + summary)
  or demote the claim.
- Weather metadata: ✅ `inputs/timeseries/weather.meta.yaml` exists and the
  package copies it — good. Ensure the package's weather source is named
  consistently in REPORT §9 (it says "representative Abu Dhabi profile"; your
  station files are RAK airport TMYx / Abu Dhabi TM2 — name the actual station).

### 2.4 Renderer/deploy claim ⚠️
README promises a public Render read-only showcase (`render.yaml` verified to
exist ✅ with `AQUASOLAR_READ_ONLY=true`). If the live URL isn't up tomorrow,
cut the claim or have a local fallback (`python -m aquasolar web-ui`) as the
demo path. A dead link on a slide is worse than no link.

---

## 3. MEDIUM — code quality (things judges won't run but reviewers notice)

### 3.1 The numeric-literal convention has visibly degraded ⚠️
R2 (only literals 0/1/2) is your signature discipline, but:
- `design.py` uses `int("7fffffff")` (broken hex — see 1.2);
- recent error-handling code (my own addition, `runner.py`) uses
  `float("273.15")`-style consistently — fine;
- `defaults.py`, `web.py`, `tm2.py` use string-wrapped ints extensively —
  convention-compliant but genuinely hard to read live. For the defence,
  have `docs/equation_register.md` open, not source code.

Fix the `int(...,16)` bug; then re-run `test_literal_scan` and repair the
scanner regression (1.2) so the convention claim survives.

### 3.2 Known-but-unfixed internal bugs ℹ️
From your own audit notes (PROJECT_REPORT §Historical):
- `uncertainty/monte_carlo.py` lognormal branch references `math.log` with no
  `math` import — one-line fix, do it (a judge reading the file will spot it).
- `economics/lcoe.py`: typo'd function name `bottlen_water_comparison`.
  One-line rename + alias if anything imports it.
- `integrator.py`'s try/except fallbacks swallow exceptions silently — if you
  demo the full-system class at all, add logging, or don't demo it.

### 3.3 Packaging hygiene ℹ️
- `Simulation/.tmp_tools/` contains an **entire vendored Python environment**
  (fastapi, numpy, pvlib site-packages — thousands of files) inside the
  project. Exclude it from any zip/archive you submit; it looks like
  environment contamination and bloats the package enormously.
- `.pytest_cache/`, `__pycache__/`, `.venv` — same, exclude.
- `archive/nonessential/` holds competition PDFs and older reports — make sure
  the *current* report is unambiguous about which document is authoritative
  (`CARNOT2026_AquaSolar/REPORT.md` vs outer `PROJECT_REPORT.md`, whose header
  itself admits it is stale). Consider a one-line banner in PROJECT_REPORT.md:
  "superseded by CARNOT2026_AquaSolar/REPORT.md".
- `pyproject.toml` includes `pytest` in core dependencies and pins nothing
  (`environment.lock` exists ✅ — cite it in the defence for reproducibility).

### 3.4 Documentation debt ℹ️
- README references `DATA_ENTRY_GUIDE.md` — ✅ exists in outer tree; confirm it
  also exists in the package tree or fix the link.
- REPORT.md §14 says disclosure "should disclose" — DISCLOSURE.md ✅ already
  does this adequately (prior work + AI usage). Good; reference it explicitly
  from REPORT §14 instead of describing it in future tense.
- `docs/change_requests/` and `docs/model_specs/` appear empty — remove or
  populate.

---

## 4. What is genuinely strong — lead with these tomorrow

1. **Provenance architecture**: every parameter has `source_type`,
   `source_ref`, `status`; seeded assumptions are labelled; the runner hard-
   blocks on placeholder sources (`tbd`, `example`, …). This is rare and
   exactly what Carnot asks for.
2. **Equation registry** (`model/equations.md`): EQ-PVT-01..04 map 1:1 to
   `electrical.py`, `thermal.py`, `coupled.py`. Present this mapping slide.
3. **Assumptions register** (`model/assumptions.md` A-01..A-10): each has
   statement / why needed / impact if violated. This is the defensible-model
   criterion in one page — memorize A-03 (fixed inlet) and A-10 (exploratory
   outputs) for Q&A.
4. **Validation-before-run**: 27 required parameters, unit-kind conversions,
   hourly-interval and timestamp checks; refuse-to-overwrite scenario IDs.
5. **Honest limitation arrays** embedded in every result JSON.

---

## 5. Suggested fix order for tonight (est. total ~2–3 h)

| # | Action | Effort | Impact |
|---|---|---|---|
| 1 | Fix or delete `tests/unit/test_weather_converter.py` in the package | 5 min | unblocks entire suite |
| 2 | Fix 3 remaining package test failures (`test_epw` irradiance params, `test_web` nav test) | 30–60 min | green suite |
| 3 | `int("7fffffff")` → `int("7fffffff", 16)` ×4 in outer `design.py` | 2 min | kills 2 test failures |
| 4 | Repair literal-scan regression (outer) | 20 min | restores R2 enforcement claim |
| 5 | Reconcile the two `test_web.py` preflight failures (400 vs 409) in whichever tree you present | 20 min | green suite |
| 6 | Generate + commit `carnot-demo` outputs inside the package **or** fix `validation.md` + README wording | 10 min | validation claim true |
| 7 | Verify package runs from a **fresh clone location** (root-path resolution) | 15 min | live-demo safety |
| 8 | One-slide honesty pass: φ_soil=1, IAM=none, only M-PV-01/M-TH-01 populated | 15 min | prevents worst Q&A moment |
| 9 | `math` import in monte_carlo.py; rename `bottlen_water_comparison` | 10 min | polish |
| 10 | Exclude `.tmp_tools/`, caches from any submitted archive; delete probe outputs | 5 min | packaging |

---

*Verified-by-execution summary (2026-11-14): outer suite 6F/145P; package
suite 1 collection error + 3F/134P; package `check-inputs` exit 0; package
`run` exit 0 (writes to outer outputs dir); package `outputs/` absent;
carnot.pdf read from rendered pages (submission = report + presentation +
code package + live defence; judging = reproducibility, transparency,
verification, team capability; simple defensible > complex weak).*
