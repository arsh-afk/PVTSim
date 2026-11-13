# Accepted Unit Strings for AquaSolar Living

Maps each `quantity_kind` (from `docs/quantity_kinds.yaml`) to the unit
strings the unit library (Pint) accepts for that kind.

This file is approved at Gate 0 and locked. Changes require a new change request.

---

## Accepted Units by Quantity Kind

| quantity_kind | accepted_unit_strings | SI base unit |
|---|---|---|
| `density` | `kg/m3`, `kg*m**-3`, `gram/liter`, `g/L`, `g/l`, `lb/ft3`, `pound/cubic_foot` | kg/m³ |
| `specific_heat` | `J/(kg*K)`, `J/kg/K`, `joule/(kilogram*kelvin)`, `cal/(g*K)`, `kcal/(kg*K)` | J/(kg·K) |
| `text` | *(any non-empty string)* | — |
| `angle` | `deg`, `degree`, `degrees`, `rad`, `radian`, `radians`, `arcmin`, `arcminute`, `arcsec`, `arcsecond` | rad |
| `length` | `m`, `meter`, `meters`, `km`, `kilometer`, `cm`, `centimeter`, `mm`, `millimeter`, `in`, `inch`, `ft`, `foot`, `mi`, `mile` | m |
| `time` | `s`, `second`, `seconds`, `min`, `minute`, `minutes`, `h`, `hour`, `hours`, `d`, `day`, `days`, `yr`, `year`, `years`, `ms`, `millisecond` | s |
| `fraction` | *(unitless — omit or use `1`)* | 1 |
| `rate_per_time` | `1/s`, `1/second`, `1/h`, `1/hour`, `1/d`, `1/day`, `1/yr`, `1/year`, `per_second`, `per_year`, `year**-1`, `s**-1` | 1/s |
| `irradiance` | `W/m2`, `watt/meter2`, `W/(m*m)`, `kW/m2`, `kw/m**2` | W/m² |
| `temperature` | `K`, `kelvin`, `C`, `celsius`, `degC`, `deg_C`, `F`, `fahrenheit`, `degF` | K |
| `temperature_difference` | `K`, `kelvin`, `delta_K`, `C`, `celsius`, `delta_C`, `degC`, `deg_C` | K (magnitude only) |
| `flow_mass` | `kg/s`, `kg/second`, `g/s`, `gram/second`, `kg/h`, `kg/hour`, `lb/h`, `pound/hour` | kg/s |
| `flow_volumetric` | `m3/s`, `m**3/s`, `liter/second`, `L/s`, `m3/h`, `m**3/h`, `gal/min`, `gallon/minute`, `L/h` | m³/s |
| `power` | `W`, `watt`, `kW`, `kilowatt`, `MW`, `megawatt`, `mW`, `milliwatt` | W |
| `energy` | `J`, `joule`, `kJ`, `kilojoule`, `MJ`, `megajoule`, `Wh`, `watt_hour`, `kWh`, `kilowatt_hour`, `MWh`, `cal`, `calorie`, `kcal`, `kilocalorie` | J |
| `heat_transfer_coefficient` | `W/(m2*K)`, `watt/(meter**2*kelvin)`, `W/m2/K`, `W*m**-2*K**-1` | W/(m²·K) |
| `thermal_conductance` | `W/K`, `watt/kelvin`, `W/k`, `J/(s*K)`, `W*m*K**-1` | W/K |
| `thermal_conductivity` | `W/(m*K)`, `watt/(meter*kelvin)`, `W/m/K`, `W*m**-1*K**-1` | W/(m·K) |
| `area` | `m2`, `m**2`, `meter2`, `square_meter`, `km2`, `hectare`, `ha`, `ft2`, `sq_ft`, `acre` | m² |
| `area_thermal_resistance` | `m2*K/W`, `kelvin*meter**2/watt`, `K*m2/W`, `m2*K*watt**-1` | K·m²/W |
| `areal_heat_capacity` | `J/(m2*K)`, `joule/(meter**2*kelvin)`, `J*m**-2*K**-1`, `Wh/(m2*K)` | J/(m²·K) |
| `pressure` | `Pa`, `pascal`, `kPa`, `kilopascal`, `MPa`, `megapascal`, `bar`, `mbar`, `atm`, `atmosphere`, `psi`, `pound_force/inch2`, `mmHg`, `torr` | Pa |
| `count` | *(unitless integer)* | 1 |
| `boolean` | *(true/false)* | — |
| `energy_per_volume` | `J/m3`, `joule/meter**3`, `Wh/L`, `wh/liter`, `kJ/m3` | J/m³ |
| `concentration` | `mg/L`, `milligram/liter`, `g/m3`, `gram/meter**3`, `kg/m3`, `ppm`, `ppb`, `ug/L`, `microgram/liter` | kg/m³ (default) |
| `uv_intensity` | `W/m2`, `watt/meter2`, `mW/cm2`, `milliwatt/centimeter**2` | W/m² |
| `uv_dose` | `J/m2`, `joule/meter**2`, `mJ/cm2`, `millijoule/centimeter**2` | J/m² |
| `permeability` | `m/(s*Pa)`, `meter/(second*pascal)`, `LMH/bar`, `liter/(meter2*hour*bar)` | m/(s·Pa) |
| `loading_capacity` | `kg`, `kilogram`, `g`, `gram`, `lb`, `pound` | kg |
| `rate_per_volume` | `1/(m3*s)`, `meter**-3*second**-1`, `1/(L*s)`, `liter**-1*second**-1` | 1/(m³·s) |
| `activation_energy` | `J/(mol*K)`, `joule/(mole*kelvin)`, `kJ/(mol*K)`, `kcal/(mol*K)`, `cal/(mol*K)` | J/(mol·K) |
| `emission_per_energy` | `kg_CO2eq/J`, `g_CO2eq/kWh`, `kg/kWh`, `g/J`, `ton/MWh` | kg/J |
| `emission_per_volume` | `kg_CO2eq/m3`, `g/L`, `g/liter`, `kg/m3` | kg/m³ |
| `currency` | *(any 3-letter ISO 4217 code)* | — |
| `currency_per_time` | `USD/year`, `AED/month`, `USD/s`, `dollars_per_year` | currency/s |
| `currency_per_energy` | `USD/J`, `USD/kWh`, `AED/kWh`, `USD/Wh` | currency/J |
| `currency_per_volume` | `USD/m3`, `USD/L`, `AED/L`, `dollars_per_liter` | currency/m³ |
| `dimensionless` | *(unitless)* | 1 |
| `timestamp` | *(ISO 8601 string with explicit offset, e.g. `2026-01-01T00:00:00+04:00`)* | — |
| `volume` | `m3`, `m**3`, `liter`, `L`, `ml`, `milliliter`, `gal`, `gallon`, `mL` | m³ |
| `mass` | `kg`, `kilogram`, `g`, `gram`, `lb`, `pound`, `mg`, `milligram` | kg |
| `rate_per_temperature` | `1/(K*s)`, `kelvin**-1*second**-1`, `1/(C*s)`, `1/(K*hour)`, `1/K` | 1/(K·s) |

---

## Rules

1. Unit strings are case-insensitive for alphabetic characters (`W/m2` == `w/m2`).
2. Exponent notation accepts both `**` and `/` syntax (`m2` or `m**2` or `m^-2`).
3. Compound units must be unambiguous: `J/(kg*K)` is accepted; `J/kg*K` is rejected
   (could mean `(J/kg)*K`).
4. The `temperature` and `temperature_difference` kinds share accepted unit strings
   (K, C, degC). The distinction is enforced by the caller using `quantity_kind`.
5. Currency codes must be exactly 3 uppercase ASCII letters (ISO 4217).

---

## References

- SI Brochure, 9th edition, Bureau International des Poids et Mesures (BIPM)
- ISO 80000-3:2019 — Quantities and units — Part 3: Space and time
- ISO 80000-5:2019 — Quantities and units — Part 5: Energy, heat, work, power
