# Model Validation and Reproducibility

## Scope
The current package is best read as a reproducible research model rather than a fully field-calibrated engineering design. The validation objective is therefore to confirm that the numerical structure is consistent, the solver converges, the inputs are internally coherent, and the generated outputs are reproducible on a clean run.

## Numerical checks
- The PVT bracketed solver is applied to the collector outlet temperature and converges when the residual crosses the specified tolerance.
- The key equations implement consistent units and temperature definitions across the electrical and thermal balances.
- Input validation checks the parameter registry, weather contract, and required fields before execution.

## Reproducibility check
The packaged scenario `carnot-demo` was produced with the project code and the repository weather file (`inputs/timeseries/weather.csv`, Ras Al Khaimah International Airport TMYx profile). The generated reference result files are retained at `outputs/pvt_only/carnot-demo.csv` and `outputs/pvt_only/carnot-demo.summary.json`, and can be regenerated on demand with:

```bash
python -m aquasolar run carnot-demo --weather inputs/timeseries/weather.csv
```

The reference simulation yields **2,143.27 kWh** electrical output (`M-PV-01`) and **3,559.71 kWh** useful thermal energy (`M-TH-01`) across 8,760 hourly time steps with 0 nonconverged steps.

## Model Scope, Equations, and Provenance Notes
- **PVT Configuration and Active Equations:** The runnable model path executes an exploratory fixed-inlet PVT calculation (`pvt_only`). When `soiling.mode = none`, the soiling multiplier is 1.0 (no soiling derate applied). When `iam_model = none`, incident angle modifier correction is unity.
- **Solver Upper Bound (`pvt_th.T_fluid_max`):** 358.15 K (85 °C) is sourced from the solar-loop high-temperature pump cut-out specified in `AquaSolar_TRNSYS_Master_Direction.md#6.2`. It is used as a numerical bisection solver upper bound reflecting system operational limits, not as a physical collector stagnation temperature.
- **Fixed-Inlet Assumption Limitation:** The exploratory PVT runner evaluates collector performance at a representative fixed inlet temperature (`pvt_th.demo_inlet_temperature` = 293.15 K / 20 °C). Full dynamic tank feedback, DHW loop draw, electrical-bus dispatch, and water treatment are modular standalone implementations and are not integrated into an end-to-end runnable loop in this exploratory runner.

## Interpretation
The model demonstrates numerical feasibility under Ras Al Khaimah / UAE weather conditions. It should not be treated as a certified design result until additional sensor data, calibration, and validation against measured site performance are available.
