# Corrected solar-thermal reference specifications

> **Correction:** This file is not a CoolPV/Janghan product datasheet. The
> earlier version incorrectly attributed product claims and a 45°C collector
> outlet limit to a datasheet that is not present in the supplied sources.
> The two supplied papers describe conventional flat-plate (FPC) and evacuated
> tube (ETC) solar-thermal cogeneration systems, not the AquaSolar unglazed
> PVT collector. Their values are useful reference-study data, not verified
> CoolPV specifications or direct replacements for the PVT model inputs.

## What the supplied studies actually specify

| Quantity | 2016 SCMD study | 2017 optimization study | Interpretation |
|---|---|---|---|
| Collector technology | TISUN FM-S 2.55 flat-plate collectors and Sunda SEIDO 1-16 evacuated-tube collectors | FPC and ETC modeled with TRNSYS Types 1b and 71 | Neither paper tests the CoolPV/Janghan unglazed PVT product. |
| FPC collector curve | Intercept efficiency 0.781; first-order coefficient 3.65; second-order coefficient 0.051 (the PDF text extraction loses the superscript in its unit) | Intercept efficiency 0.781; first-order coefficient 3.65 W/(m² K); second-order coefficient 0.015 W/(m² K²) | The second-order values differ between papers; preserve the version-specific value and verify against the cited collector test data before use. |
| ETC collector curve | Intercept efficiency 0.73; first-order coefficient 1.5 W/(m² K); second-order coefficient 0.0054 W/(m² K²) | Intercept efficiency 0.732; first-order coefficient 1.5 W/(m² K); second-order coefficient 0.0054 W/(m² K²) | Study-specific coefficients; not interchangeable with the current PVT `tau_alpha`, `F_R`, and `U_L` without a validated model mapping. |
| Solar-loop flow basis | Manufacturer-recommended 25 L/(h m²) for FPC and 30 L/(h m²) for ETC | Table 1 reports tested 40 and 45 kg/(h m²) for FPC and ETC, while also listing a 25 kg/(h m²) solar-pump maximum | The 2017 table's flow entries are internally inconsistent; do not silently select one or transfer them to the current PVT loop. |
| FPC configuration | Five FPCs installed at 35°; the pilot has a 520 L storage tank. A 5 m² FPC case is analyzed for SDHW. | Optimized single-family SCMD: 12 m² aperture area, 30° tilt, 200 L TES | Different study cases and objectives; not the current 6 m² PVT design. |
| ETC configuration | Three ETCs installed at 15° in the pilot | Optimized single-family SCMD: 9 m² aperture area, 20° tilt, 200 L TES | Different collector and design basis from the current PVT design. |
| DHW temperature | The study reports an average DHW storage temperature of 77°C for one SCMD simulation case. | DHW supply setpoint is 50°C; the collector controller also stops charging when storage exceeds 100°C. | These are tank/supply/control values, not a 50–70°C collector-outlet target or a collector fluid maximum. |
| MD temperature | A 40°C temperature difference is reported for the MD system in the simulated case. | MD is modeled separately and uses heat from the storage/heat-exchanger subsystem. | This is not a collector outlet setpoint. |
| Seasonal/annual efficiency | Average FPC collector efficiency of 40% is reported for the SCMD study. | Annual FPC/ETC collector efficiencies of 45%/60% are reported for the optimized study. | System-level study results, not guaranteed single-module efficiencies. |

The 2016 study also reports optimized single-family collector areas of 12.7 m²
for FPC and 9.3 m² for ETC, with an FPC tilt of 35° and 300 L TES. The later
2017 study reports 12 m² FPC or 9 m² ETC, 30°/20° tilt, and 200 L TES for its
optimized single-family cases. These are separate study results, not a single
combined specification.

## Temperature claims and the current PVT model

Neither paper specifies a 50–70°C collector-fluid outlet operating band, nor
does either provide a maximum collector outlet or stagnation temperature for
the current PVT collector. The 50°C value in the 2017 paper is the DHW supply
setpoint. The 77°C value in the 2016 paper is an average tank temperature for
one simulated system case. The 100°C threshold is a high-storage-temperature
pump/controller cutout. None is a substantiated collector-outlet limit.

Consequently, `pvt_th.T_fluid_max` is intentionally left unset and in draft
status until a manufacturer limit, test result, or explicitly approved model
limit is provided. The PVT-only run requires this input; do not raise it to
70°C merely to reach a desired outlet temperature. The existing 6 m² area,
40 kg/h total flow, `tau_alpha = 0.50`, and `U_L = 12 W/(m² K)` remain the
AquaSolar design-basis assumptions and are not values established by these
two studies. The heat-removal factor is also an exploratory assumption.

## References

1. Uday Kumar, N. T., and Andrew Martin. “Simulation and Economic Analysis of
   Solar Thermal Cogeneration System for Production of Heat and Pure Water
   using Membrane Distillation.” *International Journal of Thermal and
   Environmental Engineering*, 11(1), 33–39 (2016).
   [Supplied PDF](../Simulation-and-Economic-Analysis-of-Solar-Thermal-Cogeneration-System-for-Production-of-Heat-and-Pure-Water-using-Membrane-Distillation.pdf);
   [DOI: 10.5383/ijtee.11.01.005](https://doi.org/10.5383/ijtee.11.01.005).
   See especially pp. 34–37.
2. Kumar, N. T. U., and A. Martin. “Techno-economic optimization of solar
   thermal integrated membrane distillation for cogeneration of heat and pure
   water.” *Desalination and Water Treatment*, 98, 16–30 (2017).
   [Supplied PDF](../1-s2.0-S1944398624128810-main.pdf);
   [DOI: 10.5004/dwt.2017.21615](https://doi.org/10.5004/dwt.2017.21615).
   See especially pp. 19 and 23–28.
