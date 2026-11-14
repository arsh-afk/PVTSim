# AquaSolar Web Workbench — UI Critique

**Date:** 2026-11-14 · **Method:** live audit of `python -m aquasolar web-ui` in headless
Chromium (1280×720), all seven screens driven and screenshotted, DOM/ARIA/contrast/focus
probed programmatically. Screenshots in `reports/ui-*.png`.

**Bottom line:** this is a genuinely well-built UI — clearly a designer was involved.
Colour system, typographic hierarchy, information architecture, keyboard focus, and ARIA
landmarking are above the standard of most research code. The problems are few but two
are worth fixing before you demo, and one is a live-presentation hazard.

---

## Verified findings (checked, not assumed)

| # | Finding | Severity | Evidence |
|---|---|---|---|
| 1 | Design studio shows `—` in all 8 KPI cards for ~5 s while nothing tells the user it is working | 🔴 high | `reports/ui-design.png` vs `reports/ui-design-final.png` |
| 2 | "RO recovery **5,000 %**" — a 0.50 fraction rendered with a 100× unit error | 🔴 high | design-studio slider label |
| 3 | Console 404 on every page load | 🟡 medium | 1 `console.error` per load, no matching HTTP response |
| 4 | Sliders have a visible label but no `aria-valuetext`, so the announced value lacks units | 🟡 medium | sliders wrapped in `<label>` at `index.html:592` |
| 5 | Duplicate/stale text: nav badge reads `04 Validation 0`, `02 Parameters —` | 🟢 low | nav DOM |
| 6 | Two digits-heavy labels at 9px; 11px body text in the sidebar header | 🟢 low | computed styles |
| 7 | No skip link; 7 `<header>` elements; `main` count 1 ✓ | 🟢 low | landmark probe |

**Things I initially suspected and disproved — do not "fix" these:**

- ❌ *16 broken images.* All 21 `<img>` are `loading="lazy"`; `naturalWidth` is 0 until
  scrolled into view. After a scroll pass: **0 broken images, 0 failed requests.**
- ❌ *Empty KPI cards / screening broken.* The screening completes in ~5 s and the cards
  fill correctly (`—` count drops from 9 → **0**). Pure loading-state issue, not a data bug.
- ❌ *Blank gap in Figure 1.* The white margin is part of the source PNG, not a layout bug.
  Image is 3300×2258 rendered at 942×645 with `object-fit: contain`.
- ❌ *Scenarios stuck on "Loading saved scenarios…".* Loads fine; my probe fired too early.
- ❌ *No focus indicators.* Tab traversal shows a **3 px teal (`#70c4ae`) outline** on every
  focusable element. Excellent, and correctly `:focus-visible`-only.
- ❌ *16 unlabeled sliders.* Every slider is wrapped in a `<label>`
  (`<label class="design-slider"><span>RO recovery …</span><input type="range" …></label>`,
  `index.html:592`). My first probe only checked `aria-label`, and at the time of measurement
  the Design studio had not rendered, so the 16 ranges it counted were from other tabs' markup.
  The real gap is narrower — see item 4.

---

## 🔴 1. Design studio: silent ~5 s dead state

**What happens.** Click *07 Design studio*. Status bar reads "Adjust a control to see the
screening update." All eight KPI cards render `—`. The weather `<select>` is empty for the
first ~2 s, then populates, then the screening POST runs (~4.5 s, 8,760 intervals), then the
cards fill. Total to first number: **~5 s**.

**Why it matters.** A judge clicks the flashiest tab, sees a screen full of dashes and no
spinner, and concludes it is broken. In the earlier screenshot this looks like a dead
feature; seconds later it is the best screen in the app.

**Cause.** `runDesignScreening()` returns early when `#design-weather` is empty
(`app.js:2346`), and that select is populated asynchronously after the weather probe
finishes. Until then `#design-status` keeps its static HTML copy `"Adjust a control to see
the screening update."`, no request is made, and the KPI cards sit on their `—`
placeholders.

**Fix (pick one, ~15 min):**
- Call `runDesignScreening({ immediate: true })` once after defaults load, **and**
- set `#design-status` to `"Running the whole-system screening…"` while the request is in
  flight, plus a `skeleton` class on the KPI grid so cards aren't bare em dashes.
- Bonus: cache the last result so tab-switching re-renders instantly (you already keep
  `state.design`).

---

## 🔴 2. "RO recovery 5,000 %" — unit bug visible on screen

The Design studio slider is labelled **"RO recovery 5,000 %"** while its range is
`min=20 max=85 value=50`. The model value is a *fraction* (0.50) being formatted as a
percentage with a ×100 already applied, so 0.50 → `5,000 %`.

**Cause (confirmed in source).** `static/app.js:2262` declares
`ro_recovery: { unit: " %", digits: 0, scale: 100 }`, and `designOutputs()
(app.js:2279)` does `value = value * spec.scale`. The slider already carries a
percent value (`min=20 max=85 value=50`), so the display multiplies by 100 a second time.

**Fix:** delete `scale: 100` from the `ro_recovery` entry. One character-class change; the
`/ 100` conversion in `readDesignControls()` (`app.js:2295`) stays as is, because the model
does want a fraction.

---

## 🟡 3. Console 404 on every page load

Every single load logs one `console.error: Failed to load resource: 404`. Notably the
Playwright `requests failed` counter is **0** and my `response` listener recorded **no**
status ≥ 400 — so this is a sub-resource the page requests that the network log attributes
to a browser-internal fetch (typically `/favicon.ico`; the page declares a
`theme-color` but no icon link, and `performance` shows no icon entry).

**Fix:** add `<link rel="icon" href="/static/...">` with a real asset, or a
`data:image/svg+xml` inline favicon. Costs 2 lines and removes the only console error —
which matters because "no console errors" is exactly what judges check.

---

## 🟡 4. Sliders announce a bare number, with no unit

Each Design studio slider **does** have an accessible name (good — the wrapping `<label>`
plus the visible text gives *"RO recovery 50 %"*). What is missing is `aria-valuetext`:
screen readers announce the raw range value (`2`, `0.5`, `50`) rather than *"2 W/K"* or
*"50 %"*. Low visual impact, easy win, and it is the kind of detail that separates a polished
submission from a good one.

**Fix (one line per slider):**

```html
<input type="range" min="0.5" max="8" step="0.5" value="2"
       data-design-field="tank_heat_loss"
       aria-valuetext="2 W/K">
```

Better still, set it from `designOutputs()` in `app.js:2273` so it stays in sync:
`input.setAttribute('aria-valuetext', output.textContent)`.

---

## 🟢 Polish

- **Duplicate number rendering.** The nav button's accessible text is
  `"02 Parameters —"` / `"04 Validation 0"`, i.e. the ordinal and the count badge are both
  in the text node. Wrap the badge in a `<span aria-hidden="true">` and put the real count in
  the button's `aria-label` (`"Parameters, 37 items"`).
- **9 px and 10 px type.** `.nav-section-label` is 9 px (contrast is fine at **8.31 : 1** —
  I measured it; the colour is not the issue, the size is), and several micro-labels sit at
  10 px. Projector rooms are unkind. Bump the floor to 11 px for anything carrying meaning.
- **No skip link.** With 7 `<header>` and 2 `<nav>` landmarks, add
  `<a class="skip" href="#main">Skip to content</a>` — you already have exactly one `<main>`.
- **`Arrows`/`Ctrl K` discovery.** The search shortcut shows as a `<kbd>Ctrl K</kbd>` at
  10 px on the sidebar. Consider moving it into the search field as a placeholder hint so
  the shortcut is discovered rather than hunted.
- **Figure 1 is enormous in scroll cost.** 1.88 MB PNG at 3300×2258 for a 942-px render.
  Export at 2× (≈1900 px) and convert to WebP — cuts ~1.5 MB and speeds the Overview
  tab noticeably. Same for the two detailed-flow PNGs (~1.9 MB each).
- **`"PVT ONLY · EXPLORATORY"` badge** is excellent and should stay prominent — it is the
  single best honesty signal in the UI. Consider making it a persistent element in the
  header across *all* tabs rather than only the page once validations load.

---

## What is genuinely strong — say so in the demo

1. **Visual system.** Deep teal sidebar (`#102f37`) against warm off-white (`#f5f4ed`),
   with a mint accent (`#70c4ae`). Coherent, professional, and *not* a default framework
   look. It reads as a product, not a student project.
2. **Information architecture.** Seven numbered phases grouped under
   PREPARE / UNDERSTAND / ANALYZE / EXPLORE. A judge understands the whole model workflow
   from the sidebar alone — this is unusually good.
3. **The Overview page.** Hero → readiness checklist → "why this simulation was needed"
   with the problem statement → Figure 1 concept → timeline. That is a *pitch*, embedded in
   software. Most competition entries never get near this.
4. **Real validation hardware photos** (Fig 2 a–c, alt-texted) next to the simulated system.
   Enormous credibility signal — it says "we built this," not "we wrote this."
5. **Focus handling.** `:focus-visible`-only 3 px outline across buttons, links, inputs,
   selects, textareas, with `outline-offset: 2px`. Correct, consistent, and rare.
6. **Accessibility hygiene generally.** One `<main>`, `lang="en"`, `theme-color`,
   `width=device-width` viewport, 9 `aria-live` regions, `role="group"`/`role="tablist"`
   with labels on the custom unit toggles, and **alt text on all 21 images** — including
   genuinely descriptive text ("Team members assembling the three-module PVT array on a
   mobile test frame in the workshop").
7. **Honesty in the chrome.** "PVT ONLY · NOT DESIGN-VALIDATED", "Checking inputs…", and the
   screening footnote *"Trends are defensible; absolute values depend on the assumptions
   below"*. This matches the Carnot criteria directly.

---

## Demo-day checklist (30 min of work)

| Priority | Action | Time |
|---|---|---|
| 1 | Fix the `RO recovery` ×100 label bug | 10 min |
| 2 | Run screening on tab open + show "Running…" status and skeleton cards | 15 min |
| 3 | Add a favicon to silence the 404 | 2 min |
| 4 | **Warm the Design studio before you present** — open it, let it finish, then leave it | 1 min |
| 5 | Compress `aquasolar-system-process.png` (1.9 MB) and the two flow diagrams | 10 min |
| 6 | Set `aria-valuetext` from `designOutputs()` so sliders announce units | 10 min |

**Presentation tip:** load the app ~30 s before your slot and click through all seven tabs
once. Every expensive first-paint (lazy images, weather probe, screening) is then warm, and
nothing you show will be a dash.

*Screenshots: `reports/ui-overview.png`, `ui-parameters.png`, `ui-datafiles.png`,
`ui-validation.png`, `ui-model.png`, `ui-runs.png`, `ui-runs-loaded.png`, `ui-design.png`
(pre-screening), `ui-design-final.png` (loaded), `ui-overview-concept.png`.*
