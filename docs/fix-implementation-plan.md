# AquaSolar Fix & Implementation Plan

**Prepared:** 2026-11-15  
**Inputs:** [CRITIQUE_REPORT.md](./CRITIQUE_REPORT.md),
[UI_CRITIQUE_REPORT.md](./UI_CRITIQUE_REPORT.md), and the additional
Parameters, Data Files, Validation, and Model-page feedback.

This is an implementation plan, not a claim that the listed changes are
complete. It combines the competition-readiness work with the UI redesign and
sets verification gates so documentation, implementation, and the demo agree.

## 1. Current baseline and decisions

The reports were written against two similar but divergent trees. Rechecking
them on 2026-11-15 found:

- The submission package's full test suite passes **141 tests** when run with
  that package's `src` on `PYTHONPATH`. In the shared environment, the plain
  command initially imported a different installed `aquasolar` package and
  could not find the package's weather converter. A clean editable install
  without `PYTHONPATH` is still required.
- The outer development tree has **152 passing tests and one failure**:
  `test_allows_zero_one_two`. The scanner finds many numeric literals in
  `design.py`; this is not just the reported planted-fixture detection
  regression. The `7fffffff` issue and reported Design Studio/API failures
  did not reproduce.
- The weather converter and EPW regression tests now exist in the package.
  The package's UI does not contain the Design Studio seen in the outer tree.
- The package has no `outputs/` directory or bundled run results. The outer
  tree has an `outputs/` directory, but no result files were found.
- `.tmp_tools/` exists in the outer tree. `DATA_ENTRY_GUIDE.md` was not found
  in either tree, despite documentation references.

### Decisions to make before implementation

1. **Canonical tree:** use
   [CARNOT2026_AquaSolar](../CARNOT2026_AquaSolar/) as the submission and
   demo source of truth. Freeze the outer tree or label it development-only.
   If both trees must remain maintained, define and test a deliberate sync
   process rather than editing them interchangeably.
2. **Design Studio scope:** decide whether the outer-only Design Studio is
   part of the promised submission. If yes, port the feature and dependencies
   into the canonical package before applying its fixes. If not, do not imply
   it is in the package or use it as the competition demo.
3. **Results policy:** after resolving the temperature-bound provenance below,
   either generate and include reproducible package results or state clearly
   that outputs are not bundled and show how to regenerate them.
4. **R2 numeric-literal policy:** decide whether the 0/1/2 rule applies to
   scientific/configuration constants. Preserve the rule only with a
   sustainable, explicit approach; do not make real constants opaque by
   converting them to strings.

## 2. Ordered implementation work

### Phase A — Establish a trustworthy submission baseline

#### A1. Make the package independently runnable

- In a clean copy of the canonical package, create the documented Python
  environment and install the project using its documented editable-install
  command.
- Without setting `PYTHONPATH`, run the full test suite, input check, one
  supported simulation, and WebUI startup.
- Confirm imports resolve from the canonical package and that all generated
  files remain under its own root. Do not rely on the neighboring development
  tree or a globally installed copy.

**Acceptance:** the commands documented in the package README work from a
clean copy, with no cross-tree reads/writes or import ambiguity.

#### A2. Resolve the outer tree's remaining test failure

- Inspect the numeric-literal findings in
  [design.py](../src/aquasolar/design.py) and decide which values are runtime
  algorithm literals versus user-facing/scientific configuration.
- If R2 remains global, move actual configuration into typed, documented data
  and preserve provenance. If it is intentionally scoped, update the scanner
  to encode narrow, reviewed exceptions and document the new boundary.
- Keep the planted bad-literal fixture test; it must still prove the scanner
  detects violations.
- Re-run the outer suite only if that tree remains supported. The previously
  reported `7fffffff`, Design Studio, and preflight status-code failures should
  not be changed unless they reappear.

**Acceptance:** the maintained tree's full suite passes, and the numeric rule
has a clear, testable meaning rather than a false-green exception.

#### A3. Make outputs and reproduction claims truthful

- Resolve `pvt_th.T_fluid_max` provenance before generating a reference run.
  If a traceable source supports the value, cite it. If not, label it as an
  assumption or leave it unset and blocked; do not present it as a safe limit.
- Update
  [model/validation.md](../CARNOT2026_AquaSolar/model/validation.md) and the
  package [README.md](../CARNOT2026_AquaSolar/README.md): either include
  verified `carnot-demo` results created inside the package, or explicitly
  say results are not bundled and provide the regeneration command.
- Test result generation from the clean package location, not the outer tree.
- Reconcile all test-suite claims with the clean-install result from A1.

**Acceptance:** every promised output exists at the named path, or the docs
unambiguously say it is generated on demand.

#### A4. Reconcile model scope, equations, and provenance

- Align the runnable PVT equations with the enforced configuration. State
  explicitly that `soiling.mode = none` means the soiling multiplier is one,
  and `iam_model = none` means no IAM correction is applied. Distinguish the
  current PVT calculation from broader proposed equations.
- Check that `T_fluid_max` has a source appropriate to its use as a solver
  bound. If not, keep the run blocked rather than inventing a citation.
- Re-run the canonical scenario with one fixed set of parameters, weather,
  seed, and environment. Reconcile the different electrical/thermal energy
  figures from the two trees; report the per-area yield and keep the
  fixed-inlet assumption's limitation visible.

**Acceptance:** active code, parameter provenance, equations, and reported
annual outputs describe the same run and assumptions.

#### A5. Correct metric and status interpretation

- In [REPORT.md](../CARNOT2026_AquaSolar/REPORT.md), say which metrics the
  runnable PVT path actually emits. The current report says the run provides
  `M-PV-01` and `M-TH-01`; identify other metric definitions as not yet
  populated by this run.
- Clarify in the status output or its heading that `confirmed` describes the
  parameter record/status and does not mean measured or calibrated. Surface
  `source_type` and `source_ref` next to values so assumptions cannot be
  mistaken for observations.
- Name the actual weather station/source in report text and match it to the
  metadata sidecar; avoid the ambiguous “representative Abu Dhabi profile”
  wording where the selected source is RAK airport TMYx or Abu Dhabi TM2.

**Acceptance:** a reviewer can distinguish measured/source data, literature
values, assumptions, and unpopulated metrics without inferring their status.

#### A6. Close the reproducibility and deployment gaps

- Decide whether the PVT runner should write a per-run manifest using the
  existing manifest helper in
  [integration/manifest.py](../CARNOT2026_AquaSolar/src/aquasolar/integration/manifest.py).
  If implemented, include the actual input hashes and run/configuration
  identity; test that the manifest is written with the results. Otherwise,
  remove “every run produces a manifest” claims from the outer
  [PROJECT_REPORT.md](../PROJECT_REPORT.md).
- Verify the public Render URL and its read-only behavior. If unavailable,
  remove the live-showcase claim and use the local WebUI command as the demo
  fallback.

**Acceptance:** each reproducibility/deployment claim has a working artifact
or is removed.

#### A7. Fix known internal defects

- Add the missing `math` import and a focused lognormal-path regression test
  in [monte_carlo.py](../CARNOT2026_AquaSolar/src/aquasolar/uncertainty/monte_carlo.py).
- Correct the `bottlen_water_comparison` spelling in
  [lcoe.py](../CARNOT2026_AquaSolar/src/aquasolar/economics/lcoe.py). Check
  for callers first; retain a compatibility alias if the misspelled function
  is an external API.
- Review silent exception fallbacks in
  [integrator.py](../CARNOT2026_AquaSolar/src/aquasolar/integrator.py).
  Surface failures or log them; otherwise keep the full-system path out of
  the demo and clearly label it as not runnable/validated.

**Acceptance:** the lognormal path is exercised, the public function name is
unambiguous, and failures cannot silently look successful.

#### A8. Repair package documentation and archive hygiene

- Add or restore the missing `DATA_ENTRY_GUIDE.md`, or update links in the
  READMEs and
  [PROJECT_REPORT.md](../PROJECT_REPORT.md) to documents that are included.
- Mark the outer report as superseded if the package
  [REPORT.md](../CARNOT2026_AquaSolar/REPORT.md) is authoritative. Link
  [DISCLOSURE.md](../CARNOT2026_AquaSolar/DISCLOSURE.md) directly instead of
  saying disclosure “should” happen.
- Decide whether empty `docs/change_requests/` and `docs/model_specs/`
  directories are needed; populate intentionally or omit from the archive.
- Build the submission archive from an explicit include list. Exclude
  `.tmp_tools/`, caches, virtual environments, and `__pycache__`; inspect the
  archive contents rather than deleting workspace files.
- Consider moving test-only dependencies such as pytest out of core
  dependencies and cite the existing lock file as the environment reference.

**Acceptance:** links resolve in the distributed package, one report is
authoritative, and the archive contains only intended deliverables.

### Phase B — Redesign the WebUI around the user's input workflow

This phase applies to the canonical WebUI. The current design critique is
about the outer tree's seven-screen interface; first complete decision 2
above. Use the existing AquaSolar colors, typography, focus treatment, and
honesty badges. Do not replace them with a generic dashboard or hide important
provenance behind decorative cards.

#### B1. Establish a product-specific information hierarchy

Before changing layout, map the current API fields to the user's tasks:

1. Choose and understand the weather/data file.
2. Inspect required parameters and their provenance.
3. See validation findings in the context of the affected file/input.
4. Understand which calculations the runnable model performs and what it
   excludes.
5. Resolve blockers and run the supported scenario.

Define a compact visual vocabulary and apply it consistently:

- **Weather/data source** — values read from the selected CSV and its
  metadata.
- **Configured parameter** — a scalar entered in the parameter files.
- **Assumption/demo value** — an explicitly labelled assumed/default value.
- **Derived result** — computed by the model, not an input.
- **Missing/invalid** — no value or a validation error, with a direct action.

Use the existing metadata (`data_origin`, `source_type`, `source_ref`, status,
units, and required flags) as evidence. Never infer that a value is measured
when the metadata does not say so.

**Acceptance:** a first-time user can identify a value's origin, unit,
assumption/measured status, and required/optional state without opening a
different tab or reading source code.

#### B2. Rework Parameters for legibility and provenance

- Replace the current hard-to-scan presentation with grouped, predictable
  sections: required-to-run parameters, optional/conditional parameters, and
  inactive or future-model parameters.
- Give each row a stable hierarchy: parameter name and plain-language purpose;
  value and unit; source/status badge; source reference; validation state.
- Make assumptions visually distinct from measured/source-derived values
  without relying on color alone. Provide text labels and accessible names.
- Add search and filters only where they help users answer concrete questions
  (for example, “required to run” or “assumptions”); avoid dense repeated
  labels and unexplained technical IDs.
- Preserve the ability to inspect the exact registered ID and provenance.

**Acceptance:** representative parameter rows can be interpreted without
guessing whether a number came from weather, configuration, or an assumption;
keyboard navigation and narrow-screen layout remain usable.

#### B3. Rework Data Files around source and readiness

- Organize weather/time-series and table files by their role in the simulation.
- Show filename, origin/station, interval and time zone, row count, required
  columns, metadata pairing, and compatibility state in a scannable summary.
- Provide an expandable detail view for columns, units, provenance, and sample
  rows instead of placing every field in a dense table by default.
- Clearly distinguish values actually read from the selected CSV from scalar
  parameters or values derived later by the model.
- Make actions discoverable: inspect, replace/add, and see why a file cannot
  be used. Keep filename uniqueness and CSV/metadata pairing requirements
  explicit.

**Acceptance:** a user can tell which file supplies each weather series and
whether it is compatible before starting a run.

#### B4. Put file validation findings beside the files they describe

- Show actionable errors and warnings inline under the affected Data File or
  column, grouped by severity, with a concise message and correction.
- Let users expand details for timestamps, gaps, missing fields, or metadata
  problems without navigating away from the file.
- Avoid duplicating the same finding in two competing lists. Keep an overall
  Validation view only for a compact project-wide summary and parameter/system
  issues; link each summary item to the affected file or parameter.
- Preserve validation-before-run blockers and make the next action explicit.

**Acceptance:** a data-file error is visible where the user selects or edits
that file, and the global summary links to it without hiding or duplicating
the diagnosis.

#### B5. Redesign the Model page to explain the actual execution path

- Replace the crowded presentation with a primary, left-to-right or
  top-to-bottom flow that matches implemented behavior:
  weather + site/parameters → input validation → solar geometry and
  transposition → PVT electrical/thermal calculation → reported hourly/annual
  outputs.
- Annotate each stage with its key inputs and outputs, units, and a short
  explanation. Show where the CSV contributes values and where parameter
  assumptions enter.
- Clearly separate “currently simulated” from “conceptual/future” elements.
  Tank dynamics, DHW, electrical bus, and water treatment must not appear as
  active stages unless implemented in the runnable path.
- Use progressive disclosure for equations and technical detail: one
  understandable overview first, with optional equation/assumption detail
  linked to the equation register.
- Keep the PVT-only / not-design-validated warning prominent.

**Acceptance:** a judge can explain the runnable simulation's inputs,
transformations, and outputs from the page without mistaking planned modules
for executed calculations.

### Phase C — Resolve UI defects and accessibility polish

If the Design Studio is included, apply these in order to the canonical version.
The audited outer implementation is in
[static/index.html](../src/aquasolar/static/index.html),
[static/app.js](../src/aquasolar/static/app.js), and
[static/app.css](../src/aquasolar/static/app.css).

#### C1. Remove the Design Studio's cold-load dead state

- Populate the weather selector before requesting screening; do not leave the
  default message above eight `—` cards while the first request waits.
- Show a truthful “running” state and skeleton/placeholder treatment during
  the request, then replace it with results or an explicit error/retry state.
- Reuse a successful cached result on tab return and prevent duplicate
  requests. Keep the existing screening limitation visible.

**Acceptance:** with a cold cache, opening the Studio immediately communicates
loading and reaches results/error predictably; no unexplained blank/dash state.

#### C2. Fix RO recovery percentage formatting

Remove the extra display scaling for `ro_recovery`; keep the percentage-to-
fraction conversion sent to the model. Test that slider value `50` displays
`50%` and the request receives `0.5`.

#### C3. Eliminate the page-load 404

Add a real or inline favicon and verify a cold WebUI load has no missing-icon
request or console error.

#### C4. Announce slider values with units

Set `aria-valuetext` from the same formatted value shown to the user whenever
a design control changes, including initial render. Verify the accessible
name, value, and unit for keyboard and assistive-technology use.

#### C5. Clarify navigation status/count badges

Separate decorative ordinals and badges from the accessible name. Hide purely
decorative text from assistive technology; expose an accurate, dynamically
updated count or status. Do not hard-code counts that can become stale.

#### C6. Improve meaningful small text

Raise the minimum size for meaningful navigation labels and sidebar text,
checking contrast, wrapping, and responsive layouts. Preserve the existing
visual identity rather than enlarging every decorative label indiscriminately.

#### C7. Add skip navigation and review landmarks

Add a keyboard-visible skip link to the single main content region. Check
focus order and landmark names; do not mass-rewrite valid `<header>` elements
merely to reduce their count.

#### C8. Make Ctrl-K search discoverable

Move or repeat the shortcut hint near the search field while preserving
keyboard operation and screen-reader access.

#### C9. Optimize large figures

Resize and convert the oversized overview/flow images to appropriately sized,
compressed formats. Compare the WebP or alternative output against the source
at presentation size, preserve descriptive alt text, and verify all assets
load after scrolling.

#### C10. Keep scope honesty visible

Decide whether the PVT-only/not-design-validated badge should persist across
all views. If so, place it consistently without crowding the page or obscuring
the specific view's primary action.

#### C11. Recheck all views and responsive states

After B1–B5 and C1–C10, cold-load and exercise every view at presentation and
narrow-screen sizes. Check loading, empty, error, success, and disabled
states; tab/keyboard focus; accessible names and values; console/network
errors; image loading; and overflow. Capture updated screenshots for the
implementation review.

**Do not regress:** the critique disproved reports of broken lazy images,
permanently empty KPIs, the Figure 1 white gap, stuck scenario loading, missing
focus indicators, and unlabeled sliders. Preserve the strong focus treatment,
real hardware photos, useful status messaging, and prominent scope disclosure.

## 3. Final release gates

Do not call the work complete until all applicable gates pass:

1. **Environment:** clean package install, no `PYTHONPATH` workaround, correct
   package-local paths.
2. **Tests:** canonical full suite passes; if the outer tree remains
   maintained, its full suite passes under the chosen R2 policy.
3. **Science and claims:** model equations, parameter provenance, metric
   claims, station identity, and output numbers agree with a single fresh run.
4. **UI:** Parameters, Data Files, Validation, and Model pages explain
   provenance, errors, and execution flow as specified; Design Studio gates
   apply only if that feature is included.
5. **Accessibility and performance:** keyboard, screen-reader values,
   responsive behavior, image load, and console/network checks pass.
6. **Package:** archive excludes `.tmp_tools/` and development caches; all
   internal documentation links resolve; included outputs are reproducible.
7. **Demo:** test the exact packaged build and local fallback before
   presenting. Warm expensive screens only as a last-mile fallback, not as a
   substitute for a clear loading state.

## 4. Strengths to preserve

Keep the project's provenance records, equation-to-code mapping, assumptions
register, validation-before-run behavior, overwrite protection, limitation
arrays, and existing focus styling. The redesign should make those strengths
easier to understand—not replace them with less transparent UI.
