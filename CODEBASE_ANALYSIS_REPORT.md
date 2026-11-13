# AquaSolar Living — Codebase Architecture & Math Model Report

**Date:** 2026-11-13
**Scope:** Full repository analysis of `C:\Users\arsh2\OneDrive - American University of Ras Al Khaimah\Fall2026\waterresearch\Simulation`

---

## 1. Architecture Overview
AquaSolar Living is a villa-scale PVT (photovoltaic-thermal) and potable-water assurance system simulator. The architecture is modular, with subsystems communicating via parameter dictionaries and shared state.

**Core Subsystems:**
- **`weather/`**: Irradiance (GHI, DNI, DHI) → Plane-of-array (POA) → Solar Geometry + IAM + Soiling → Effective Irradiance.
- **`pvt/`**: Coupled electro-thermal collector model.
- **`tank/`**: Multi-node stratified thermal storage.
- **`solar_loop/`**: Differential-controller + pumps + pipe losses.
- **`water_treatment/`**: Sequential treatment trains (Pathways A/B/C) with per-stage quality transformation.
- **`mnt/`**: Oracle-based decision engine for minimal necessary treatment.
- **`electrical/`**: Load balance, battery dispatch, grid interaction.

**Runnable Status:**
- **PVT-only**: Fully integrated and runnable end-to-end.
- **Tank, Loop, Water Treatment, Electrical**: Coded as modules, tested in isolation, but NOT integrated into the executable `simulate.py` driver yet. They are currently stubs in the simulator loop.

---

## 2. Math-Model Inventory

### EQ-PVT-01: Electrical Output
- **Form:** $P_{el} = \eta_{ref} \cdot [1 - \beta \cdot (T_c - T_{ref})] \cdot \phi_{soil} \cdot G_{eff} \cdot A \cdot f_{irr} \cdot f_{mpp}$
- **Inputs:** `T_c` (K), `G_{eff}` (W/m²), `eta_ref`, `T_ref`, `beta`, `phi_soil` (from soiling factor), `A` (m²), `f_irr`, `f_mpp`.
- **Outputs:** `P_{el}` (W).
- **File:** `src/aquasolar/pvt/electrical.py`

### EQ-PVT-02: Useful Heat (Steady-State)
- **Form:** $Q_u = A \cdot F_R \cdot [(\tau\alpha \cdot G_{eff} - P_{el}/A) - U_L \cdot (T_{f,in} - T_{amb})]$
- **Inputs:** `T_{f,in}`, `m_dot`, `G_{eff}`, `P_{el}`, `T_{amb}`, `A`, `tau_alpha`, `F_R`, `U_L`.
- **Outputs:** $Q_u$ (W).
- **File:** `src/aquasolar/pvt/thermal.py`

### EQ-TNK-01: Node Energy Balance
- **Form:** $\rho c_p V_i \frac{dT_i}{dt} = \dot{m}_{in}c_p(T_{in,i} - T_i) + Q_{in,i} - Q_{out,i} - Q_{loss,i} + Q_{cond,i}$
- **Inputs:** Node temperature/mass/volume state, inflow/outflow, conduction.
- **Outputs:** $T_i$ (K).
- **File:** `src/aquasolar/tank/step.py`

### Water Treatment (Sequential Trains)
- **Model:** $Q_{out, stage} = Q_{in, stage} \cdot \prod (1 - r_i)$ or $10^{-LR_i}$
- **Inputs:** Pathway parameters (turbidity, TSS, doc, ecoli, etc.).
- **Outputs:** Transformed quality dictionaries.
- **File:** `src/aquasolar/water_treatment/train.py`, `stages.py`

---

## 3. Input–Output Map

| Subsystem | Output variable | Unit | Consumed by |
| :--- | :--- | :--- | :--- |
| **Weather** | $G_{eff}$ | W/m² | `pvt/collector.py` |
| **PVT** | $P_{el}$, $Q_u$, $T_{f,out}$ | W, K | `solar_loop/`, `tank/` |
| **Solar Loop** | $T_{tank,in}$ | K | `tank/` |
| **Tank** | $T_{avg}$, $T_{top}$, $T_{bot}$ | K | `solar_loop/`, `reporting/` |

---

## 4. Registry-Key Reference
- **`pvt_el.*`**: Cell efficiency, ref temp, temp coeff.
- **`pvt_th.*`**: Collector area, $F_R$, $U_L$, cell-fluid resistance.
- **`loop.*`**: Pipe dimensions, R-values, pump curves.
- **`mnt.*`**: Treatment thresholds, pathway costs.
- **`electrical.*`**: Battery params, limits, dispatch strategies.

---

## 5. Runnable vs Stub Status
| Subsystem | Status | Gap |
| :--- | :--- | :--- |
| **PVT-only** | Fully Runnable | None |
| **Tank** | Coded/Tested | Not in simulator integration |
| **Solar Loop** | Coded/Tested | Not in simulator integration |
| **Electrical** | Coded/Tested | Not in simulator integration |
| **Economics** | Coded (standalone) | Not in UI/CLI output loop |
