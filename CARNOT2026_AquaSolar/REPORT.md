# AquaSolar Living: Comprehensive Project Report for Carnot 2026

This document consolidates the core technical material from the project codebase, input registry, model documentation, and project report into a single competition-ready narrative. It is intentionally written as a substantive technical draft that can later be re-formatted for polishing, slide adaptation, and final submission.

## 1. Executive summary

AquaSolar Living is a villa-scale mathematical model for an integrated photovoltaic-thermal (PVT) and water-assurance system intended for the UAE residential context. The central concept is to exploit high desert solar irradiance to generate both electricity and useful heat, store that thermal energy, and use a staged water-treatment logic to deliver safe water while reducing unnecessary treatment intensity.

The system is designed as a realistic energy-water coupling problem: a solar collector converts irradiance into both electrical output and thermal energy, a thermal loop moves heat toward a storage tank, and a treatment train uses a minimum-necessary-treatment (MNT) logic to balance water quality, energy consumption, and operational burden. The project is not presented as a final validated engineering design; rather, it is a transparent and reproducible research model with a clear numeric backbone and an explicit set of assumptions, limits, and data provenance.

The simulation code in the repository reflects a staged development path. The main full-system architecture is present in the codebase, but the only currently runnable end-to-end path is the PVT-only exploratory simulation. That means the model is strongest as an honest, defendable, reproducible exploratory system model that demonstrates a valid mathematical routine under UAE weather conditions (specifically Ras Al Khaimah International Airport TMYx meteorological profile).

## 2. Real-world problem and relevance

The United Arab Emirates faces a combined energy and water stress problem. Residential buildings require cooling, water heating, pumping, and treated water while also operating under high temperature and strong solar resource availability. In this context, PVT systems are especially relevant because they can jointly deliver electrical power and useful heat from the same collector area.

This dual-use logic is attractive for villa-scale urban and peri-urban settings because it reduces the need to treat energy and water as isolated systems. In the AquaSolar concept, a collector acts as a thermal and electrical energy source, the tank stores the heat to shift supply into later demand periods, and the water treatment train can selectively respond to demand and quality constraints rather than over-treating all water at a fixed intensity.

The project’s relevance to the competition is therefore not simply that it solves a general energy or water problem in isolation, but that it addresses the coupled trade-off between solar exploitation, thermal storage, electrical load satisfaction, and potable-water quality.

## 3. Scope and current status

The repository clearly distinguishes between what is complete and what is still exploratory. The project report states that the current runnable scope is only the PVT-only path. The tank, loop, treatment, electrical-bus, and economics modules are coded but not yet integrated into a single end-to-end execution path.

This is important to the scientific framing of the project. The package should be understood as:

- a mathematically explicit and reproducible system model,
- focused on the coupled PVT thermal/electrical formulation,
- designed with modular subsystem logic for future full-system integration,
- and intentionally bounded so that the reported results remain scientifically honest.

## 4. Architecture of the proposed system

The conceptual system architecture is:

1. Solar irradiance reaches the PVT collector
2. The collector simultaneously produces electrical output and useful thermal energy
3. Useful heat is transferred to a stratified thermal storage tank
4. The tank supplies domestic hot water or thermal demand
5. Water treatment trains process source water through options such as filtration, membrane treatment, and disinfection
6. Electrical generation and treatment loads are balanced against grid support and parasitic power use
7. The whole system is evaluated using a combination of energy, quality, and economic metrics

The architecture is intentionally modular. The project code is decomposed into subprocesses for weather, PVT physics, solar loop control, tank dynamics, treatment logic, MNT decision rules, electrical balancing, and economics. This modularity improves transparency and reproducibility, which is a major strength for a competition in which judges will look for defendable assumptions and reproducibility.

## 5. Data flow and input structure

The simulator is built around externalized data rather than hardcoded constants. The input registry organizes data under several categories:

- parameter YAML files in `inputs/parameters/`
- timeseries CSV files in `inputs/timeseries/`
- lookup tables in `inputs/tables/`
- provenance and evidence files in `inputs/provenance/`
- approvals and validation documents in `inputs/approvals/`
- a global index in `inputs/input_index.yaml`

The data architecture is designed so that every declared parameter, table, and timeseries entry is traceable. The project report explains how the registry and loader pipeline works:

- `input_index.yaml` declares the parameter inventory and required conditions
- `registry/schema.py` provides structured parameter metadata with fields for id, unit, source type, source reference, and status
- `registry/load.py` reads the parameter files and validates required conditions
- `io/timeseries.py` loads time-indexed datasets and validates data quality and spatial/temporal consistency
- `io/quality_report.py` produces quality reports rather than silently repairing bad data
- `defaults.py` creates a seed-based demo configuration when values are blank, clearly labelling them as assumptions rather than calibrated engineering values

The CLI command `aquasolar check-inputs` validates all registered inputs and writes the status report to `inputs/STATUS.md`, which makes the package reproducible and auditable.

## 6. Weather processing

Weather processing is a critical part of the system because PVT performance depends strongly on irradiance, ambient temperature, wind, and optical geometry. The code uses a solar geometry + transposition pipeline to convert raw meteorological variables into effective plane-of-array irradiance.

The relevant set of modules is:

- `weather/solar_geometry.py`: computes solar zenith, azimuth, and geometric incidence angle
- `weather/transposition.py`: converts GHI/DNI/DHI into plane-of-array irradiance with supported transposition methods
- `weather/iam.py`: implements incidence-angle modifier logic
- `weather/soiling.py`: models soiling corrections as a multiplicative factor in the range `[0,1]`

The resulting effective irradiance is approximated as:

$$G_{eff} = G_{POA} \times IAM \times \phi_{soil}$$

where the final irradiance used in the PVT calculation is the result of the geometry and optical adjustments, not simply the raw weather input.

## 7. Mathematical model

### 7.1 PVT electrical output

The electrical output is represented using a temperature-corrected efficiency formulation. The project register states the form as:

$$P_{el} = \eta_{ref} \left[1 - \beta (T_c - T_{ref})\right] \phi_{soil} G_{eff} A f_{irr} f_{MPP}$$

where:

- $\eta_{ref}$ is the reference electrical efficiency,
- $\beta$ is the temperature coefficient of efficiency,
- $T_c$ is the cell temperature,
- $T_{ref}$ is the reference temperature,
- $\phi_{soil}$ is the soiling factor,
- $G_{eff}$ is the effective irradiance,
- $A$ is the collector area,
- $f_{irr}$ is the irradiance correction factor,
- $f_{MPP}$ is the maximum-power-point factor.

This equation is central to the coupled energy formulation because it links cell temperature to electrical performance and therefore to useful heat generation.

### 7.2 Useful heat and collector thermal balance

The useful thermal output is represented by the classical thermal balance form:

$$Q_u = A F_R \left[S - U_L (T_{f,in} - T_a)\right]$$

with

$$S = \tau_{\alpha} G_{eff} - \frac{P_{el}}{A}$$

The terms are:

- $Q_u$: useful thermal output,
- $A$: collector area,
- $F_R$: heat-removal factor,
- $U_L$: overall heat-loss coefficient,
- $T_{f,in}$: collector inlet temperature,
- $T_a$: ambient temperature,
- $S$: absorbed solar energy term,
- $\tau_{\alpha}$: transmittance-absorption factor.

This formulation is consistent with the project’s PVT assumption that useful heat is produced alongside electrical output and that the two are thermally coupled through the cell temperature and flow conditions.

### 7.3 Cell temperature and outlet temperature loop

The cell temperature is represented by a thermal resistance relation between the cell and the fluid:

$$T_c = T_{f,m} + R_{cf} q_{cf}, \quad T_{f,m} = \frac{T_{f,in} + T_{f,out}}{2}$$

The collector fluid outlet follows from an energy balance:

$$T_{f,out} = T_{f,in} + \frac{Q_u}{\dot{m} c_{p,f}}$$

This relation is the backbone of the coupled algebraic loop. In the project implementation, the solver iteratively solves the mutually dependent values of cell temperature, electrical output, useful heat, and outlet temperature using a bracketing or bisection method over the collector outlet temperature.

The code clearly states that the solver is bisection-based, with an inner cell-temperature iteration and a residual of the form:

$$r = T_{in} + \frac{Q_u}{\dot{m} c_{p,f}} - T_{out}$$

The implementation uses a strict convergence tolerance and a physically meaningful upper bound on the fluid temperature.

### 7.4 Thermal storage and tank dynamics

The tank model is built around node-wise energy balances and is described in the project report and code as a stratified, multi-node thermal storage system. The governing balance is:

$$\rho c_p V_i \frac{dT_i}{dt} = Q_{charge,i} + Q_{adv,i} + Q_{cond,i} - Q_{loss,i} + Q_{aux,i}$$

This expresses the local thermal state as the balance between charging, advection, conduction, losses, and auxiliary heating. The key project report also describes additional relations such as:

$$Q_{cond,i} = \frac{k_{eff} A_x}{\Delta z}(T_{i+1} - 2T_i + T_{i-1})$$

and

$$Q_{loss,i} = UA_i (T_i - T_{amb})$$

The project uses idealized mixing assumptions and constant fluid properties for the operating range of interest rather than a full CFD-scale thermal stratification model. This is consistent with the stated simplicity-over-complexity principle of the competition.

### 7.5 Water treatment pathways and MNT logic

The water-assurance portion of the model is organized into treatment chains. The project defines a set of stage-level water balances:

$$m_{feed} = m_{prod} + m_{rej}$$

$$m_{feed} c_{feed} = m_{prod} c_{prod} + m_{rej} c_{rej}$$

Recovery and rejection are then represented as:

$$R = \frac{V_{prod}}{V_{feed}}, \quad R_k = 1 - \frac{c_{prod}}{c_{feed}}$$

The coded treatment modules track species such as turbidity, TSS, DOC, chlorine, VOCs, coliform, viruses, hardness, sulfate, TDS, alkalinity, and pH. The system uses discrete pathway logic — A/B/C or a minimum-necessary-treatment approach — to select the least-intensive treatment route that still satisfies treatment quality constraints. This is important for the engineering narrative because it addresses the desire to avoid over-treatment while still meeting quality requirements.

For hydraulic treatment energy, the project uses:

$$P_{hyd} = Q_{feed} \frac{\Delta p}{\eta_{pump}}$$

and for the energy intensity of water production:

$$E_{spec} = \frac{E_{electric}}{V_{prod}}$$

The MNT logic is a decision rule, not a final plant design; it is intended to demonstrate the trade-off between quality, treatment intensity, and energy consumption.

### 7.6 Electrical balance and economics

The project frames the electrical side as a balance between solar generation, parasitic loads, and grid interaction. A simplified system-level formulation is:

$$E_{el,total} = E_{PVT} + E_{grid} - E_{dump}$$

The economics are represented through cost and levelized metrics, including annualized cost and product-water cost proxies. The equations in the report and code point to lifecycle and levelized cost logic, but the project remains explicit that this is an exploratory system model and not a fully validated engineering design.

## 8. Assumptions and model boundaries

The assumptions register and project documentation identify the main boundary conditions of the model. The most important assumptions are:

1. The collector cell temperature is uniform across the active collector area.
2. The PVT collector is treated as steady-state within each hourly interval.
3. The inlet fluid temperature is fixed for the duration of the exploratory PVT interval.
4. Pipe heat loss, recirculation, and full tank stratification are not included in the default PVT-only runner.
5. Fluid properties are treated as constant over the operating range.
6. Soiling is represented as a multiplicative correction factor rather than a dynamic deposition process.
7. The treatment train is represented as a decision model, not a fully validated membrane or UV plant design.
8. The weather input is derived from the Ras Al Khaimah International Airport TMYx profile (`ARE_RK_Khaimah.Intl.AP.411840_TMYx.epw`, converted to `inputs/timeseries/weather.csv`) with full metadata sidecar, rather than a fully calibrated field dataset.
9. The outputs are exploratory research estimates, not certified engineering results.
10. The model prioritizes transparency, traceability, and defendability over unbounded complexity.

These assumptions are essential to the report because they explain both the strengths and the limits of the simulation. The project is strong precisely because it makes these assumptions explicit rather than burying them inside the code.

## 9. Inputs, calibration, and provenance

The package includes a full set of input data and provenance records. The main data sources include:

- weather CSVs and metadata files in `inputs/timeseries/`
- parameter files in `inputs/parameters/`
- tables for cost, quality limits, treatment removals, and operational curves in `inputs/tables/`
- provenance metadata in `inputs/provenance/`

The project report also explains that the repository keeps measured, literature-derived, and assumption-based values distinct. This matters because the model intentionally separates:

- measured data,
- literature-derived parameter choices,
- and seeded defaults that are clearly labelled as assumptions until validated.

**Clarification on parameter status:** In the parameter schema and `inputs/STATUS.md`, the status `confirmed` indicates that a parameter record is complete, checked against schema bounds, and backed by a documented reference—it does **not** mean the value has been physically measured or calibrated. Assumptions, design baselines, and literature proxies surface their `source_type` (e.g. `literature`, `assumption`, `design_basis`) and explicit `source_ref` alongside numeric values so reviewers cannot confuse assumptions with observations.

The fact that the simulation requires checks such as `aquasolar check-inputs` and produces `inputs/STATUS.md` is an important contribution to reproducibility and rigour. It ensures that the result is not only numerically reproduceable but also traceable in terms of all conditions that influence the model.

## 10. Simulation workflow and outputs

The key runnable workflow is:

```powershell
cd CARNOT2026_AquaSolar
python -m venv .venv
python -m pip install -e ".[solar]"
python -m aquasolar apply-demo-defaults
python -m aquasolar check-inputs
python -m aquasolar run carnot-reproduction --weather inputs/timeseries/weather.csv
python -m pytest -q
```

The run produces output artifacts in `outputs/pvt_only/`, including:

- a CSV file with hourly simulation results, and
- a summary JSON with key performance metrics such as electrical energy, useful heat, and execution metadata.

**Active vs Unpopulated Metrics:** The runnable PVT simulation actually emits only two primary metrics:
- `M-PV-01`: electrical energy generated (joules and kWh)
- `M-TH-01`: useful thermal heat collected (joules and kWh)

Other metrics defined in the project register—including `M-IN-01` (combined solar utilization), water-treatment recovery and specific energy, and downstream levelized cost metrics—are formal specifications for the modular subsystems but are **not** populated by the current PVT-only execution path. Reviewers can verify this directly in `outputs/pvt_only/carnot-demo.summary.json`.

These metrics make the results interpretable and support the narrative that the model is not just a solver but a decision-support framework.

## 11. Validation and reproducibility

The project report and the full codebase make clear that reproducibility is an expected part of the submission. The validation path includes:

- parameter checking via `check-inputs`
- table and timeseries validation
- scenario-specific output generation
- test suite execution in `tests/`
- output files saved as reproducible artifacts

The project’s own validation status is that the simulation remains exploratory and the output must be interpreted correctly. In other words, the code is intended to demonstrate a valid model structure and reproducible calculations, not to certify a final design installation. This is consistent with the competition requirement that the model be rigorous and reproducible without going beyond the evidence.

## 12. Current implementation status and limitations

The project’s central limitation is scope. The project report explicitly states that the full system runner — covering tank dynamics, DHW demand, electrical-bus dispatch, and water treatment integration — exists as code but is not yet wired into an executable full-system path. Therefore:

- the PVT-only sequence is the only end-to-end runnable path,
- the upstream modules are well-structured and logically complete,
- the integrated system remains a future engineering extension,
- and the report must avoid claiming that all of it has already been validated as a whole.

This limitation is also a strength: it prevents overclaiming and makes the project easier to defend as a transparent, modular system model rather than a false “complete design” claim.

## 13. Novelty and contribution

The project is novel in the way it combines a villa-scale PVT collector with a water-assurance logic framework in a single explanatory structure. It is not merely a solar energy report or a water treatment paper in isolation; it is a coupled system model aimed at a desert residential use case. The novelty lies in the explicit bridging of:

- solar collection and thermal/electrical output,
- storage and thermal buffering,
- water treatment pathway selection,
- quality thresholds and energy trade-offs,
- and the reproducible, modular system description.

This is also relevant to the competition theme because it addresses an energy problem in a way that is grounded in real-world UAE conditions and uses a mathematically transparent formulation rather than a black box.

## 14. Prior work disclosure and AI usage

The competition rules require prior work to be disclosed and permit AI use if it is properly credited. Complete prior work history and AI tool disclosures are documented in [DISCLOSURE.md](DISCLOSURE.md).

Specifically:

- Prior AquaSolar Living work and team-linked project documents (CMAT-00184 Theme 5 Final Report, AURAK 2026, and earlier white papers) form the technical baseline.
- New work for Carnot 2026 includes the restructured mathematical formulation, externalized parameter and weather provenance registries, clean standalone package installation, and reproducibility verification gates.
- AI tools (large language models and code assistants) were utilized for documentation drafting, equation formatting, and packaging hygiene, while the authors retain full responsibility for the model formulation, scientific interpretation, and verification.

## 15. Conclusions

AquaSolar Living is a strong candidate for a competition submission because it combines a relevant energy-water challenge, a mathematically explicit model, modular subsystem structure, externalized and traceable inputs, reproducible outputs, and a defensible narrative about the limits of the current model.

The project is not a final validated engineering solution, but that is not a weakness under the rules of the competition. The competition explicitly rewards simple, well-justified models over complex but weakly defended ones. This project’s strength lies in its transparency, traceability, and disciplined formulation under a realistic problem context.

In a live defence, the project can be explained as a coupled PVT + thermal + water-assurance system whose main scientific value is in the explicit structure of the governing equations, the solver logic, and the clearly stated assumptions that bound the model. That is the right level of sophistication for a competitive mathematical modelling submission.

## 16. References

The project bibliography and supporting references include a combination of engineering texts, project documents, and literature describing solar cogeneration and water-treatment systems. The repository includes the cited PDF set and a bibliography file in the final submission package. The report should therefore be read alongside the package bibliography and the model equations register.

Key source families include:

- Duffie & Beckman: solar thermal process fundamentals,
- project reports and white papers by AURAK and CMAT-00184,
- membrane/distillation and cogeneration literature included in the reference PDFs,
- and the internally generated system assumptions and code documentation.

This report is intentionally a comprehensive technical draft that can later be reformatted into a final polished submission document.
