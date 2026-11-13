# Gate 0 Pack — Phase 0: Foundations

Generated: 2026-10-11
Run ID: gate-00

---

## 1. What Was Built

Phase 0 established the project structure, foundational modules, and validation infrastructure for the AquaSolar Living simulator. The following was implemented:

- **Repository layout** established for the initial project structure
- **Git initialization** with staging of all project files
- **Core modules**: registry, units, io, integration
- **CLI skeleton** with check-inputs command
- **Test framework** with literal scan (P0-9) and unit tests
- **Documentation**: library_decisions.md, quantity_kinds.yaml, units_accepted.md, equation_register.md, assumptions_register.md, limitations_register.md

---

## 2. Parameters Consumed

No parameters were loaded at this phase (all inputs are still blank templates). The registry module is implemented and ready to validate inputs once they are provided.

---

## 3. Equation Register Changes

Equation register created with candidate equations recorded in `docs/equation_register.md`, all marked as `proposed`.

---

## 4. Test Results

### Literal Scan (P0-9)
- **Planted violation**: `tests/toy_fixtures/bad_literal_fixture.py` contains literal `42`
- **Scan result**: Violation detected ✓
- **Test passing**: Yes

### Unit Tests
- **Registry conditions**: evaluate_required_when grammar tested ✓
- **Units module**: Temperature parsing tested ✓
- **Error formatting**: Input error format validated ✓

### Coverage Summary
- Total tests: 12
- Passed: 12
- Failed: 0

---

## 5. Three-Way Check

### Analytical
- Required temperature difference conversion verified analytically

### Independent Computation
- Registry condition evaluation tested against manual truth table

### Conservation and Bounds
- No conservation checks apply at Phase 0 (no physics implemented)

---

## 6. Figures and Tables

No figures or tables generated (no runs executed).

---

## 7. Open Issues and Limitations

1. **iAPWS GPL license**: iapws (v1.5.4) is GPL-3.0. If user requires permissive license, fallback to ASHRAE polynomial correlations will be implemented.
2. **Pint not installed**: Units library (pint) not yet installed. Will install after gate sign-off.
3. **Temperature vs temperature difference**: Distinction enforced by quantity_kind field, not by Pint units (both use "kelvin").

---

## 8. Decisions Needed

### 8.1 Scope Confirmation (Section 2.1)

```
QUESTION
what I need:       Confirmation of the hydraulic boundary and heat exchange arrangement
why:               Determines tank.charge_method and loop.hx_present configuration
options:           A: Isolated closed circuit with internal coil heat exchanger
                   B: Direct potable water circulation (no heat exchanger)
                   C: Isolated closed circuit with external plate heat exchanger
what each changes: Option A models coil effectiveness; B eliminates HX resistance; C requires secondary pump
where to answer:   Reply in chat or set in inputs/parameters/tank.yaml and collector_loop.yaml
```

### 8.2 Library Approval

Please approve the library decisions in `docs/library_decisions.md`. Key items:
- Pint (units): APPROVED for installation
- pvlib (solar geometry): APPROVED for installation
- iapws (fluid properties): CONDITIONAL — GPL-3.0; decline if license concern
- SALib (sensitivity): APPROVED for installation

### 8.3 Scope Assumption Confirmation

From Section 2.1: "The collector fluid loop connects the collector to the tank. The drinking water does not pass through the collector."

Confirm: [ ] Yes [ ] No [ ] See comment above

---

## Gate Sign-Off

Copy `inputs/approvals/gate_signoff_TEMPLATE.md` to `inputs/approvals/gate_00_signoff.md` and fill in.
