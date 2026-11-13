# AquaSolar Living --- TRNSYS Verification and Python Simulation Master Direction

**Purpose:** Give an agentic AI a controlled, auditable specification
for inspecting existing TRNSYS projects and the current AquaSolar Python
model, then determining what is reusable, what must change, what is
missing, and how to validate the coupled simulation.

**Source documents** 1. Khanmohammdi, Musharavati & Sheykhmohammadi,
*Energy and exergy examinations of a PVT based hybrid system for power,
heating and potable water production: Transient modeling*, *Renewable
Energy* 195 (2022), 540--553, DOI: 10.1016/j.renene.2022.05.114.
Referred to below as **Reference Paper**. 2. *AquaSolar Living: Smart
PVT-Integrated Water Assurance and Domestic Hot-Water Cogeneration for
Sustainable Villa Communities*, Final Report. Referred to below as
**AquaSolar Report**.

**Critical instruction:** The Reference Paper is the source for the
original TRNSYS/EES system structure and its component-equation lineage.
The AquaSolar Report is the source for the intended AquaSolar
architecture, operating strategy, and prototype design basis. Do not
copy the reference system's numerical parameters or its
seawater/brine-disposal assumptions into AquaSolar without explicit
justification. Do not claim that a component exists in an existing
TRNSYS deck until the deck has been inspected.

------------------------------------------------------------------------

## 1. Mission and expected outputs

The agent must inspect all supplied TRNSYS project files (for example
`.tpf`, `.dck`, `.dat`, `.tmf`, component source, external EES files,
weather files, plot/configuration files), the current Python repository,
and both source documents. It must produce:

1.  **Project inventory:** files, TRNSYS version, executable model entry
    point, linked external models, weather/demand data, and how to run
    the project.
2.  **TRNSYS component map:** every component instance, Type number,
    label, inputs, outputs, parameters, and its role in the system.
3.  **Variable lineage map:** every important Python variable and TRNSYS
    variable mapped to a physical quantity, unit, source, equation, and
    downstream consumers.
4.  **Process-flow and signal-flow diagrams:** thermal, electrical,
    water, control, and data/monitoring paths.
5.  **Equation traceability matrix:** Reference Paper equation →
    AquaSolar adaptation → Python implementation location → TRNSYS
    implementation location → validation test.
6.  **Difference register:** reference design versus AquaSolar design
    versus existing code/deck; mark each item `MATCH`, `ADAPTED`,
    `MISSING`, `CONFLICT`, `UNKNOWN`, or `NOT APPLICABLE`.
7.  **Balance and validation report:** timestep/unit tests, mass and
    energy residuals, annual KPIs, sensitivity tests, and unresolved
    discrepancies.
8.  **Implementation plan:** prioritized fixes, file/function names,
    acceptance tests, and any assumptions that require human approval.

Never silently alter a model while performing an audit. First document
the baseline, preserve copies, and make proposed changes in a separate
branch or version.

------------------------------------------------------------------------

## 2. Evidence hierarchy and source boundaries

Use this hierarchy when resolving model decisions:

1.  **AquaSolar Report** for AquaSolar design intent and supervisory
    control.
2.  **Reference Paper** for original PVT/tank/RO equation lineage and
    original TRNSYS topology.
3.  **Actual existing TRNSYS deck and Python source** for what has truly
    been implemented.
4.  **Measured prototype data and component datasheets** for calibration
    and physical parameters.
5.  **Explicitly labelled engineering assumptions** only when the
    sources do not specify a required detail.

A source document's statement that a model was planned, simulated, or
intended is not evidence that a TRNSYS deck or Python implementation
already contains it. The AquaSolar report describes a pre-TRNSYS Python
screening model and a planned TRNSYS 18 implementation/calibration
stage. Verify actual project files and model execution before reporting
implementation status.

When evidence conflicts, preserve both values and record the conflict.
Do not choose whichever value makes annual results look closer to the
report.

------------------------------------------------------------------------

## 3. System boundary and design basis

### 3.1 Reference Paper system --- retain as a separate baseline

The Reference Paper models PVT electricity and useful heat, a stratified
hot-water tank, circulation pump, valves and hysteresis controllers,
inverter, and a single-stage RO desalination unit. Its illustrated
control directs PVT electricity to building electrical demand and the RO
unit; surplus electricity may be sold/exported. The paper uses a 45,000
ppm saline feed, 250 ppm product-water target, 15% RO recovery, 80%
high-pressure-pump efficiency, and a 300 L storage tank. Its reported
PVT basis is five panels × 4 m² = 20 m², reference electrical efficiency
12%, reference temperature 20 °C, temperature coefficient 0.004 K⁻¹, and
circulation flow 200 kg/h. The paper's weather cases are Doha,
Stockholm, and Tehran.

These values describe the reference model and **must not be treated as
AquaSolar inputs**.

### 3.2 AquaSolar Living design basis --- default target model

  -------------------------------------------------------------------------
  Subsystem               Reported design basis   Notes for audit
  ----------------------- ----------------------- -------------------------
  Location/weather        Ras Al Khaimah, UAE;    Report says synthetic
                          25.79° N, 55.94° E;     screening weather scaled
                          fixed 25° south-facing  to monthly GHI; Stage 2
                          tilt                    intends a Meteonorm TMY.
                                                  Identify which file is
                                                  actually used.

  PVT                     6 m², three unglazed    Report's prototype basis;
                          modules, approximately  verify nameplate and
                          1.2 kWp                 measured curves.

  Solar resource          GHI 2,161 kWh/m²·yr;    Report values, not a
                          plane-of-array 2,286    replacement for checking
                          kWh/m²·yr               the weather file.

  PVT thermal model       Type 560 equivalent; η₀ η₀ and a₁ are collector
                          = 0.50; a₁ = 12 W/m²K;  thermal parameters.
                          40 kg/h                 Confirm exact
                                                  equation/implementation
                                                  and units.

  PV model                ηref = 20%; β =         The report describes a
                          0.37%/K; derate fd =    cell-temperature model;
                          0.92; kc = 0.012; knf = do not assume these
                          0.034                   coefficients have the
                                                  same mathematical
                                                  definition as the
                                                  Reference Paper's simple
                                                  efficiency equation.

  Circulation loop        40 kg/h; 4/1 K pump     The reference paper uses
                          hysteresis; 4--9 W; 85  a different hysteresis
                          °C cut-out              definition. Implement the
                                                  AquaSolar thresholds as
                                                  specified and test the
                                                  deadband.

  Hot-water tank          150 L, six nodes; U =   Report also says 200
                          0.7 W/m²K; DC element   L/day at 45 °C, and an
                          1.2 kW; AC element 2.0  upper-node
                          kW                      tempering/delivery
                                                  strategy.

  Electrical bus          48 V DC; MPPT 98%; 1 kW Keep DC-side and AC-side
                          inverter at 96%         energy separate.

  Battery                 Optional LFP 2.5 kWh;   Control preserves 35% SOC
                          SOC 10--95%; 92%        for water-assurance loads
                          round-trip efficiency   in comfort top-up logic.
                                                  Model charge/discharge
                                                  efficiencies explicitly.

  RO                      75 GPD TFC; 6 bar; 50%  Verify whether 6 bar and
                          recovery; booster       0.22 efficiency represent
                          efficiency ηbp = 0.22;  the intended hardware;
                          fouling factor FF =     use component
                          0.9; feed TDS 250 mg/L; datasheet/measurements
                          target 25 L/day         where available.

  Product-water train     sediment + carbon; RO;  Include auxiliary energy
                          remineralisation        and quality interlocks.
                          approximately +60 mg/L  Water is not declared
                          Ca/Mg; 30 L product     potable by simulation
                          tank; UV-LED            alone.

  Concentrate reuse       40 L buffer; reuse for  "Zero reject" is a target
                          toilet flushing;        requiring explicit
                          flushing demand 112.5   storage and overflow
                          L/day; municipal        accounting, not a
                          top-up; overflow        hard-coded result.
                          counted as reject       

  Time resolution         10-minute step, 8,760   Use sub-stepping or
                          h/year                  stable numerical
                                                  integration for the
                                                  six-node tank if
                                                  required.

  Demand                  200 L/day hot water at  Apply time profiles where
                          45 °C; 25 L/day         available, not just
                          drinking water target   uniform daily totals.
  -------------------------------------------------------------------------

**Weather caution:** the report lists synthetic weather for the Python
screening model and a Meteonorm TMY for the planned TRNSYS stage.
Results from these two weather bases are not directly comparable without
a matched-weather rerun.

------------------------------------------------------------------------

## 4. Required physical process diagrams

Create diagrams in the audit output and compare them with the actual
deck. Use the following as the target conceptual flow, not as proof that
a project file already implements it.

### 4.1 Thermal flow

``` text
Weather: GHI/DHI/DNI, ambient temperature, wind
                  |
                  v
       Plane-of-array irradiance
                  |
                  v
         Unglazed PVT collector <----- circulation pump / return water
           |                 |
           | DC electricity  | useful heat
           v                 v
     MPPT / 48 V bus     150 L six-node stratified tank
                              |        ^
                  hot draw ---+        | DC/AC auxiliary heater
                              v        |
                    tempering/mixing valve
                              |
                       45 °C hot-water load
```

The hydraulic direction and node connections must be confirmed against
the actual TRNSYS deck. The Reference Paper describes cold water
entering the PVT, heated outlet entering the upper tank node, tank draw
from the upper node, and make-up entering the lower node; its tank node
convention may differ from the AquaSolar implementation.

### 4.2 Electrical flow

``` text
PVT DC generation -> MPPT -> 48 V DC bus
                           |
                           +-> critical controls, pumps, RO, UV
                           +-> DC tank element (only under control conditions)
                           +-> battery charge (up to SOC ceiling)
                           +-> remaining electricity to inverter -> villa loads/export
Battery -> DC bus for allowed loads / comfort heating above reserve
Grid -> AC backup heater / allowed auxiliary supply
```

Define one consistent power-allocation order in code and tests. The
report's supervisory logic is authoritative for AquaSolar; do not use
the Reference Paper's three-case RO controller as a substitute.

### 4.3 Drinking-water flow

``` text
Municipal/villa tank
  -> inlet sensors (TDS, pH, turbidity, temperature, pressure, flow)
  -> sediment filter
  -> carbon-block filter
  -> boosted RO membrane
       |                         |
       | permeate                | concentrate
       v                         v
  remineralisation           40 L brine/concentrate buffer
       |                         |
  30 L product tank              +-> toilet cistern flushing
       |                         +-> municipal top-up when needed
  UV-LED at tap                  +-> overflow measured as reject
       |
  outlet quality sensors
       |
  release to tap only when quality/interlocks pass;
  otherwise divert/hold safely, never label unsafe water as potable
```

The report says out-of-specification water is diverted away from the
drinking-water outlet. Implement a fail-safe destination and volume
accounting rather than deleting failed water from the balance.

### 4.4 Control/data flow

``` text
Sensors + weather + demand forecasts
                |
                v
     Safety interlocks (Level 1)
                |
                v
   Deterministic supervisory dispatch (Level 2)
                |
                v
       pumps / RO / heaters / battery / valves
                |
                v
   logged state, power, temperature, water quality
                |
                v
 AI forecasts / fault detection / maintenance (Level 3)
                |
                v
       recommendations only unless validated
```

The safety layer must work without cloud or AI availability. The AI
layer must not override a safety interlock.

------------------------------------------------------------------------

## 5. Equation library and implementation rules

Use SI units internally: seconds, metres, kilograms, kelvin or degrees
Celsius (never mix temperature differences and absolute temperatures),
watts, joules, cubic metres, and consistent concentration units. Convert
to kWh only for reporting. Every equation must state assumptions, valid
range, unit convention, and numerical safeguards.

### 5.1 Conservation balances

For each component and each timestep:

**Mass balance** \[ `\sum `{=tex}`\dot `{=tex}m\_{in} -
`\sum `{=tex}`\dot `{=tex}m\_{out} = `\frac{dM}{dt}`{=tex} \]

At steady component flow, accumulation is zero. For storage tanks, it is
generally not zero.

**First-law balance** \[
`\dot `{=tex}Q-`\dot `{=tex}W+`\sum `{=tex}`\dot `{=tex}m\_{in}h\_{in}-`\sum `{=tex}`\dot `{=tex}m\_{out}h\_{out}
=`\frac{dE_{stored}}{dt}`{=tex} \]

Use a clearly documented sign convention. The Reference Paper gives the
steady-flow form with heat/work and stream enthalpy terms; the AquaSolar
model must include transient storage terms where relevant.

**Energy residuals:** log the per-step and annual residual for tank,
battery, DC bus, RO water streams, product tank, and concentrate buffer.
Never use a balancing "miscellaneous" term to conceal a missing
component.

### 5.2 PVT thermal model

The Reference Paper's absorber balance is expressed as:

\[ `\dot `{=tex}Q\_{absorbed} =
`\dot `{=tex}Q\_{loss,top,conv}+`\dot `{=tex}Q\_{loss,top,rad}
+`\dot `{=tex}Q\_{loss,back}+`\dot `{=tex}Q_u \]

\[ `\dot `{=tex}Q\_{loss,top,conv}=h_c A(T\_{PVT}-T\_{amb}) \]

\[ `\dot `{=tex}Q\_{loss,top,rad}=h_r A(T\_{PVT}^{4}-T\_{sky}^{4}) \]

\[ `\dot `{=tex}Q\_{loss,back}=`\frac{A(T_{abs}-T_{inside})}{R_B}`{=tex}
\]

\[ `\dot `{=tex}Q_u=`\dot `{=tex}m c_p(T\_{out}-T\_{in}) \]

\[
`\dot `{=tex}Q\_{absorbed}=GA(`\tau`{=tex}`\alpha`{=tex})(1-`\eta`{=tex}\_{PV})
\]

The source PDF's typesetting may render symbols imperfectly. Confirm
each term and definition from the original article equation and any
existing implementation before copying it verbatim. The AquaSolar Report
instead describes a Type-560-equivalent unglazed collector using a
zero-loss efficiency and a first-order heat-loss coefficient. Do not
combine these two thermal formulations into one equation unless the
chosen collector model explicitly requires it.

A common first-order collector representation is:

\[
`\dot `{=tex}Q_u=A`\left[\eta_0 G_{POA}-a_1(T_{fm}-T_a)\right]`{=tex}\]

where (T\_{fm}) is mean fluid temperature. Use this only if it matches
the selected Type 560 parameterization and the project's definition of
η₀ and a₁. Apply a physically justified nonnegative useful-gain clamp
only if consistent with the selected TRNSYS model; record any clamp.

**PV electricity:** the Reference Paper uses a simple relation
(`\dot `{=tex}W\_{PVT}=GA(`\tau`{=tex}`\alpha`{=tex})`\eta`{=tex}\_{PV}).
AquaSolar requires a temperature-dependent electrical model with its own
reference efficiency, temperature coefficient, derate and
cell-temperature relation. The agent must locate the exact implemented
formula in Python and compare it with the report. Do not assume the
paper's 12% reference efficiency applies to AquaSolar's 20%.

At every timestep log (G\_{POA}), ambient temperature,
inlet/outlet/mean-fluid temperature, cell temperature, pump state,
useful heat, gross DC generation, losses/derate, and net DC generation.

### 5.3 Six-node stratified tank

The Reference Paper gives a transient node balance of the form:

\[ m_i c_p`\frac{dT_i}{dt}`{=tex} = a_i`\dot `{=tex}m_h c_p(T_h-T_i)
+b_i`\dot `{=tex}m_L c_p(T_L-T_i) +UA_i(T\_{env}-T_i)
+`\text{inter-node mixing/conduction}`{=tex} +`\dot `{=tex}Q_i \]

Its printed equation includes terms involving neighbouring nodes and
control coefficients (a_i,b_i,g_i). Confirm the exact signs and node
indexing against the article and the TRNSYS Type 4c deck. Do not simply
copy a possibly garbled extracted equation.

For each node (i), the Python model should explicitly account for: -
node thermal capacitance (M_i c_p); - collector inlet/return flow
entering the selected node; - hot-water draw and cold make-up at their
assigned nodes; - inter-node conduction/mixing; - ambient loss
(UA_i(T\_{amb}-T_i)); - heater power assigned to that node; - any
numerical re-stratification or inversion correction, if used.

The report says the collector return is at the top, make-up at the
bottom, losses are included, and there are two heating elements. Verify
this unusual/important collector-return description against the intended
hydraulic diagram before implementation. Document node 1 versus node 6
orientation; never assume node 1 is top without checking.

The Reference Paper also gives: \[
`\dot `{=tex}Q_h=`\dot `{=tex}m_hc_p(T_h-T_6),`\qquad`{=tex}
`\dot `{=tex}Q_L=`\dot `{=tex}m_Lc_p(T_1-T_L) \] with the article's node
convention. These equations are convention-dependent; map (T_1,T_6) to
the actual top/bottom in the chosen implementation.

### 5.4 Tempering valve / hot-water delivery

The Reference Paper controls a mixing/flow valve to maintain
approximately 45 °C delivery. For ideal mixing of hot and cold water:

\[ `\dot `{=tex}m_h T_h+`\dot `{=tex}m_c
T_c=(`\dot `{=tex}m_h+`\dot `{=tex}m_c)T\_{del} \]

\[ `\frac{\dot m_h}{\dot m_h+\dot m_c}`{=tex}
=`\frac{T_{del}-T_c}{T_h-T_c}`{=tex} \]

Clamp the hot fraction to \[0,1\] and handle (T_h `\le `{=tex}T\_{del})
safely. This algebra is an ideal-mixing representation; the actual valve
and flow control must be checked against the TRNSYS Type 11b/11f
mapping.

### 5.5 RO model --- Reference Paper equation lineage

The Reference Paper formulates a single-stage RO unit using Nafey/Sharaf
solution-diffusion relations and a FilmTec temperature correction. Its
main sequence includes:

1.  Feed flow from permeate target and recovery: \[
    `\dot `{=tex}M_f=`\frac{\dot M_d}{RR}`{=tex} \]
2.  Salt balance / product concentration from feed concentration and
    salt rejection/desorption relation. Confirm the article's exact Eq.
    17 before implementation.
3.  Temperature correction factor (article Eq. 20): \[
    TCF=`\exp`{=tex}`\left[2700\left(\frac{1}{298}-\frac{1}{273+t}\right)\right]`{=tex}\]
4.  Water permeability (article Eq. 21): \[
    k_w=`\frac{6.84\times10^{-8}\,[18.6865-(0.177X_b)]}{t+273}`{=tex} \]
5.  Salt permeability (article Eq. 22): use the article's exact
    expression with (FF), (TCF), and its temperature term. The PDF text
    extraction can corrupt superscripts/brackets; retrieve from the
    original equation image or a reliable source before implementing.
6.  Osmotic pressure (article Eqs. 23--25): \[
    P_f=75.84X_f,`\quad `{=tex}P_b=75.84X_b,`\quad `{=tex}P_d=75.84X_d
    \]
7.  Average osmotic pressure and net osmotic pressure (Eqs. 26--27): \[
    P\_{ave}=0.5(P_f+P_b),`\qquad `{=tex}`\Delta `{=tex}P\_{osm}=P\_{ave}-P_d
    \]
8.  Applied pressure difference (Eq. 28) depends on target permeate
    flow, (TCF), (FF), effective membrane area, number of
    elements/vessels and (k_w). Confirm exact notation and whether the
    equation's ΔP includes osmotic pressure before coding.
9.  High-pressure-pump power (Eq. 29): \[
    HP=`\frac{1000\,\dot M_f\,\Delta P}{3600\,\rho_f\,\eta_{hp}}`{=tex}
    \] The equation's numeric factor and units depend on the article's
    definitions of mass/volume flow and pressure; validate dimensionally
    before use.
10. Specific power consumption (Eq. 30): \[
    SPC=`\frac{HP}{\dot M_d}`{=tex} \] with compatible time and volume
    units.

**Important:** these equations were developed for a
seawater/brackish-water system. AquaSolar uses municipal feed near 250
mg/L and a 75 GPD low-pressure membrane. A direct transplant can produce
invalid osmotic pressure, pump power or membrane-flux predictions. Keep
the reference-equation implementation as a separate reproducibility
mode, then implement/validate an AquaSolar mode using measured
membrane/permeance data and the report's design basis. Do not force a
high-salinity model to fit the low-salinity case with unexplained
constants.

For AquaSolar, enforce: \[
`\dot `{=tex}V_f=`\dot `{=tex}V_p+`\dot `{=tex}V_b \] \[
R=`\frac{\dot V_p}{\dot V_f}`{=tex},`\qquad`{=tex}
`\dot `{=tex}V_b=`\dot `{=tex}V_f-`\dot `{=tex}V_p \] and the salt
balance: \[ `\dot `{=tex}V_f X_f=`\dot `{=tex}V_p X_p+`\dot `{=tex}V_b
X_b \] for consistent concentration and volume units, with density
correction if necessary. For ideal salt rejection and
(X_p`\ll `{=tex}X_f), (X_b`\approx `{=tex}X_f/(1-R)). At 250 mg/L and
50% recovery this is approximately 500 mg/L before remineralisation,
consistent with the report's approximate value. Use this as a sanity
check, not as a guarantee of potable quality.

Model permeate production as constrained by the membrane's rated
capacity, feed conditions, pressure, temperature, fouling, and available
runtime. Never allow RO to produce more than the rated/physically
achievable rate simply because the product tank requests water.

### 5.6 DC bus, inverter, battery and auxiliaries

For each timestep, separately account for generation, conversion losses,
loads, charge/discharge and grid flows. Use a single documented sign
convention.

-   MPPT output = available PV DC × MPPT efficiency, subject to
    controller limits.
-   Inverter AC output = DC input × inverter efficiency, subject to
    power rating.
-   Battery SOC evolves from charge/discharge energy and efficiencies,
    bounded by 10--95% SOC in the report.
-   Round-trip efficiency 92% must be allocated into explicit
    charge/discharge efficiencies (for example symmetric square-root
    allocation) or a datasheet-based pair; state which method is used.
-   Auxiliary loads include circulator, RO booster, UV, controller,
    sensors, delivery pump, valves and any auto-flush.
-   Enforce energy priority at the DC bus. Do not count the same PV kWh
    both as battery charging and as direct consumption/export.
-   Model grid import and export separately; the report's "all exported
    PV absorbed by villa loads" is a scenario assumption, not a physical
    grid guarantee.

### 5.7 Concentrate buffer and zero-reject water balance

For every timestep, calculate: - RO feed, permeate and concentrate; -
product-tank inventory, drinking-water demand, quality rejection and
overflow; - concentrate-buffer inventory, RO concentrate input,
toilet-flush demand, municipal top-up, overflow and any measured
disposal.

\[ V\_{f}=V\_{p}+V\_{b} \] \[ V\_{buffer,t+`\Delta `{=tex}t}=
V\_{buffer,t}+V\_{brine,in}-V\_{reuse}-V\_{overflow} \]

Clamp inventory to \[0, 40 L\], but record overflow as a named output.
Flushing demand is served by concentrate first and municipal top-up
second, per report. Do not call the system "zero reject" if overflow,
purge, failed product diversion, or maintenance flushing is untracked.
The report's appendix states that a 1 L RO auto-flush per start is
routed to the brine buffer; include it if reproducing the reported
scenario.

------------------------------------------------------------------------

## 6. AquaSolar supervisory control --- required order

Implement the report's deterministic Level 2 control as a clearly
separated state machine. Safety interlocks always override it.

### 6.1 Safety interlocks (Level 1)

At minimum, stop/divert the relevant process on: - collector/tank
over-temperature; - leak detected; - inadequate feed/booster pressure; -
UV fault or UV intensity below manufacturer requirement; - product-water
TDS or other monitored quality out of configured limits; - sensor
failure or implausible sensor drift; - full product tank / full
concentrate buffer where applicable; - electrical protection or
inverter/battery limits.

The report includes an 85 °C collector/pump cut-out basis, product
quality release interlock, and a weekly ≥60 °C tank hygiene cycle. The
precise trip thresholds and fail positions must be explicit
configuration values and reviewed for hardware safety.

### 6.2 Supervisory dispatch (AquaSolar Report, Section 5.3 and Appendix A)

Apply the following ordered logic each 10-minute step, while preventing
double allocation of power:

1.  Compute weather, POA irradiance, PVT thermal/electrical output and
    pump state.
2.  Serve controller, pumps, RO and UV from PV; then battery if SOC is
    at least 10%; then allowed grid supply/charger path.
3.  If tank top is below 45 °C, use available PV for the DC heater.
4.  Charge battery toward 95% SOC.
5.  After 13:00, divert remaining PV to the DC heater up to 55 °C.
6.  Export/assign remaining electricity to villa loads according to the
    declared bus and tariff boundary.
7.  In comfort windows 04:30--08:00 and 16:30--21:30, if tank top is
    below 50 °C, heat from battery only above the 35% reserve; otherwise
    use the AC element, until the control target of 53 °C is reached.
    Reconcile the report's stated 50 °C top-up threshold and 53 °C
    stopping threshold explicitly.
8.  If the tank has not reached 60 °C during the week, force the hygiene
    cycle to 61 °C on Saturday afternoon, subject to the actual
    hardware's safe operating limits and tempering protection.
9.  Start RO when product tank is below 80% and either solar surplus
    covers RO power or SOC \>50% between 06:00--22:00; also start when
    product tank is below 25% as the report's emergency override. Stop
    when full or when any safety/quality/power interlock fails. Resolve
    precedence if the emergency rule conflicts with unavailable power;
    safety and minimum-power limits win.
10. Route concentrate to buffer. During flushing, draw buffer first and
    municipal top-up second. Count overflow, maintenance flushes and any
    discharge explicitly.

The report also says RO runs "always below 25%" in the summary.
Interpret this as a low-product-tank override, not a claim that the unit
runs continuously at a low tank level. The code should name this rule
and test it.

**Pump hysteresis:** the AquaSolar report specifies a 4 K on / 1 K off
differential, while the Reference Paper uses a 10 K on / 2 K off
description. These are different control bases. Use 4/1 K for AquaSolar
unless measured prototype controller configuration says otherwise.
Define the exact temperature difference and polarity.

### 6.3 Level 3 AI features

Forecasting, learned demand profiles, anomaly detection, predictive
maintenance and digital-twin updates are optional supervisory
enhancements. They must not be silently included in the baseline model.
Baseline results should be reproducible with deterministic control and
fixed inputs. Log every AI recommendation, accepted/rejected action, and
reason.

------------------------------------------------------------------------

## 7. TRNSYS component and variable mapping plan

The Reference Paper reports the following Types/components. The
AquaSolar Report gives a planned TRNSYS mapping. Verify the installed
TRNSYS version and available libraries before relying on a Type number.

  -------------------------------------------------------------------------------------
  Function             Reference Paper   AquaSolar planned Variables to trace
                       mapping           mapping           
  -------------------- ----------------- ----------------- ----------------------------
  Weather              Type 109 TMY2     Type 15-6/109,    time, GHI/DHI/DNI, ambient
                                         Meteonorm TMY     temperature, wind, humidity
                                                           if used

  PVT                  Type 563          Type 560          POA irradiance, inlet/return
                                         equivalent        temperature, mass flow,
                                                           outlet temperature, useful
                                                           heat, DC power

  Tank                 Type 4c           Type 4c, six      each node temperature, node
                                         nodes             mass, losses, heater powers,
                                                           draw/make-up, collector flow

  Circulation pump     Type 3b           Type 3b           on/off signal, mass flow,
                                                           electric power, inlet/outlet
                                                           states

  Hysteresis           Type 2b           Type 2b           measured ΔT, on/off
  controller                                               thresholds, controller
                                                           output

  General/difference   Type 2d           Type 2d plus      SOC, tank top, product
  controller                             Python/control    level, RO enable, interlocks
                                         logic             

  Mixing/tempering     Type 11b          Type 11b          hot/cold inlet flow and
  valve                                                    temperatures, delivery set
                                                           point, outlet
                                                           temperature/flow

  Flow-control valve   Type 11f          Type 11f          inlet flow, split signal,
                                                           branch flows

  Inverter             Type 48a          Type 48 / verify  DC power, AC power,
                                         exact             conversion efficiency,
                                         Type/version      rating

  RO equations         EES called via    Type 66a or       feed/permeate/concentrate,
                       Type 66a          native equations  TDS, pressure, temperature,
                                                           recovery, pump power

  Battery              not in core       Type 47 planned   SOC, charge/discharge,
                       reference table                     efficiencies, power limits

  Brine buffer         not in reference  Type 39 planned   inventory, brine input,
                       design                              reuse draw, top-up, overflow

  Demand profile       reference         Type 14h planned  timestep demand and setpoint
                       figures/tables                      

  MPPT / DC controls   not fully         verify component  DC generation, controller
                       represented as    or custom model   efficiency, bus balance
                       AquaSolar                           

  UV, sensors, quality not reference     likely            power, status, TDS, pH,
  gate                 system            custom/native     turbidity, UV state,
                                         logic             release/divert volume
  -------------------------------------------------------------------------------------

**Variable mapping record format (mandatory):**

  -----------------------------------------------------------------------
  Field                               Description
  ----------------------------------- -----------------------------------
  `variable_id`                       Stable unique ID,
                                      e.g. `pvt.q_useful_W`

  `meaning`                           Physical meaning

  `unit_internal`                     Canonical unit

  `python_symbol`                     Exact variable/attribute name and
                                      file/function

  `trnsys_instance`                   Deck component label/instance

  `trnsys_type_output`                Type number and output index/name,
                                      as applicable

  `source`                            Reference Paper equation/table,
                                      AquaSolar report section/table,
                                      datasheet, or measurement

  `equation_id`                       Equation identifier in this
                                      document or source

  `consumers`                         Downstream variables/components

  `status`                            MATCH / ADAPTED / MISSING /
                                      CONFLICT / UNKNOWN / N/A

  `test_id`                           Test that validates this mapping
  -----------------------------------------------------------------------

Do not invent TRNSYS output indices. Read them from the deck/component
proforma and record the version-specific mapping.

------------------------------------------------------------------------

## 8. Python architecture recommended for auditability

The agent should map the existing code to this conceptual structure; do
not create duplicate modules before inventorying the repository.

``` text
simulation/
  config/          # design parameters, units, weather source, scenario definitions
  weather/         # TMY reader, POA irradiance, sun geometry
  pvt/             # thermal collector and PV cell/electrical model
  tank/            # six-node transient tank and stratification
  hydraulics/      # pump, valves, mixing, flow state
  electrical/      # DC bus, MPPT, inverter, battery, grid
  ro/               # reference-paper RO mode and AquaSolar RO mode
  water/            # product tank, quality gate, brine buffer, flushing balance
  controls/         # safety interlocks, deterministic dispatch, optional AI policy
  metrics/          # energy/exergy, water, economics, KPIs
  io/               # logging, result exports, plots, reports
tests/
  unit/
  integration/
  regression/
  conservation/
```

### Timestep order

Use one documented timestep sequence, and avoid updating a state twice
in the same step:

1.  Read weather, inlet-water state, demand and previous storage states.
2.  Compute POA irradiance and collector/pump control from prior state
    and current forcing.
3.  Calculate PVT thermal/electrical outputs.
4.  Calculate hot-water draw, tank node flows, heat losses, heater
    inputs, and update tank states using a stable integration method.
5.  Determine available DC/AC power and dispatch critical loads, RO,
    battery, heater and export in the documented order. If the PVT
    thermal model needs the pump state from the controller, make the
    dependency explicit.
6.  Calculate RO feed/permeate/brine and RO electrical demand only when
    enabled and power/quality conditions permit.
7.  Update product-water and brine-buffer inventories, including demand,
    reuse, top-up, flush and overflow.
8.  Update battery SOC and grid exchanges without double counting
    energy.
9.  Apply output-quality release/diversion logic and safety-state
    transitions.
10. Write timestep outputs, mass/energy residuals, and state flags.

The precise order may require a predictor-corrector iteration because
pump state, collector output, tank temperature and power dispatch are
coupled. If iteration is used, specify convergence tolerance and maximum
iterations. Compare the same time-step convention with TRNSYS.

------------------------------------------------------------------------

## 9. Equation and variable traceability checklist

The agent must populate this matrix from the actual code and deck. Blank
cells are work to do, not permission to infer.

  ----------------------------------------------------------------------------------------------------
  Model block        Source equation /  Required inputs    Required outputs / states  Required audit
                     design basis                                                     
  ------------------ ------------------ ------------------ -------------------------- ----------------
  Weather / POA      AquaSolar report   timestamp,         POA irradiance             compare to
                     §6.2; Erbs diffuse GHI/DHI/DNI or                                weather source
                     split + isotropic  weather-native                                and annual POA
                     transposition      inputs, tilt,                                 
                                        azimuth, albedo                               

  PVT heat           Reference Paper    POA, ambient,      useful heat, outlet/mean   compare selected
                     Eqs. 6--11 **or**  inlet temperature, fluid temperature          model and units
                     AquaSolar Type-560 flow, collector                               
                     equivalent         parameters                                    

  PV electricity     Reference Paper    POA, cell          gross/net DC power         verify
                     Eq. 12 as          temperature, ηref,                            temperature
                     baseline;          β, derate, area                               response and
                     AquaSolar                                                        clipping
                     cell-temperature                                                 
                     model                                                            

  Pump controller    AquaSolar 4/1 K;   tank/collector     pump on/off, flow, power   hysteresis test;
                     85 °C cut-out      temperatures,                                 no chatter
                                        previous state                                

  Tank               Reference Paper    previous node      six node temperatures,     residual,
                     Eq. 13 / Type 4c   temperatures,      losses                     stratification
                                        flows, UA,                                    and energy
                                        heaters, ambient                              conservation

  Mixing valve       Reference Paper    hot/cold           hot/cold split, delivery   target tracking
                     flow scheme; ideal temperatures,      temperature                and bounds
                     mixing equation    delivery target,                              
                                        draw                                          

  RO flow/recovery   Reference Paper    target flow,       feed, permeate,            mass balance and
                     Eq. 16; AquaSolar  available feed,    concentrate                rated capacity
                     50% recovery       tank demand,                                  
                                        recovery                                      

  RO salt balance    Reference Paper    feed TDS,          product and concentrate    salt balance;
                     Eqs. 17--19;       rejection/salt     TDS                        unit conversion
                     AquaSolar salt     passage, flows                                
                     conservation                                                     

  RO                 Reference Paper    temperature, TDS,  pressure requirement, pump dimensional
  hydraulics/power   Eqs. 20--30;       membrane           power, SPC                 audit and
                     AquaSolar measured area/permeance,                               datasheet
                     low-pressure unit  pressure,                                     comparison
                                        efficiency                                    

  DC bus             AquaSolar §5.1,    PV, MPPT, loads,   each power path, grid      bus residual; no
                     §5.3, Table 2      battery, inverter  import/export              double counting

  Battery            AquaSolar SOC      previous SOC,      next SOC, losses           bounds and
                     limits and         charge/discharge                              energy balance
                     efficiency         power, Δt                                     

  Product tank       30 L capacity,     RO permeate,       inventory, unmet demand,   water balance
                     target 25 L/day    demand, diversion, overflow                   
                                        initial volume                                

  Brine loop         40 L buffer,       concentrate,       reuse, top-up,             zero-reject
                     flush-first reuse, flushing demand,   overflow/reject            claim must be
                     top-up second      flush water,                                  measured
                                        inventory                                     

  Quality gate       AquaSolar Appendix sensor values, UV  release/divert flag,       fail-safe test
                     A4                 state, limits      rejected volume            

  Exergy             Reference Paper    temperatures,      fuel/product/destruction   common dead
                     Eqs. 3--5 and      streams, power,                               state,
                     Table 3            solar exergy model                            nonnegative
                     definitions;                                                     residuals
                     AquaSolar report                                                 

  KPIs               AquaSolar Table 3  timestep outputs   annual totals/fractions    formula
                     and §6.3                                                         definitions and
                                                                                      units

  Economics          AquaSolar report   CAPEX/OPEX,        cost per litre, savings,   keep financial
                     §7 and Appendix B  tariffs, life,     payback                    assumptions
                                        discount rate                                 separate from
                                                                                      physics
  ----------------------------------------------------------------------------------------------------

------------------------------------------------------------------------

## 10. Required annual outputs and report benchmarks

Use these values as **regression targets to investigate**, not
hard-coded outputs. Results will depend on weather file, implementation,
initial conditions, load profiles and interpretation of assumptions.

  -----------------------------------------------------------------------
  KPI                                 AquaSolar Report S3 reference value
  ------------------------------ ----------------------------------------
  Plane-of-array irradiation                              13,714 kWh/year

  PV electricity (DC)                                      2,189 kWh/year

  PVT useful heat                                          1,310 kWh/year

  Hot water delivered                  200 L/day at 45 °C; 1,351 kWh/year
                                                                 reported

  Heater electricity from PV /                     77 / 194 / 44 kWh/year
  battery / grid                 

  System loads (controller,                                   76 kWh/year
  pumps, RO, UV)                 

  Electricity to villa / grid                         1,709 / 44 kWh/year
  import                         

  Net electricity balance                                 +1,665 kWh/year

  Solar-thermal / renewable                                     81% / 97%
  hot-water fraction             

  Electrical self-sufficiency                                         89%

  Energy / exergy efficiency                                22.3% / 13.7%

  Drinking water produced             9.14 m³/year (report also describes
                                                 nominal 25 L/day target)

  RO feed / concentrate reused /                   18.6 / 9.5 / 0 m³/year
  reject to drain                

  RO specific energy: booster /                        1.26 / 1.56 kWh/m³
  including UV and valves        

  Product TDS after                            67 mg/L (P10--P90: 64--72)
  remineralisation               

  RO / circulation pump                                459 / 2,580 h/year
  operating hours                
  -----------------------------------------------------------------------

The report describes 40 Monte Carlo runs and gives P10--P90 ranges for
selected outputs. Reproduce uncertainty only after deterministic model
closure is demonstrated. Store the random seed and all sampled
parameters.

------------------------------------------------------------------------

## 11. Mandatory inconsistency and plausibility audit

The agent must explicitly examine these items before claiming successful
replication:

1.  **Reference vs AquaSolar size mismatch:** 20 m² PVT / 300 L tank /
    200 kg/h / 12% reference efficiency in the Reference Paper versus 6
    m² / 150 L / 40 kg/h / 20% reference efficiency in AquaSolar.
2.  **RO feed mismatch:** 45,000 ppm seawater in the paper versus about
    250 mg/L municipal feed in AquaSolar. The paper's pressure, osmotic
    and membrane assumptions may not be valid for the new case.
3.  **Recovery mismatch:** 15% reference recovery versus 50% AquaSolar
    recovery.
4.  **Tank node topology:** source article node numbering and AquaSolar
    collector-return/top-up locations must be reconciled with the actual
    deck.
5.  **Weather mismatch:** synthetic screening weather versus Meteonorm
    TMY; confirm the exact weather file and annual irradiation.
6.  **PV model mismatch:** Reference Paper's simple efficiency equation
    versus AquaSolar's temperature-dependent model.
7.  **Controller mismatch:** Reference Paper's 10 K on / 2 K off
    hysteresis and three-case RO dispatch versus AquaSolar's 4 K / 1 K
    pump control and layered priority dispatch.
8.  **RO capacity arithmetic:** 75 GPD is a nominal rating under
    manufacturer test conditions; check whether the model's 25 L/day
    target and 459 h/year runtime are mutually consistent with actual
    production and derating.
9.  **Water-balance arithmetic:** 25 L/day year-round is 9.125 m³/year,
    close to the report's 9.14 m³/year; verify that product demand and
    production are not conflated. At 50% recovery, 9.14 m³ product
    implies about 18.28 m³ feed and 9.14 m³ concentrate before flushes,
    whereas the report lists 18.6 m³ feed and 9.5 m³ concentrate.
    Investigate differences due to flush water, time-step accounting,
    and rounding rather than forcing totals.
10. **Concentrate reuse:** the report describes about 9.5 m³/year
    concentrate reused and zero reject; prove this from buffer
    inventory, toilet demand, flushing and overflow logs.
11. **Electricity balance:** distinguish PV DC generation, post-MPPT
    power, battery charge/discharge, heater use, system auxiliaries,
    inverter output, villa load and export. Do not infer the net balance
    from a single total.
12. **Heat balance:** compare collector heat, tank losses, delivered
    useful heat, backup heat and stored-energy change. Explain any
    difference between 1,310 kWh useful PVT heat and 1,351 kWh delivered
    hot-water energy.
13. **Control conflict:** report's summary mentions morning/evening
    top-up to 50 °C; Appendix A says heating until 53 °C. Use 50 °C as
    enable threshold and 53 °C as stop target only if
    approved/documented.
14. **Temperature limits:** report describes a 55 °C PV diversion limit,
    a weekly 61 °C hygiene cycle, summer tank values 60--75 °C, and an
    85 °C cut-out. Ensure these apply to distinct state variables and
    are physically compatible; include a tempering valve and scald
    protection.
15. **Efficiency definitions:** energy and exergy efficiencies need
    explicit numerator/denominator boundaries. Use the same boundary as
    the report/reference when comparing.
16. **Exergy equations:** establish one dead-state (T_0); use the
    correct physical exergy expression and a documented solar-radiation
    exergy factor. Do not compare exergy totals computed with different
    dead states.
17. **Water quality:** simulated TDS/pH/turbidity/UV status is not proof
    of microbiological safety. The model may represent a quality
    interlock but cannot certify potable water without laboratory
    evidence.
18. **Missing diagrams/equations:** some equation images in the report
    PDF may not be extractable as text. Recover the visual equation from
    the PDF or use the cited source; do not reconstruct corrupted
    symbols by guesswork.

------------------------------------------------------------------------

## 12. Validation and acceptance criteria

### 12.1 Unit tests

-   Unit conversion tests: W↔kW, J↔kWh, kg/h↔kg/s, L↔m³, mg/L↔kg/m³,
    °C/K differences, bar/Pa.
-   PVT: zero irradiance should yield no solar generation; increasing
    irradiance should not reduce generation under otherwise identical
    conditions; hotter cells should reduce PV output when β is negative.
-   Pump hysteresis: on at the configured turn-on threshold; remains on
    inside deadband; off at turn-off threshold; over-temperature
    interlock overrides.
-   Tank: no heat loss when tank and ambient temperatures match; losses
    reverse direction only if model permits; heater adds energy; draws
    reduce stored energy; temperatures remain finite and physically
    bounded.
-   Mixing valve: delivery never exceeds hot inlet due solely to ideal
    mixing; computed split lies within \[0,1\].
-   RO: feed = permeate + concentrate; salt balance closes; recovery
    remains within \[0,1\]; product output never exceeds capacity or
    available feed; pump power nonnegative.
-   Battery: SOC always within 10--95%; charge/discharge cannot occur
    simultaneously unless explicitly supported; efficiency losses are
    accounted for.
-   Product tank and brine buffer: inventory remains within capacity; no
    silent overflow; unmet demand is logged.
-   Quality gate: UV/TDS fault means no release to tap.
-   Deterministic repeatability: same input, initial state and seed
    produce identical outputs.

### 12.2 Integration tests

-   Clear sunny day, low tank temperature.
-   Cloudy day with no usable PV surplus.
-   High tank temperature / pump cut-out.
-   Product tank below 25% with inadequate available power.
-   Product tank at 90% and no demand.
-   Battery at 10%, 35%, 50% and 95% SOC.
-   Full brine buffer during low toilet demand.
-   High toilet demand with insufficient brine.
-   Out-of-specification product water and UV failure.
-   Grid outage / controller offline / sensor fault.
-   Seven-day hygiene cycle.
-   Full-year run with initial-state spin-up and no unexplained state
    discontinuities.

### 12.3 Acceptance checks

The report's planned prototype targets are daily PV and useful heat
within ±10%, tank temperatures within ±2 K, and product water tested
against applicable WHO/UAE limits. Treat these as future calibration
targets, not as already achieved. Before prototype validation,
require: - tank and battery annual energy residuals within 0.5% (the
report says its screening model achieved this); - mass balance closure
for all water streams within a defined numerical tolerance; - no
unlogged reject/overflow; - no duplicate electrical energy allocation; -
all annual KPIs generated from timestep outputs, never hard-coded.

------------------------------------------------------------------------

## 13. Agent workflow and deliverable format

### Phase A --- inventory, read-only

1.  List all input files and hashes; identify the authoritative TRNSYS
    deck and Python entry point.
2.  Read TRNSYS project/deck connections, component parameters and
    external calls.
3.  Identify Python modules, equations, constants, initial conditions,
    timestep, solver and outputs.
4.  Record current run commands and baseline results.
5.  Produce `inventory.md` and a copy of baseline output.

### Phase B --- map and compare

1.  Build component map and variable lineage table.
2.  Recreate thermal/electrical/water/control diagrams from actual
    files.
3.  Compare actual implementation to Sections 3--8.
4.  Assign each item a status and evidence location (file, line, deck
    component, page/table/equation).
5.  Produce `traceability_matrix.csv`, `difference_register.md`, and
    diagrams.

### Phase C --- verify equations and units

1.  Trace each equation to its exact source and implementation.
2.  Check dimensional consistency and numerical ranges.
3.  Separate the Reference Paper RO mode from AquaSolar RO mode.
4.  Run component-level tests and conservation tests before annual
    comparisons.
5.  Record equation variants and why one was selected.

### Phase D --- calibrated regression

1.  Run deterministic baseline on a known weather year and fixed seed.
2.  Compare with the AquaSolar Report KPIs and investigate each material
    difference.
3.  Run sensitivity checks for flow, tank volume, PVT area, battery
    size, RO recovery, membrane performance and demand.
4.  Only then run Monte Carlo scenarios.
5.  Produce a reproducible report including configuration, code
    revision, input file hashes, run timestamp, timestep, solver, units,
    and residuals.

### Phase E --- controlled changes

For every proposed code/deck change, provide: - reason and evidence; -
old and new equation/parameter; - expected effect; - test added; -
before/after KPIs; - rollback path.

Do not optimize for matching the report's annual numbers at the expense
of conservation laws or physical correctness.

### Required final audit report outline

1.  Executive status: what runs, what does not, what is unknown.
2.  Actual TRNSYS topology and Python architecture.
3.  Process diagrams.
4.  Component/variable/equation traceability.
5.  Reference-to-AquaSolar adaptation decisions.
6.  Unit, mass, energy and exergy balance results.
7.  Annual KPIs vs report benchmarks.
8.  Unresolved conflicts and human decisions required.
9.  Prioritized implementation plan.
10. Reproducibility appendix.

------------------------------------------------------------------------

## 14. Source references

-   **Reference Paper:** Khanmohammdi, S., Musharavati, F., &
    Sheykhmohammadi, M. (2022). "Energy and exergy examinations of a PVT
    based hybrid system for power, heating and potable water production:
    Transient modeling." *Renewable Energy*, 195, 540--553. DOI:
    https://doi.org/10.1016/j.renene.2022.05.114. Relevant sections:
    system definition and assumptions; mathematical simulation
    §§3.1--3.1.3; Tables 1--3; Figs. 1--4.
-   **AquaSolar Report:** *AquaSolar Living: Smart PVT-Integrated Water
    Assurance and Domestic Hot-Water Cogeneration for Sustainable Villa
    Communities*. Relevant sections: §5 system and control; §6
    methodology, model formulation, components and benchmarks; Appendix
    A parameters, exergy and timestep control logic; Appendix B costs
    and water-quality plan.

**Final operating principle:** use the Reference Paper to understand and
reproduce the original TRNSYS/EES method; use the AquaSolar Report to
define the new system; use the actual project files to establish what
has already been implemented; and use conservation, tests and
measurements---not a desired annual KPI---to decide whether the
simulation is correct.
