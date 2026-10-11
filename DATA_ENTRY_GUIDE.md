# AquaSolar Living: Data Entry Guide

Generated from the same definitions as the template files, so the ids below match the files exactly.

## Rules that apply to every input

1. Nothing in the simulation has a default. Every required item must be filled and set to `confirmed`, or the run stops and names the item.
2. Fill parameter files in `inputs/parameters/` (YAML). Fill data files in `inputs/timeseries/` and `inputs/tables/` (CSV plus a `.meta.yaml` with the same name).
3. Put the evidence for each value in `inputs/provenance/` and name the file in `source_ref`.
4. Units: give a unit string for every value in the parameter files, and for every column in the meta files (or a unit column in the CSV where one exists). Temperature differences use the `temperature_difference` kind, not an absolute temperature.
5. Timestamps: ISO 8601 with an explicit UTC offset, written as `<YYYY-MM-DDThh:mm:ss+hh:mm>`. Never mix time zones in one file.
6. CSV: UTF-8, comma delimiter, period decimal point, one header row, no thousands separators, empty cell for missing (never 0, -999 or text).
7. Categorical entries: `value` must equal one of `allowed_values` exactly.
8. Conditional entries: if `required_when` is false for your setup, set `status: not_applicable`.
9. The agent never edits your values. It writes errors that quote the file, the id or row, what is wrong and what format it expected.
10. Run `python -m aquasolar check-inputs` at any time. It rewrites `inputs/STATUS.md` with what is missing, in the order the phases need it.

## Where each input goes

| Folder | What goes there | Format |
| --- | --- | --- |
| `inputs/parameters/` | Single values and model choices | YAML, one file per subsystem |
| `inputs/timeseries/` | Anything indexed by time | CSV + `.meta.yaml` |
| `inputs/tables/` | Lists, curves and lookup tables | CSV + `.meta.yaml` |
| `inputs/provenance/` | Evidence for values | Any file; referenced by name |
| `inputs/candidates/` | Agent-proposed values (never used) | Agent writes, you review |
| `inputs/approvals/` | Your gate sign-offs | Markdown, copy of the template |

## Parameter files

### `inputs/parameters/constants.yaml`: Physical constants and reference fluid properties

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `const.rho_water_ref` | density | 4 | numerics.property_model == constant | Reference density of liquid water, used only if property_model is constant |
| `const.cp_water_ref` | specific_heat | 4 | numerics.property_model == constant | Reference specific heat of liquid water, used only if property_model is constant |
| `const.property_source` | text | 4 | numerics.property_model == temperature_dependent | Name of property source used when property_model is temperature_dependent |

### `inputs/parameters/site.yaml`: Location, orientation, soiling

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `site.latitude` | angle | 3 | always | Site latitude, decimal degrees, north positive |
| `site.longitude` | angle | 3 | always | Site longitude, decimal degrees, east positive |
| `site.elevation` | length | 3 | always | Site elevation above sea level |
| `site.timezone` | text | 1 | always | IANA time zone name of the site |
| `site.collector_tilt` | angle | 3 | always | Collector tilt from horizontal |
| `site.collector_azimuth` | angle | 3 | always | Collector azimuth, convention stated in notes |
| `site.azimuth_convention` | categorical | 3 | always | Azimuth convention used for the value above |
| `site.ground_albedo` | fraction | 3 | always | Ground reflectance for transposition |
| `site.shading_loss_factor` | fraction | 3 | always | Fractional irradiance loss from fixed shading |
| `soiling.mode` | categorical | 3 | always | How soiling is supplied |
| `soiling.loss_rate` | rate_per_time | 3 | soiling.mode == linear_rate_with_cleaning | Fractional loss accumulated per unit time between cleanings |
| `soiling.max_loss` | fraction | 3 | soiling.mode == linear_rate_with_cleaning | Upper bound on fractional soiling loss |
| `soiling.clean_recovery` | fraction | 3 | soiling.mode == linear_rate_with_cleaning | Fraction of accumulated soiling removed by a cleaning or rain event |

### `inputs/parameters/pvt_electrical.yaml`: PV side of the PVT collector

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `pvt_el.eta_ref` | fraction | 3 | always | Electrical efficiency at reference conditions |
| `pvt_el.T_ref` | temperature | 3 | always | Cell temperature at reference conditions |
| `pvt_el.G_ref` | irradiance | 3 | always | Irradiance at reference conditions |
| `pvt_el.beta` | rate_per_temperature | 3 | always | Temperature coefficient of efficiency, relative per temperature |
| `pvt_el.irradiance_model` | categorical | 3 | always | Efficiency dependence on irradiance |
| `pvt_el.iam_model` | categorical | 3 | always | Incidence-angle modifier model |
| `pvt_el.inverter_efficiency` | fraction | 7 | always | Inverter or power electronics efficiency (use the value for the actual device) |
| `pvt_el.module_count` | count | 3 | always | Number of modules in the array |
| `pvt_el.mpp_assumption` | categorical | 3 | always | How maximum power point operation is handled |
| `pvt_el.mpp_efficiency_factor` | fraction | 3 | pvt_el.mpp_assumption == user_efficiency_factor | Tracking efficiency factor |

### `inputs/parameters/pvt_thermal.yaml`: Thermal side of the PVT collector

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `pvt_th.collector_area` | area | 3 | always | Collector area used for the thermal and electrical calculation (state aperture or gross in notes) |
| `pvt_th.area_basis` | categorical | 3 | always | Which area the value above refers to |
| `pvt_th.collector_type` | categorical | 3 | always | Collector construction |
| `pvt_th.thermal_model` | categorical | 3 | always | Collector thermal model |
| `pvt_th.tau_alpha` | fraction | 3 | always | Effective transmittance-absorptance product |
| `pvt_th.F_R` | fraction | 3 | pvt_th.thermal_model == steady_state_hottel_whillier_form | Collector heat-removal factor |
| `pvt_th.U_L` | heat_transfer_coefficient | 3 | always | Overall heat-loss coefficient |
| `pvt_th.U_L_wind_dependence` | categorical | 3 | always | Wind dependence of the loss coefficient |
| `pvt_th.R_cell_fluid` | area_thermal_resistance | 3 | always | Thermal resistance per area between cell and mean fluid |
| `pvt_th.thermal_capacitance` | areal_heat_capacity | 3 | pvt_th.thermal_model == quasi_dynamic | Effective thermal capacitance per area |
| `pvt_th.flow_min` | flow_mass | 5 | always | Minimum permitted collector flow |
| `pvt_th.flow_max` | flow_mass | 5 | always | Maximum permitted collector flow |
| `pvt_th.T_fluid_max` | temperature | 5 | always | Maximum permitted collector fluid temperature (stagnation or protection limit) |
| `pvt_th.pv_only_reference_model` | categorical | 3 | always | How the PV-only reference cell temperature is computed for the cooling-benefit comparison |

### `inputs/parameters/collector_loop.yaml`: Pump, fluid and controller for the collector-to-tank loop

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `loop.fluid_type` | text | 5 | always | Working fluid of the collector loop |
| `loop.fluid_density` | density | 5 | always | Loop fluid density |
| `loop.fluid_cp` | specific_heat | 5 | always | Loop fluid specific heat |
| `loop.flow_mode` | categorical | 5 | always | Flow control |
| `loop.mass_flow_fixed` | flow_mass | 5 | loop.flow_mode == fixed | Mass flow when pump is on |
| `loop.pump_power_model` | categorical | 5 | always | Pump electrical power model |
| `loop.pump_power_fixed` | power | 5 | loop.pump_power_model == fixed_when_on | Pump electrical power when on |
| `loop.pump_efficiency` | fraction | 5 | loop.pump_power_model == hydraulic_power_over_efficiency | Pump overall efficiency |
| `loop.pressure_drop` | pressure | 5 | loop.pump_power_model == hydraulic_power_over_efficiency | Loop pressure drop at operating flow |
| `loop.pipe_loss_UA` | thermal_conductance | 5 | always | Pipe heat-loss conductance, supply plus return |
| `loop.pipe_ambient_mode` | categorical | 5 | always | Ambient used for pipe losses |
| `loop.pipe_ambient_value` | temperature | 5 | loop.pipe_ambient_mode == constant_value | Constant pipe ambient temperature |
| `loop.hx_present` | boolean | 5 | always | Heat exchanger between loop and tank |
| `loop.hx_effectiveness` | fraction | 5 | loop.hx_present == true | Heat exchanger effectiveness |
| `loop.ctrl_dT_on` | temperature_difference | 5 | always | Temperature difference at which the pump turns on |
| `loop.ctrl_dT_off` | temperature_difference | 5 | always | Temperature difference at which the pump turns off |
| `loop.ctrl_T_tank_max` | temperature | 5 | always | Tank temperature above which charging stops |
| `loop.ctrl_min_irradiance` | irradiance | 5 | loop.ctrl_use_min_irradiance == true | Minimum irradiance for pump operation, if used |
| `loop.ctrl_use_min_irradiance` | boolean | 5 | always | Whether an irradiance condition is part of pump control |
| `loop.ctrl_sensor_nodes` | text | 5 | always | Tank node and collector point the controller reads (text) |
| `loop.ctrl_min_dwell` | time | 5 | always | Minimum on or off time |

### `inputs/parameters/tank.yaml`: 150 L thermal storage tank and hot-water draw

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `tank.volume` | volume | 4 | always | Water volume of the tank |
| `tank.height` | length | 4 | always | Internal height |
| `tank.diameter` | length | 4 | always | Internal diameter |
| `tank.node_count` | count | 4 | always | Number of vertical nodes (one gives the single-node limiting case) |
| `tank.UA_total` | thermal_conductance | 4 | always | Total standby loss conductance to ambient |
| `tank.loss_distribution` | categorical | 4 | always | How standby loss is distributed over nodes |
| `tank.ambient_mode` | categorical | 4 | always | Ambient temperature around the tank |
| `tank.ambient_constant` | temperature | 4 | tank.ambient_mode == constant_value | Constant tank ambient temperature |
| `tank.charge_inlet_node` | count | 4 | always | Node index receiving heated loop fluid |
| `tank.charge_outlet_node` | count | 4 | always | Node index supplying loop return to collector |
| `tank.charge_method` | categorical | 4 | always | How loop heat enters the tank |
| `tank.coil_effectiveness` | fraction | 4 | tank.charge_method != direct_fluid_exchange | Effectiveness of internal coil or external exchanger |
| `tank.draw_outlet_node` | count | 4 | always | Node index of hot-water outlet |
| `tank.makeup_inlet_node` | count | 4 | always | Node index of cold make-up inlet |
| `tank.conduction_model` | categorical | 4 | tank.node_count != 1 | Inter-node conduction treatment |
| `tank.effective_conductivity` | thermal_conductivity | 4 | tank.conduction_model == effective_conductivity | Effective axial conductivity including destratification effects |
| `tank.mixing_model` | categorical | 4 | tank.node_count != 1 | Buoyancy mixing treatment |
| `tank.aux_present` | boolean | 4 | always | Backup heater present |
| `tank.aux_power` | power | 4 | tank.aux_present == true | Backup heater electrical power |
| `tank.aux_efficiency` | fraction | 4 | tank.aux_present == true | Backup heater conversion efficiency |
| `tank.aux_setpoint` | temperature | 4 | tank.aux_present == true | Backup heater thermostat set-point |
| `tank.aux_node` | count | 4 | tank.aux_present == true | Node index where backup heat is added |
| `tank.delivery_temp_min` | temperature | 4 | always | Minimum acceptable hot-water delivery temperature |
| `tank.stored_temp_min_safety` | temperature | 4 | tank.safety_policy == true | Minimum stored temperature required by your hot-water safety policy, if any |
| `tank.safety_policy` | boolean | 4 | always | Whether a minimum stored temperature policy applies |

### `inputs/parameters/electrical_system.yaml`: Electrical configuration and parasitic loads

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `elec.configuration` | categorical | 7 | always | System configuration |
| `elec.export_allowed` | boolean | 7 | elec.configuration in grid_connected,grid_connected_with_battery | Surplus electricity may be exported |
| `elec.battery_capacity` | energy | 7 | elec.configuration in grid_connected_with_battery,off_grid_with_battery | Usable battery energy capacity |
| `elec.battery_round_trip_eff` | fraction | 7 | elec.configuration in grid_connected_with_battery,off_grid_with_battery | Battery round-trip efficiency |
| `elec.battery_min_soc` | fraction | 7 | elec.configuration in grid_connected_with_battery,off_grid_with_battery | Minimum permitted state of charge |
| `elec.battery_max_power` | power | 7 | elec.configuration in grid_connected_with_battery,off_grid_with_battery | Maximum battery charge or discharge power |
| `elec.controller_power` | power | 7 | always | Controller electrical power draw |
| `elec.sensor_power_total` | power | 7 | always | Total sensor electrical power draw |
| `elec.comms_power` | power | 7 | always | Communications and data-logging power draw |
| `elec.inverter_standby_power` | power | 7 | always | Inverter standby power draw |
| `elec.priority_order` | text | 7 | always | Order in which PV output serves loads (text list) |

### `inputs/parameters/treatment_components.yaml`: Per-stage hardware data for the treatment train

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `tc.pathway_stage_lists` | text | 6 | always | Stage lists for pathways A, B, C as ordered ids from the allowed set (text) |
| `tc.rated_product_flow` | flow_volumetric | 6 | always | Product flow at which the unit runs when it is on, per pathway basis stated in notes; demand above it is unmet |
| `tc.feed_pressure_available` | pressure | 6 | always | Pressure available at the unit inlet |
| `tc.booster_pump_efficiency` | fraction | 6 | tc.booster_present == true | Booster pump overall efficiency, if a booster is used |
| `tc.booster_present` | boolean | 6 | always | Whether a booster pump is used for any pathway |
| `tc.sediment.pressure_drop_model` | categorical | 6 | always | Pressure drop treatment for the sediment filter |
| `tc.sediment.capacity` | loading_capacity | 6 | always | Loading capacity before replacement (basis in notes) |
| `tc.sediment.replacement_rule` | categorical | 6 | always | Replacement trigger |
| `tc.carbon.pressure_drop_model` | categorical | 6 | always | Pressure drop treatment for activated carbon |
| `tc.carbon.capacity` | loading_capacity | 6 | always | Loading capacity before breakthrough or replacement |
| `tc.carbon.replacement_rule` | categorical | 6 | always | Replacement trigger |
| `tc.carbon.disinfectant_removal_model` | categorical | 6 | always | How residual disinfectant removal is handled |
| `tc.uf.pressure_drop_model` | categorical | 6 | always | Pressure drop treatment for ultrafiltration |
| `tc.uf.recovery` | fraction | 6 | always | Ultrafiltration water recovery |
| `tc.uf.backwash_volume` | volume | 6 | always | Volume used per backwash |
| `tc.uf.backwash_interval` | text | 6 | always | Time or volume between backwashes (basis in notes) |
| `tc.uf.backwash_energy` | energy | 6 | always | Electrical energy per backwash |
| `tc.uf.replacement_rule` | categorical | 6 | always | Replacement trigger |
| `tc.uf.capacity` | loading_capacity | 6 | always | Capacity before replacement (basis in notes) |
| `tc.membrane.type` | categorical | 6 | always | Membrane class used in pathway C |
| `tc.membrane.recovery` | fraction | 6 | always | Water recovery of the membrane stage |
| `tc.membrane.operating_pressure` | pressure | 6 | always | Operating pressure at the membrane |
| `tc.membrane.pump_efficiency` | fraction | 6 | always | High-pressure pump overall efficiency |
| `tc.membrane.flux_model` | categorical | 6 | always | Flux model |
| `tc.membrane.water_permeability` | permeability | 6 | tc.membrane.flux_model == solution_diffusion_user_parameters | Water permeability coefficient |
| `tc.membrane.area` | area | 6 | tc.membrane.flux_model != constant_recovery_only | Membrane area |
| `tc.membrane.temp_correction` | categorical | 6 | always | Temperature correction of flux |
| `tc.membrane.fouling_model` | categorical | 6 | always | Fouling treatment |
| `tc.membrane.fouling_rate` | rate_per_volume | 6 | tc.membrane.fouling_model == user_rate_per_volume | Permeability decline per unit throughput |
| `tc.membrane.replacement_rule` | categorical | 6 | always | Replacement trigger |
| `tc.membrane.capacity` | loading_capacity | 6 | always | Capacity before replacement (basis in notes) |
| `tc.membrane.pretreatment_note` | text | 6 | always | What pretreatment precedes the membrane in pathway C (text) |
| `tc.remin.enabled` | boolean | 6 | always | Remineralization stage present in pathway C |
| `tc.remin.method` | text | 6 | tc.remin.enabled == true | Remineralization method (text) |
| `tc.remin.energy_per_volume` | energy_per_volume | 6 | tc.remin.enabled == true | Electrical energy per volume for remineralization |
| `tc.uv.lamp_power` | power | 6 | always | UV lamp electrical power when on |
| `tc.uv.ballast_efficiency` | fraction | 6 | tc.uv.power_basis == lamp_side | Ballast efficiency, if the lamp power above is lamp-side |
| `tc.uv.power_basis` | categorical | 6 | always | Whether lamp power is measured at the wall or the lamp |
| `tc.uv.operation_policy` | categorical | 6 | always | Lamp operation policy |
| `tc.uv.warmup_time` | time | 6 | tc.uv.operation_policy == on_with_flow_plus_warmup | Warm-up time before output is valid |
| `tc.uv.lamp_life` | time | 6 | always | Rated lamp operating life |
| `tc.uv.dose_accounting` | boolean | 6 | always | Whether UV dose is computed |
| `tc.uv.transmittance_source` | categorical | 6 | tc.uv.dose_accounting == true | Source of UV transmittance of the water |
| `tc.uv.lamp_intensity` | uv_intensity | 6 | tc.uv.dose_accounting == true | Effective UV intensity in the reactor |
| `tc.uv.reactor_volume` | volume | 6 | tc.uv.dose_accounting == true | Reactor irradiated volume |
| `tc.uv.target_dose` | uv_dose | 6 | tc.uv.dose_accounting == true | Target dose for the dose check |
| `tc.conductivity_to_tds_factor` | dimensionless | 6 | tc.use_conductivity_to_tds == true | Conversion factor if TDS is derived from conductivity |
| `tc.use_conductivity_to_tds` | boolean | 6 | always | Whether TDS is derived from conductivity |
| `tc.sensor_cost_and_power_note` | text | 6 | always | Anything not covered above that draws power (text) |

### `inputs/parameters/storage_quality.yaml`: Storage-tank water quality and disinfectant decay

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `sq.enabled` | boolean | 6 | always | Run the storage-quality module |
| `sq.villa_storage_volume` | volume | 6 | sq.enabled == true | Villa storage tank volume |
| `sq.mixing_model` | categorical | 6 | sq.enabled == true | Storage mixing treatment |
| `sq.disinfectant_species_id` | text | 6 | sq.enabled == true | Species id (from the species registry) that decays |
| `sq.decay_model` | categorical | 6 | sq.enabled == true | Decay model |
| `sq.k_ref` | rate_per_time | 6 | sq.decay_model in first_order_arrhenius,first_order_constant | First-order decay rate at reference temperature |
| `sq.T_ref` | temperature | 6 | sq.decay_model == first_order_arrhenius | Reference temperature for the decay rate |
| `sq.temp_coefficient` | activation_energy | 6 | sq.decay_model == first_order_arrhenius | Temperature sensitivity of decay (activation energy or equivalent, basis in notes) |
| `sq.wall_decay` | rate_per_time | 6 | sq.wall_decay_enabled == true | Wall decay rate, if modelled |
| `sq.wall_decay_enabled` | boolean | 6 | sq.enabled == true | Whether wall decay is modelled |
| `sq.storage_temperature_mode` | categorical | 6 | sq.enabled == true | Source of storage water temperature |
| `sq.storage_temperature_constant` | temperature | 6 | sq.storage_temperature_mode == constant_value | Constant storage temperature |
| `sq.initial_concentration` | concentration | 6 | sq.enabled == true | Initial disinfectant concentration in storage |
| `sq.treated_storage_enabled` | boolean | 6 | always | Model storage of treated water downstream of the unit |
| `sq.treated_storage_volume` | volume | 6 | sq.treated_storage_enabled == true | Treated-water storage volume |
| `sq.treated_decay_note` | text | 6 | sq.treated_storage_enabled == true | Which decay settings apply to treated water (text) |

### `inputs/parameters/mnt_spec.yaml`: Minimum Necessary Treatment definition

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `mnt.pathway_ids` | text | 7 | always | Pathway ids in the set (text list) |
| `mnt.intensity_order` | text | 7 | always | Pathway ids ordered from lowest to highest intensity (text list) |
| `mnt.objective_mode` | categorical | 7 | always | How the objective J ranks feasible pathways |
| `mnt.weight_energy` | dimensionless | 7 | mnt.objective_mode == weighted_sum | Weight on specific energy |
| `mnt.weight_reject` | dimensionless | 7 | mnt.objective_mode == weighted_sum | Weight on reject fraction |
| `mnt.weight_consumable` | dimensionless | 7 | mnt.objective_mode == weighted_sum | Weight on consumable use |
| `mnt.lexicographic_order` | text | 7 | mnt.objective_mode == lexicographic | Order of criteria (text list) |
| `mnt.normalization` | categorical | 7 | mnt.objective_mode == weighted_sum | How terms are normalized in J |
| `mnt.decision_interval` | time | 7 | always | How often the pathway can be re-selected |
| `mnt.controller_delay` | time | 7 | always | Delay between a sensor reading and a pathway change |
| `mnt.infeasible_policy` | categorical | 7 | always | What to do when no pathway meets the limits |

### `inputs/parameters/economics.yaml`: Costs, prices and financial settings

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `econ.currency` | text | 9 | always | Currency code |
| `econ.horizon` | time | 9 | always | Analysis horizon |
| `econ.discount_rate` | rate_per_time | 9 | always | Discount rate per year |
| `econ.escalation_electricity` | rate_per_time | 9 | always | Electricity price escalation per year |
| `econ.escalation_water` | rate_per_time | 9 | always | Water and bottled-water price escalation per year |
| `econ.escalation_other` | rate_per_time | 9 | always | Escalation for other costs per year |
| `econ.capex_pvt` | currency | 9 | always | Capital cost of the PVT system as used for this villa |
| `econ.capex_tank` | currency | 9 | always | Capital cost of the tank and loop |
| `econ.capex_treatment` | currency | 9 | always | Capital cost of the treatment unit per pathway (see table pathway_costs) |
| `econ.capex_monitoring` | currency | 9 | always | Capital cost of sensors, controller and data platform |
| `econ.installation` | currency | 9 | always | Installation cost |
| `econ.annual_maintenance` | currency_per_time | 9 | always | Annual maintenance cost |
| `econ.monitoring_service_cost` | currency_per_time | 9 | always | Annual cost of the monitoring service |
| `econ.pvt_degradation` | rate_per_time | 9 | always | Annual electrical degradation rate |
| `econ.pvt_lifetime` | time | 9 | always | Service life of the PVT system |
| `econ.tank_lifetime` | time | 9 | always | Service life of the tank |
| `econ.residual_value` | currency | 9 | always | Residual value at the end of the horizon |
| `econ.electricity_value_basis` | categorical | 9 | always | How PV electricity is valued |
| `econ.displaced_heat_source` | categorical | 9 | always | What the stored heat displaces |
| `econ.displaced_heater_efficiency` | fraction | 9 | always | Efficiency of the displaced water heater |
| `econ.displaced_fuel_price` | currency_per_energy | 9 | always | Price of the displaced energy per energy unit |
| `econ.bottled_price` | currency_per_volume | 9 | always | Price of bottled drinking water per volume |
| `econ.bottled_replaced_fraction` | fraction | 9 | always | Fraction of the drinking-water demand that bottled water currently supplies |
| `econ.municipal_water_price` | currency_per_volume | 9 | always | Municipal water price per volume |
| `econ.reject_disposal_price` | currency_per_volume | 9 | always | Cost per volume of reject water, if any |
| `econ.baseline_ro_capex` | currency | 9 | always | Capital cost of the conventional full-RO comparator |
| `econ.baseline_ro_power` | text | 9 | always | Electrical power or energy per volume of the comparator (basis in notes) |
| `econ.baseline_ro_recovery` | fraction | 9 | always | Water recovery of the comparator |
| `econ.baseline_ro_consumable_cost` | currency_per_time | 9 | always | Annual consumable cost of the comparator |
| `econ.baseline_ro_lifetime` | time | 9 | always | Service life of the comparator |

### `inputs/parameters/environment.yaml`: Environmental accounting inputs

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `env.system_boundary` | text | 9 | always | Written system boundary for environmental indicators (text) |
| `env.bottle_volume` | volume | 9 | always | Volume of one bottled-water unit |
| `env.bottle_mass` | mass | 9 | always | Mass of packaging per bottled unit |
| `env.grid_emission_factor` | emission_per_energy | 9 | always | Emission factor of grid electricity |
| `env.fuel_emission_factor` | emission_per_energy | 9 | always | Emission factor of the displaced heating fuel |
| `env.transport_emission_per_volume` | emission_per_volume | 9 | env.include_transport == true | Transport emissions per volume of bottled water, if included |
| `env.include_transport` | boolean | 9 | always | Include transport emissions |

### `inputs/parameters/numerics.yaml`: Numerical settings and run control

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `numerics.time_step` | time | 0 | always | Simulation time step |
| `numerics.start` | timestamp | 1 | always | Simulation start (timestamp in site time zone) |
| `numerics.end` | timestamp | 1 | always | Simulation end (timestamp in site time zone) |
| `numerics.spin_up` | time | 4 | always | Spin-up period discarded from results |
| `numerics.property_model` | categorical | 4 | always | Fluid property treatment |
| `numerics.loop_solver` | categorical | 5 | always | Method for the PVT algebraic loop |
| `numerics.loop_tolerance` | dimensionless | 5 | always | Convergence tolerance of the loop solve (basis in notes) |
| `numerics.loop_max_iterations` | count | 5 | always | Maximum iterations of the loop solve |
| `numerics.tank_scheme` | categorical | 4 | always | Tank time integration scheme |
| `numerics.tank_substeps` | count | 4 | numerics.tank_scheme == substepped_explicit | Substeps per time step |
| `numerics.initial_tank_temperature` | temperature | 4 | always | Initial tank temperature per node (single value, or reference an initial-profile table in notes) |
| `numerics.initial_storage_state` | text | 6 | always | Initial state of consumables, loading and wear (text pointing to a table, or zero meaning new) |
| `numerics.master_seed` | count | 0 | always | Master random seed |
| `numerics.ensemble_size` | count | 9 | always | Monte Carlo ensemble size |
| `numerics.mc_stopping_rule` | categorical | 9 | always | Stopping rule for ensemble statistics |
| `numerics.mc_stopping_tolerance` | dimensionless | 9 | numerics.mc_stopping_rule != fixed_size | Tolerance of the stopping rule |
| `numerics.sensitivity_method` | categorical | 9 | always | Global sensitivity method |
| `numerics.output_interval` | time | 8 | always | Interval of logged output |
| `numerics.gap_policy` | categorical | 1 | always | Treatment of missing weather and demand data |
| `numerics.gap_max_duration` | time | 1 | numerics.gap_policy == linear_interpolate_up_to_max_gap | Maximum gap bridged by interpolation |

### `inputs/parameters/verification.yaml`: Tolerances and acceptance limits fixed before any comparison

| Id | Kind | Needed by phase | Required when | Description |
| --- | --- | --- | --- | --- |
| `ver.energy_balance_tol_abs` | energy | 3 | always | Absolute energy balance residual tolerance per step |
| `ver.energy_balance_tol_rel` | fraction | 3 | always | Relative energy balance residual tolerance (basis in notes) |
| `ver.mass_balance_tol_rel` | fraction | 6 | always | Relative mass and solute balance tolerance |
| `ver.analytical_test_tol_rel` | fraction | 3 | always | Relative tolerance for analytical benchmark tests |
| `ver.timestep_convergence_tol` | fraction | 8 | always | Largest acceptable change in a headline metric on halving the step |
| `ver.nodecount_convergence_tol` | fraction | 4 | always | Largest acceptable change in a headline metric on doubling node count |
| `ver.calibration_period` | text | 3 | always | Date range used for calibration (text: start and end timestamps) |
| `ver.validation_period` | text | 3 | always | Date range held out for validation (text: start and end timestamps) |
| `ver.calibration_parameter_list` | text | 3 | always | Parameter ids allowed to be calibrated (text list; others stay fixed) |

## Time-series files

### `inputs/timeseries/weather.csv`: Site weather at the simulation interval or finer (needed by phase 1)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `ghi` | yes | Global horizontal irradiance |
| `dni` | no | Direct normal irradiance |
| `dhi` | no | Diffuse horizontal irradiance |
| `poa_irradiance` | no | Measured plane-of-array irradiance, if you have it |
| `t_ambient` | yes | Ambient air temperature |
| `wind_speed` | yes | Wind speed at the height stated in the meta file |
| `relative_humidity` | no | Needed only if an approved model uses it |
| `cloud_cover` | no | Needed only if an approved model uses it |
| `qc_flag` | no | Quality code from your own scheme, defined in the meta file |

Also fill `inputs/timeseries/weather.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/soiling_events.csv`: Cleaning or rain events, or a soiling factor series (needed by phase 3)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `event_type` | yes | cleaning, rain, or soiling_factor_value |
| `value` | no | Soiling factor if event_type is soiling_factor_value, else leave empty |

Also fill `inputs/timeseries/soiling_events.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/tank_ambient.csv`: Temperature around the tank and storage water temperature, if not constant (needed by phase 4)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `t_tank_ambient` | no | Air temperature around the tank |
| `t_storage_water` | no | Villa storage water temperature |

Also fill `inputs/timeseries/tank_ambient.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/dhw_draw.csv`: Hot-water draw and cold make-up temperature (needed by phase 4)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `draw_volume_flow` | yes | Hot-water draw at the tank outlet |
| `makeup_temperature` | yes | Temperature of cold make-up water entering the tank |
| `requested_delivery_temperature` | no | Delivery temperature wanted by the user, if it varies |

Also fill `inputs/timeseries/dhw_draw.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/drinking_demand.csv`: Drinking and cooking water demand at the treatment unit outlet (needed by phase 6)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `demand_volume_flow` | yes | Product-water demand |

Also fill `inputs/timeseries/drinking_demand.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/storage_flows.csv`: Villa storage inflow and outflow, if the storage module is enabled (needed by phase 6)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `storage_inflow` | yes | Mains water inflow to the villa storage |
| `storage_outflow` | yes | Total outflow from the villa storage |
| `storage_inflow_temperature` | no | Temperature of inflowing water |

Also fill `inputs/timeseries/storage_flows.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/feed_water_quality.csv`: Water quality at the unit inlet, long format: one row per parameter per time (needed by phase 6)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `species_id` | yes | Must match a species_id in the species registry table |
| `value` | yes | Measured value |
| `unit` | yes | Unit string of this value |
| `origin` | yes | sensor or lab |
| `sample_id` | no | Lab sample id or sensor id |
| `qc_flag` | no | Your quality code |

Also fill `inputs/timeseries/feed_water_quality.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/measured_pvt.csv`: Measured array data for validation, wide format (needed by phase 3)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `poa_irradiance` | yes | Measured plane-of-array irradiance |
| `t_ambient` | yes | Ambient temperature |
| `t_module_back` | yes | PV module back-surface temperature |
| `dc_voltage` | yes | DC voltage |
| `dc_current` | yes | DC current |
| `dc_power` | yes | DC power |
| `loop_flow` | no | Collector loop flow |
| `t_collector_in` | no | Collector inlet fluid temperature |
| `t_collector_out` | no | Collector outlet fluid temperature |
| `pump_power` | no | Pump electrical power |
| `pump_state` | no | On or off |
| `qc_flag` | no | Your quality code |

Also fill `inputs/timeseries/measured_pvt.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/measured_tank_profile.csv`: Measured tank temperatures, long format (needed by phase 4)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `sensor_id` | yes | Sensor identifier |
| `height_from_bottom` | yes | Sensor height above the tank bottom |
| `temperature` | yes | Measured temperature |

Also fill `inputs/timeseries/measured_tank_profile.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/measured_pv_only.csv`: Measured PV-only reference (same module without heat extraction), if you have it (needed by phase 3)

| Column | Required | What it holds |
| --- | --- | --- |
| `timestamp` | yes | Time, ISO 8601 with explicit UTC offset |
| `poa_irradiance` | yes | Plane-of-array irradiance |
| `t_module_back` | yes | Back-surface temperature |
| `dc_power` | yes | DC power |

Also fill `inputs/timeseries/measured_pv_only.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

### `inputs/timeseries/tariffs.csv`: Electricity prices by period (needed by phase 9)

| Column | Required | What it holds |
| --- | --- | --- |
| `period_start` | yes | Start of period, ISO 8601 with explicit UTC offset |
| `period_end` | yes | End of period, ISO 8601 with explicit UTC offset |
| `import_price` | yes | Price per energy unit for imported electricity |
| `export_price` | no | Price per energy unit for exported electricity |
| `currency` | yes | Currency code |

Also fill `inputs/timeseries/tariffs.meta.yaml`: site time zone, timestamp convention, interval, a unit for each column, data origin and QC codes.

## Table files

### `inputs/tables/species_registry.csv`: Every water-quality parameter the simulation tracks (needed by phase 1)

| Column | Required | What it holds |
| --- | --- | --- |
| `species_id` | yes | Short id, no spaces; used everywhere else |
| `display_name` | yes | Readable name |
| `species_class` | yes | dissolved, particulate, disinfectant or physical |
| `unit` | yes | Unit string used throughout |
| `tracked` | yes | yes or no |
| `is_sensor_channel` | yes | yes if an online sensor measures it |
| `notes` | no | Anything else |

### `inputs/tables/treatment_removal.csv`: Removal or rejection per stage per species (needed by phase 6)

| Column | Required | What it holds |
| --- | --- | --- |
| `stage_id` | yes | sediment, carbon, uf, membrane, remin or uv |
| `species_id` | yes | Must exist in species_registry |
| `removal_basis` | yes | fraction_removed, fraction_passed, or added_concentration |
| `value` | yes | Value in the stated basis |
| `condition_note` | yes | Operating condition the value applies to |
| `uncertainty_kind` | no | absolute, relative or none |
| `uncertainty_value` | no | Magnitude of the uncertainty |
| `source_type` | yes | measured, datasheet, literature, standard or assumption |
| `source_ref` | yes | File in inputs/provenance or a citation you verified |
| `status` | yes | draft or confirmed |

### `inputs/tables/pressure_drop_vs_loading.csv`: Pressure drop against loading per stage (needed by phase 6)

| Column | Required | What it holds |
| --- | --- | --- |
| `stage_id` | yes | Stage id |
| `loading` | yes | Loading value |
| `loading_unit` | yes | Unit string of loading |
| `pressure_drop` | yes | Pressure drop value |
| `pressure_unit` | yes | Unit string of pressure drop |
| `flow_basis` | yes | Flow at which the value applies |
| `source_ref` | yes | Source file or verified citation |

### `inputs/tables/product_quality_limits.csv`: Your drinking-water quality targets (needed by phase 7)

| Column | Required | What it holds |
| --- | --- | --- |
| `species_id` | yes | Must exist in species_registry |
| `limit_type` | yes | max, min or range |
| `limit_low` | no | Lower limit, empty if not applicable |
| `limit_high` | no | Upper limit, empty if not applicable |
| `unit` | yes | Unit string |
| `basis` | yes | Regulation or guideline name and clause |
| `applies_to` | yes | product_water, or tap_water_after_storage |

### `inputs/tables/controller_rules.csv`: Deployable MNT controller rules (needed by phase 7)

| Column | Required | What it holds |
| --- | --- | --- |
| `rule_id` | yes | Unique id |
| `priority` | yes | Evaluation order, lowest first |
| `input_signal` | yes | species_id or other signal name |
| `comparison` | yes | greater_than, less_than, between |
| `threshold_low` | no | Value, empty if not applicable |
| `threshold_high` | no | Value, empty if not applicable |
| `unit` | yes | Unit string |
| `action_pathway` | yes | Pathway id selected when the rule fires |
| `hysteresis` | no | Band to avoid chatter, empty if none |
| `min_dwell` | no | Minimum time in the selected pathway, empty if none |

### `inputs/tables/sensors.csv`: Sensor specifications for the optional sensor layer (needed by phase 7)

| Column | Required | What it holds |
| --- | --- | --- |
| `sensor_id` | yes | Unique id |
| `measured_species_id` | yes | species_id or physical quantity name |
| `range_low` | yes | Lower measurement range |
| `range_high` | yes | Upper measurement range |
| `unit` | yes | Unit string |
| `noise_kind` | yes | gaussian_absolute, gaussian_relative or none |
| `noise_value` | no | Standard deviation in the stated kind |
| `bias` | no | Constant offset |
| `drift_rate` | no | Drift per unit time |
| `dropout_probability` | no | Probability per time step |
| `response_time` | no | Sensor lag |
| `location` | yes | inlet or outlet |
| `source_ref` | yes | Datasheet or calibration file |

### `inputs/tables/consumable_costs.csv`: Consumable and replacement costs (needed by phase 9)

| Column | Required | What it holds |
| --- | --- | --- |
| `stage_id` | yes | Stage id |
| `item` | yes | Consumable name |
| `unit_cost` | yes | Cost per item |
| `currency` | yes | Currency code |
| `replacement_trigger_ref` | yes | The replacement_rule this follows in treatment_components |

### `inputs/tables/pathway_costs.csv`: Capital cost per pathway (needed by phase 9)

| Column | Required | What it holds |
| --- | --- | --- |
| `pathway_id` | yes | Pathway id |
| `capex` | yes | Capital cost of the treatment hardware |
| `currency` | yes | Currency code |
| `lifetime` | yes | Service life |
| `lifetime_unit` | yes | Unit string |

### `inputs/tables/scale_scenarios.csv`: Community scale-up scenarios (needed by phase 9)

| Column | Required | What it holds |
| --- | --- | --- |
| `scenario_id` | yes | Unique id |
| `villa_count` | yes | Number of villas |
| `demand_diversity_note` | yes | How demand differs between villas (text), or a reference to a table |
| `shared_maintenance_saving_fraction` | yes | Fraction of maintenance cost saved by sharing |
| `procurement_discount_fraction` | yes | Fraction of capital cost saved by bulk procurement |
| `monitoring_cost_sharing` | yes | How monitoring cost is shared (text) |

### `inputs/tables/validation_acceptance.csv`: Validation metrics and limits, signed before any comparison (needed by phase 3)

| Column | Required | What it holds |
| --- | --- | --- |
| `variable` | yes | Model output being compared |
| `metric` | yes | Name of the metric |
| `limit` | yes | Acceptance limit |
| `comparison` | yes | less_than or greater_than |
| `basis` | yes | Why this limit was chosen |

### `inputs/tables/decay_test_data.csv`: Disinfectant decay test data (needed by phase 6)

| Column | Required | What it holds |
| --- | --- | --- |
| `test_id` | yes | Test identifier |
| `elapsed_time` | yes | Time since test start |
| `concentration` | yes | Measured concentration |
| `temperature` | yes | Test temperature |
| `initial_concentration` | yes | Concentration at start |
| `unit` | yes | Unit string |

### `inputs/tables/initial_tank_profile.csv`: Optional per-node initial tank temperature (needed by phase 4)

| Column | Required | What it holds |
| --- | --- | --- |
| `node_index` | yes | Node index, first node is at the bottom |
| `temperature` | yes | Initial temperature |

### `inputs/tables/pvt_curves.csv`: Optional curves: efficiency vs irradiance, incidence-angle modifier, wind dependence, pump curve, membrane projection (needed by phase 3)

| Column | Required | What it holds |
| --- | --- | --- |
| `curve_id` | yes | irradiance_efficiency, iam, wind_loss, pump, membrane_projection, or other id |
| `x_name` | yes | Name of the x variable |
| `x_value` | yes | x value |
| `x_unit` | yes | Unit string of x |
| `y_name` | yes | Name of the y variable |
| `y_value` | yes | y value |
| `y_unit` | yes | Unit string of y |
| `source_ref` | yes | Source file or verified citation |

## Format of a filled parameter entry

```yaml
- id: <parameter id from the table above>
  value: <your value, or a categorical option>
  unit: <unit string>
  source_type: <measured | datasheet | literature | standard | assumption>
  source_ref: <file name in inputs/provenance, or a citation you verified>
  uncertainty: {kind: <absolute | relative | none>, value: <magnitude>, distribution: <normal | uniform | triangular | lognormal | none>}
  valid_range: {min: <number>, max: <number>}
  status: confirmed
  entered_by: <your name>
  entered_on: <YYYY-MM-DD>
```

## Format of a long-format water-quality row

```csv
timestamp,species_id,value,unit,origin,sample_id,qc_flag
<YYYY-MM-DDThh:mm:ss+hh:mm>,<species_id>,<number>,<unit string>,<sensor|lab>,<id>,<code>
```
