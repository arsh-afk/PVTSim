# Data Sources and Provenance

## Weather data
- Source: Abu Dhabi weather profile included in `inputs/timeseries/weather.csv`
- Metadata: `inputs/timeseries/weather.meta.yaml`
- Use: hourly solar and ambient inputs for the PVT runner

## Parameter files
The following YAML files define the system assumptions and default operating parameters:
- `inputs/parameters/site.yaml`
- `inputs/parameters/pvt_thermal.yaml`
- `inputs/parameters/pvt_electrical.yaml`
- `inputs/parameters/tank.yaml`
- `inputs/parameters/electrical_system.yaml`
- `inputs/parameters/economics.yaml`
- `inputs/parameters/mnt_spec.yaml`
- `inputs/parameters/collector_loop.yaml`
- `inputs/parameters/constants.yaml`

## Provenance note
The repository keeps measured, literature-derived, and assumption-based values separated in the parameter registry and provenance folders. This is important because the project intentionally distinguishes “seeded research defaults” from validated engineering numbers.
