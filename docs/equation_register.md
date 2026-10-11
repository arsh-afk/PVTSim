# Equation Register

This register tracks all equations used in the simulation.
Equations must be approved before implementation (R4).

## Format

Each entry has:
- `id`: Unique equation identifier (e.g., EQ-PVT-01)
- `name`: Human-readable name
- `form`: Plain-text mathematical form
- `variables`: List of variables with symbol, meaning, unit kind, and registry id
- `assumptions`: List of assumptions
- `validity_range`: The range of validity for each variable
- `reference`: Source (user-supplied or opened-and-read; else "citation needed")
- `variants`: Alternative accepted forms
- `status`: "proposed" or "approved"

---

## PVT Equations

### EQ-PVT-01: Electrical Output

- **ID**: EQ-PVT-01
- **Name**: PVT electrical output
- **Form**: `P_el = eta_ref * [1 - beta * (T_c - T_ref)] * phi_soil * G_eff * A * f_irr * f_mpp`
- **Variables**:
  - `eta_ref`: Reference electrical efficiency, unit_kind=fraction, registry_id=pvt_el.eta_ref
  - `beta`: Temperature coefficient, unit_kind=rate_per_temperature, registry_id=pvt_el.beta
  - `T_c`: Cell temperature, unit_kind=temperature, registry_id=pvt_el.T_ref (reference)
  - `phi_soil`: Soiling factor, unit_kind=fraction, registry_id=soiling factors
  - `G_eff`: Effective plane-of-array irradiance, unit_kind=irradiance
  - `A`: Collector area, unit_kind=area, registry_id=pvt_th.collector_area
  - `f_irr`: Irradiance correction factor, from pvt_el.irradiance_model
  - `f_mpp`: MPP tracking factor, from pvt_el.mpp_assumption
- **Assumptions**:
  - Cell temperature is uniform across collector
  - MPP tracking is ideal unless otherwise specified
- **Validity Range**: ASK_USER
- **Reference**: citation needed
- **Variants**:
  - Efficiency referenced to G_ref
  - Irradiance-dependent efficiency curve
- **Status**: proposed

### EQ-PVT-02: Useful Heat (Steady-State)

- **ID**: EQ-PVT-02
- **Name**: PVT useful thermal energy
- **Form**: `Q_u = A * F_R * [S - U_L * (T_f_in - T_a)]` where `S = tau_alpha * G_eff - P_el / A`
- **Variables**:
  - `A`: Collector area, unit_kind=area, registry_id=pvt_th.collector_area
  - `F_R`: Heat-removal factor, unit_kind=fraction, registry_id=pvt_th.F_R
  - `U_L`: Overall heat-loss coefficient, unit_kind=heat_transfer_coefficient, registry_id=pvt_th.U_L
  - `tau_alpha`: Transmittance-absorptance product, unit_kind=fraction, registry_id=pvt_th.tau_alpha
  - `T_f_in`: Fluid inlet temperature, unit_kind=temperature
  - `T_a`: Ambient temperature, unit_kind=temperature
- **Assumptions**:
  - Steady-state conditions
  - Uniform fluid temperature distribution
- **Validity Range**: ASK_USER
- **Reference**: citation needed
- **Variants**:
  - Quasi-dynamic form with thermal capacitance (pvt_th.thermal_capacitance)
  - Wind-dependent U_L
- **Status**: proposed

### EQ-PVT-03: Cell Temperature

- **ID**: EQ-PVT-03
- **Name**: Cell temperature from fluid temperature
- **Form**: `T_c = T_f_m + R_cf * q_cf` where `T_f_m = (T_f_in + T_f_out) / 2`
- **Variables**:
  - `T_f_m`: Mean fluid temperature, unit_kind=temperature
  - `R_cf`: Cell-to-fluid thermal resistance per area, unit_kind=area_thermal_resistance, registry_id=pvt_th.R_cell_fluid
  - `q_cf`: Heat flux from cell to fluid per area, unit_kind=power/area
- **Assumptions**:
  - Linear thermal resistance between cell and fluid
  - q_cf is derived from energy balance (to be specified)
- **Validity Range**: ASK_USER
- **Reference**: citation needed
- **Variants**: None currently
- **Status**: proposed

### EQ-PVT-04: Fluid Outlet Temperature

- **ID**: EQ-PVT-04
- **Name**: Fluid outlet temperature
- **Form**: `T_f_out = T_f_in + Q_u / (m_dot * cp_f)` for `m_dot > 0`
- **Variables**:
  - `m_dot`: Mass flow rate, unit_kind=flow_mass
  - `cp_f`: Fluid specific heat, unit_kind=specific_heat, registry_id=loop.fluid_cp
- **Assumptions**:
  - Constant fluid properties over temperature range
- **Validity Range**: ASK_USER
- **Reference**: citation needed
- **Status**: proposed

### EQ-PVT-05: PV-Only Cell Temperature

- **ID**: EQ-PVT-05
- **Name**: PV-only reference cell temperature
- **Form**: ASK_USER - user must supply form or measured series
- **Status**: proposed

---

## Loop Equations

### EQ-LP-01: Pump Control

- **ID**: EQ-LP-01
- **Name**: Collector loop pump control
- **Form**: Pump turns on when `T_coll_sensor - T_tank_sensor > loop.ctrl_dT_on`, turns off when `< loop.ctrl_dT_off` or `tank.temp > loop.ctrl_T_tank_max`, respects dwell and optional irradiance condition
- **Status**: proposed

### EQ-LP-02: Pump Power

- **ID**: EQ-LP-02
- **Name**: Pump electrical power
- **Form**: ASK_USER - depends on loop.pump_power_model
- **Status**: proposed

### EQ-LP-03: Pipe Loss

- **ID**: EQ-LP-03
- **Name**: Pipe heat loss
- **Form**: `Q_pipe = UA_pipe * (T_f_mean_pipe - T_amb_pipe)`
- **Status**: proposed

---

## Tank Equations

### EQ-TNK-01: Node Energy Balance

- **ID**: EQ-TNK-01
- **Name**: Tank node energy balance
- **Form**: `rho * cp * V_i * dT_i/dt = Q_charge_i + Q_adv_i + Q_cond_i - Q_loss_i + Q_aux_i`
- **Status**: proposed

### EQ-TNK-02: Advection

- **ID**: EQ-TNK-02
- **Name**: Advective transport between nodes
- **Form**: Upwind transport from net flow through interfaces
- **Status**: proposed

### EQ-TNK-03: Conduction

- **ID**: EQ-TNK-03
- **Name**: Axial conduction
- **Form**: `Q_cond_i = (k_eff * A_x / dz) * (T_{i+1} - 2*T_i + T_{i-1})`
- **Status**: proposed

### EQ-TNK-04: Standby Loss

- **ID**: EQ-TNK-04
- **Name**: Standby heat loss
- **Form**: `Q_loss_i = UA_i * (T_i - T_amb)`
- **Status**: proposed

### EQ-TNK-05: Inversion Mixing

- **ID**: EQ-TNK-05
- **Name**: Buoyancy inversion mixing
- **Form**: Volume-weighted mean for unstable node pairs
- **Status**: proposed

### EQ-TNK-06: Coil/Exchanger Charging

- **ID**: EQ-TNK-06
- **Name**: Heat exchanger charging
- **Form**: `Q_charge = eps * C_min * (T_loop_in - T_node)`
- **Status**: proposed

### EQ-TNK-07: Backup Heater

- **ID**: EQ-TNK-07
- **Name**: Backup heater operation
- **Form**: Thermostat control at aux_node
- **Status**: proposed

### EQ-TNK-08: Delivered Temperature

- **ID**: EQ-TNK-08
- **Name**: Delivered temperature and unmet demand
- **Form**: Check against delivery_temp_min
- **Status**: proposed

---

## Water Equations

### EQ-WTR-01: Flow and Solute Balance

- **ID**: EQ-WTR-01
- **Name**: Water mass and solute balance per stage
- **Form**: `m_feed = m_prod + m_rej` and `m_feed * c_feed = m_prod * c_prod + m_rej * c_rej`
- **Status**: proposed

### EQ-WTR-02: Recovery and Rejection

- **ID**: EQ-WTR-02
- **Name**: Recovery and rejection fractions
- **Form**: `recovery = V_prod / V_feed`; `R_k = 1 - c_prod / c_feed`
- **Status**: proposed

### EQ-WTR-03: Hydraulic Power

- **ID**: EQ-WTR-03
- **Name**: Hydraulic power for pumps
- **Form**: `P_hyd = Q_feed * dp / eta_pump`
- **Status**: proposed

### EQ-WTR-04: Specific Energy

- **ID**: EQ-WTR-04
- **Name**: Specific energy consumption
- **Form**: `E_spec = E_electric / V_prod`
- **Status**: proposed

### EQ-WTR-05: Membrane Flux

- **ID**: EQ-WTR-05
- **Name**: Membrane flux model
- **Form**: ASK_USER - depends on tc.membrane.flux_model
- **Status**: proposed

### EQ-WTR-06: Consumable Loading

- **ID**: EQ-WTR-06
- **Name**: Consumable loading and replacement
- **Form**: ASK_USER - depends on replacement_rule basis
- **Status**: proposed

### EQ-WTR-07: UV Operation

- **ID**: EQ-WTR-07
- **Name**: UV disinfection and dose
- **Form**: ASK_USER - depends on tc.uv.* parameters
- **Status**: proposed

### EQ-WTR-08: Remineralization

- **ID**: EQ-WTR-08
- **Name**: Remineralization stage
- **Form**: Adds species per treatment_removal with removal_basis=added_concentration
- **Status**: proposed

---

## Storage Quality Equations

### EQ-SQ-01: Storage Quality Decay

- **ID**: EQ-SQ-01
- **Name**: Disinfectant decay in storage
- **Form**: `V_s * dC/dt = Q_in * C_in - Q_out * C - k(T) * V_s * C`
- **Status**: proposed

---

## MNT Equations

### EQ-MNT-01: Oracle Selection

- **ID**: EQ-MNT-01
- **Name**: Minimum Necessary Treatment oracle
- **Form**: Minimize J(p,x_t) subject to quality constraints
- **Status**: proposed

### EQ-MNT-02: Controller

- **ID**: EQ-MNT-02
- **Name**: Sensor-based controller
- **Form**: Rules from controller_rules.csv with hysteresis
- **Status**: proposed

---

## Electrical Equations

### EQ-ELC-01: Power Balance

- **ID**: EQ-ELC-01
- **Name**: Electrical power balance
- **Form**: `P_net = P_el_ac - P_treat - P_pump - P_ctrl - P_sensors - P_comms - P_inv_standby`
- **Status**: proposed

### EQ-ELC-02: Battery

- **ID**: EQ-ELC-02
- **Name**: Battery state of charge
- **Form**: Update with round-trip efficiency and limits
- **Status**: proposed

---

## Economics Equations

### EQ-ECO-01: Net Present Value

- **ID**: EQ-ECO-01
- **Name**: Net present value calculation
- **Form**: `NPV = sum over t of CF_t / (1 + r)^t`
- **Status**: proposed

### EQ-ECO-02: Cost Metrics

- **ID**: EQ-ECO-02
- **Name**: Cost per litre, payback, lifecycle cost
- **Form**: ASK_USER - see metric_definitions.md
- **Status**: proposed

---

## Other Equations

### EQ-RES-01: Resampling

- **ID**: EQ-RES-01
- **Name**: Input resampling to time_step
- **Form**: ASK_USER - user chooses interpolation method
- **Status**: proposed

### EQ-ANN-01: Annualization

- **ID**: EQ-ANN-01
- **Name**: Economic annualization
- **Form**: ASK_USER - required if simulated period is not whole years
- **Status**: proposed

---

## Instructions

To approve an equation:
1. User reviews the proposed form
2. User provides reference (citation or measurement)
3. User marks status as "approved" in this file
4. Equation can then be implemented in code
