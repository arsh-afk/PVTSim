# Assumptions Register

## A-01 — Uniform cell temperature
- Statement: The active PV cell area is represented by a single equivalent temperature.
- Why needed: It allows the electrical and thermal submodels to be coupled with a single scalar temperature state.
- Impact if violated: Temperature gradients would alter cell efficiency, local heat flux, and collector outlet predictions.

## A-02 — Steady-state PVT operation within each time step
- Statement: The collector is treated as quasi-steady within each hourly interval.
- Why needed: The solver operates on a single algebraic balance at each time step.
- Impact if violated: Dynamic transients would be missed and the model would under-predict heat accumulation and lag.

## A-03 — Fixed inlet boundary for the PVT exploratory runner
- Statement: The inlet temperature is reset to a fixed value for each interval rather than dynamically integrating from a loop and tank model.
- Why needed: This keeps the simulation tractable and consistent with the existing proof-of-concept path.
- Impact if violated: The collector loop would not represent realistic recirculation or thermal storage feedback.

## A-04 — Constant fluid properties
- Statement: Fluid heat capacity and density are treated as constant over the operating range.
- Why needed: This simplifies the energy-balance equations and solver implementation.
- Impact if violated: Thermal output could be biased under large temperature swings or varying fluid composition.

## A-05 — Idealized MPP operation
- Statement: The PV output remains at a maximum-power-point efficiency factor of unity unless a user-defined factor is supplied.
- Why needed: It avoids adding a stochastic or empirical MPPT model before the core system is validated.
- Impact if violated: The electrical output could be systematically overestimated.

## A-06 — Soiling treated as a multiplicative correction
- Statement: Dust and surface fouling are represented by a scalar factor rather than a dynamic deposition model.
- Why needed: The project structure already assumes externalized data tables and simple multiplicative corrections.
- Impact if violated: Actual electrical degradation could be misrepresented in high-dust conditions.

## A-07 — Simplified tank stratification
- Statement: Tank behavior is approximated with node-based energy balances and convective mixing rather than a full CFD or multi-layer transient model.
- Why needed: The model must stay explainable and numerically stable within the project scope.
- Impact if violated: The timing of heat delivery and hot-water availability could be materially different.

## A-08 — Water treatment is a decision model rather than a certified plant design
- Statement: The treatment stages represent quality and energy trade-offs, not validated membrane or UV plant engineering.
- Why needed: The current scope is research-level system integration rather than process design approval.
- Impact if violated: Product water quality claims would exceed the evidence available from the simulation.

## A-09 — Weather data are representative rather than calibrated field data
- Statement: The weather series is used as a design-basis profile for Abu Dhabi conditions.
- Why needed: This is the available reproducible input set in the package.
- Impact if violated: True annual yield and load matching could differ from the simulation estimate.

## A-10 — Outputs are exploratory research estimates
- Statement: The numerical outputs are intended for modelling analysis, not certified engineering or safety calculations.
- Why needed: The project documentation explicitly states these are not validated engineering results.
- Impact if violated: The package would be read as a final design specification rather than a transparent research model.
