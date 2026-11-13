# Input Status

## Parameters

| ID | Value | Unit | Status |
|---|---|---|---|
| const.cp_water_ref | 4180.0 | 'J/(kg*K)' | 'confirmed' |
| const.property_source | 'constant liquid-water properties' | None | 'confirmed' |
| const.rho_water_ref | 997.0 | 'kg/m3' | 'confirmed' |
| econ.annual_maintenance | 90.57 | 'AED/month' | 'confirmed' |
| econ.baseline_ro_capex | 1530.1 | 'AED' | 'confirmed' |
| econ.baseline_ro_consumable_cost | 17.877 | 'AED/month' | 'confirmed' |
| econ.baseline_ro_lifetime | 5.0 | 'year' | 'confirmed' |
| econ.baseline_ro_power | '100 W demo comparator; verify rated basis' | None | 'confirmed' |
| econ.baseline_ro_recovery | 0.9403 | '1' | 'confirmed' |
| econ.bottled_price | 0.006 | 'AED/L' | 'confirmed' |
| econ.bottled_replaced_fraction | 0.3708 | '1' | 'confirmed' |
| econ.capex_monitoring | 4607.54 | 'AED' | 'confirmed' |
| econ.capex_pvt | 1232.64 | 'AED' | 'confirmed' |
| econ.capex_tank | 2553.78 | 'AED' | 'confirmed' |
| econ.capex_treatment | 1350.45 | 'AED' | 'confirmed' |
| econ.currency | 'AED' | None | 'confirmed' |
| econ.discount_rate | 0.0279 | '1/year' | 'confirmed' |
| econ.displaced_fuel_price | 0.105 | 'AED/kWh' | 'confirmed' |
| econ.displaced_heat_source | 'electric_resistance' | None | 'confirmed' |
| econ.displaced_heater_efficiency | 0.5604 | '1' | 'confirmed' |
| econ.electricity_value_basis | 'avoided_import_tariff' | None | 'confirmed' |
| econ.escalation_electricity | 0.0269 | '1/year' | 'confirmed' |
| econ.escalation_other | 0.0875 | '1/year' | 'confirmed' |
| econ.escalation_water | 0.0429 | '1/year' | 'confirmed' |
| econ.horizon | 20.0 | 'year' | 'confirmed' |
| econ.installation | 2967.31 | 'AED' | 'confirmed' |
| econ.monitoring_service_cost | 14.931 | 'AED/month' | 'confirmed' |
| econ.municipal_water_price | 0.011 | 'AED/L' | 'confirmed' |
| econ.pvt_degradation | 0.0252 | '1/year' | 'confirmed' |
| econ.pvt_lifetime | 25.0 | 'year' | 'confirmed' |
| econ.reject_disposal_price | 0.046 | 'AED/L' | 'confirmed' |
| econ.residual_value | 2254.64 | 'AED' | 'confirmed' |
| econ.tank_lifetime | 15.0 | 'year' | 'confirmed' |
| elec.battery_capacity | 9000000.0 | 'J' | 'confirmed' |
| elec.battery_max_power | 214.844 | 'W' | 'confirmed' |
| elec.battery_min_soc | 0.1 | '1' | 'confirmed' |
| elec.battery_round_trip_eff | 0.92 | '1' | 'confirmed' |
| elec.comms_power | 119.067 | 'W' | 'confirmed' |
| elec.configuration | 'grid_connected_with_battery' | None | 'confirmed' |
| elec.controller_power | 150.953 | 'W' | 'confirmed' |
| elec.export_allowed | True | None | 'confirmed' |
| elec.inverter_standby_power | 106.101 | 'W' | 'confirmed' |
| elec.priority_order | 'critical controls, pumps, water treatment, battery, export' | None | 'confirmed' |
| elec.sensor_power_total | 220.645 | 'W' | 'confirmed' |
| env.bottle_mass | 0.982 | 'kg' | 'confirmed' |
| env.bottle_volume | 1.0 | 'L' | 'confirmed' |
| env.fuel_emission_factor | 771.233 | 'g_CO2eq/kWh' | 'confirmed' |
| env.grid_emission_factor | 746.396 | 'g_CO2eq/kWh' | 'confirmed' |
| env.include_transport | True | None | 'confirmed' |
| env.system_boundary | 'villa PVT collector and listed auxiliaries; demo boundary' | None | 'confirmed' |
| env.transport_emission_per_volume | 0.002 | 'kg_CO2eq/m3' | 'confirmed' |
| loop.ctrl_T_tank_max | 358.15 | 'K' | 'confirmed' |
| loop.ctrl_dT_off | 1.0 | 'K' | 'confirmed' |
| loop.ctrl_dT_on | 4.0 | 'K' | 'confirmed' |
| loop.ctrl_min_dwell | 36677.02 | 's' | 'confirmed' |
| loop.ctrl_min_irradiance | 100.0 | 'W/m2' | 'confirmed' |
| loop.ctrl_sensor_nodes | 'collector outlet versus tank reference; confirm node convention' | None | 'confirmed' |
| loop.ctrl_use_min_irradiance | False | None | 'confirmed' |
| loop.flow_mode | 'fixed' | None | 'confirmed' |
| loop.fluid_cp | 4180.0 | 'J/(kg*K)' | 'confirmed' |
| loop.fluid_density | 997.0 | 'kg/m3' | 'confirmed' |
| loop.fluid_type | 'water' | None | 'confirmed' |
| loop.hx_effectiveness | 0.7028 | '1' | 'confirmed' |
| loop.hx_present | True | None | 'confirmed' |
| loop.mass_flow_fixed | 0.011111111111111112 | 'kg/s' | 'confirmed' |
| loop.pipe_ambient_mode | 'tank_ambient' | None | 'confirmed' |
| loop.pipe_ambient_value | 295.923 | 'K' | 'confirmed' |
| loop.pipe_loss_UA | 4.858 | 'W/K' | 'confirmed' |
| loop.pressure_drop | 257911.557 | 'Pa' | 'confirmed' |
| loop.pump_efficiency | 0.5696 | '1' | 'confirmed' |
| loop.pump_power_fixed | 6.0 | 'W' | 'confirmed' |
| loop.pump_power_model | 'fixed_when_on' | None | 'confirmed' |
| mnt.controller_delay | 10992.677 | 's' | 'confirmed' |
| mnt.decision_interval | 40397.138 | 's' | 'confirmed' |
| mnt.infeasible_policy | 'flag_and_stop' | None | 'confirmed' |
| mnt.intensity_order | 'A,B,C' | None | 'confirmed' |
| mnt.lexicographic_order | 'quality, energy, cost' | None | 'confirmed' |
| mnt.normalization | 'by_user_reference_table' | None | 'confirmed' |
| mnt.objective_mode | 'lexicographic' | None | 'confirmed' |
| mnt.pathway_ids | 'A,B,C' | None | 'confirmed' |
| mnt.weight_consumable | 0.0853 | '1' | 'confirmed' |
| mnt.weight_energy | 0.0672 | '1' | 'confirmed' |
| mnt.weight_reject | 0.0668 | '1' | 'confirmed' |
| numerics.end | '2026-01-01T04:00:00+04:00' | None | 'confirmed' |
| numerics.ensemble_size | 1 | None | 'confirmed' |
| numerics.gap_max_duration | 66738.229 | 's' | 'confirmed' |
| numerics.gap_policy | 'flag_and_stop' | None | 'confirmed' |
| numerics.initial_storage_state | 'new consumables; zero loading' | None | 'confirmed' |
| numerics.initial_tank_temperature | 293.15 | 'K' | 'confirmed' |
| numerics.loop_max_iterations | 3 | None | 'confirmed' |
| numerics.loop_solver | 'bracketing' | None | 'confirmed' |
| numerics.loop_tolerance | 0.0763 | '1' | 'confirmed' |
| numerics.master_seed | 20261029 | None | 'confirmed' |
| numerics.mc_stopping_rule | 'fixed_size' | None | 'confirmed' |
| numerics.mc_stopping_tolerance | 0.0731 | '1' | 'confirmed' |
| numerics.output_interval | 3600.0 | 's' | 'confirmed' |
| numerics.property_model | 'constant' | None | 'confirmed' |
| numerics.sensitivity_method | 'morris_screening' | None | 'confirmed' |
| numerics.spin_up | 55425.49 | 's' | 'confirmed' |
| numerics.start | '2025-01-01T04:00:00+04:00' | None | 'confirmed' |
| numerics.tank_scheme | 'substepped_explicit' | None | 'confirmed' |
| numerics.tank_substeps | 6 | None | 'confirmed' |
| numerics.time_step | 600.0 | 's' | 'confirmed' |
| pvt_el.G_ref | 1000.0 | 'W/m2' | 'confirmed' |
| pvt_el.T_ref | 298.15 | 'K' | 'confirmed' |
| pvt_el.beta | 0.0037 | '1/K' | 'confirmed' |
| pvt_el.eta_ref | 0.2 | '1' | 'confirmed' |
| pvt_el.iam_model | 'none' | None | 'confirmed' |
| pvt_el.inverter_efficiency | 0.96 | '1' | 'confirmed' |
| pvt_el.irradiance_model | 'none' | None | 'confirmed' |
| pvt_el.module_count | 3 | None | 'confirmed' |
| pvt_el.mpp_assumption | 'user_efficiency_factor' | None | 'confirmed' |
| pvt_el.mpp_efficiency_factor | 0.98 | '1' | 'confirmed' |
| pvt_th.F_R | 0.4922 | '1' | 'confirmed' |
| pvt_th.R_cell_fluid | 0.114 | 'K*m2/W' | 'confirmed' |
| pvt_th.T_fluid_max | 358.15 | 'K' | 'confirmed' |
| pvt_th.U_L | 12.0 | 'W/(m2*K)' | 'confirmed' |
| pvt_th.U_L_wind_dependence | 'none' | None | 'confirmed' |
| pvt_th.area_basis | 'gross' | None | 'confirmed' |
| pvt_th.collector_area | 6.0 | 'm2' | 'confirmed' |
| pvt_th.collector_type | 'unglazed' | None | 'confirmed' |
| pvt_th.demo_inlet_temperature | 293.15 | 'K' | 'confirmed' |
| pvt_th.flow_max | 0.02 | 'kg/s' | 'confirmed' |
| pvt_th.flow_min | 0.005 | 'kg/s' | 'confirmed' |
| pvt_th.pv_only_reference_model | 'user_named_model_in_equation_register' | None | 'confirmed' |
| pvt_th.tau_alpha | 0.5 | '1' | 'confirmed' |
| pvt_th.thermal_capacitance | 12133.378 | 'J/(m2*K)' | 'confirmed' |
| pvt_th.thermal_model | 'steady_state_hottel_whillier_form' | None | 'confirmed' |
| site.azimuth_convention | 'south_zero_east_negative' | None | 'confirmed' |
| site.collector_azimuth | 0.0 | 'deg' | 'confirmed' |
| site.collector_tilt | 25.0 | 'deg' | 'confirmed' |
| site.elevation | 31.1 | 'm' | 'confirmed' |
| site.ground_albedo | 0.2 | '1' | 'confirmed' |
| site.latitude | 25.79 | 'deg' | 'confirmed' |
| site.longitude | 55.94 | 'deg' | 'confirmed' |
| site.shading_loss_factor | 0.0 | '1' | 'confirmed' |
| site.timezone | 'Asia/Dubai' | None | 'confirmed' |
| soiling.clean_recovery | 0.3599 | '1' | 'confirmed' |
| soiling.loss_rate | 0.0706 | '1/year' | 'confirmed' |
| soiling.max_loss | 0.4914 | '1' | 'confirmed' |
| soiling.mode | 'none' | None | 'confirmed' |
| sq.T_ref | 303.658 | 'K' | 'confirmed' |
| sq.decay_model | 'first_order_arrhenius' | None | 'confirmed' |
| sq.disinfectant_species_id | 'free_chlorine' | None | 'confirmed' |
| sq.enabled | False | None | 'confirmed' |
| sq.initial_concentration | 1.624 | 'mg/L' | 'confirmed' |
| sq.k_ref | 0.0852 | '1/year' | 'confirmed' |
| sq.mixing_model | 'user_named_model_in_equation_register' | None | 'confirmed' |
| sq.storage_temperature_constant | 294.082 | 'K' | 'confirmed' |
| sq.storage_temperature_mode | 'constant_value' | None | 'confirmed' |
| sq.temp_coefficient | 38613.588 | 'J/(mol*K)' | 'confirmed' |
| sq.treated_decay_note | 'uses the storage decay assumptions in this demo preset' | None | 'confirmed' |
| sq.treated_storage_enabled | True | None | 'confirmed' |
| sq.treated_storage_volume | 30.0 | 'L' | 'confirmed' |
| sq.villa_storage_volume | 5.264 | 'L' | 'confirmed' |
| sq.wall_decay | 0.0159 | '1/year' | 'confirmed' |
| sq.wall_decay_enabled | True | None | 'confirmed' |
| tank.UA_total | 4.292 | 'W/K' | 'confirmed' |
| tank.ambient_constant | 314.778 | 'K' | 'confirmed' |
| tank.ambient_mode | 'timeseries' | None | 'confirmed' |
| tank.aux_efficiency | 0.95 | '1' | 'confirmed' |
| tank.aux_node | 2 | None | 'confirmed' |
| tank.aux_power | 1200.0 | 'W' | 'confirmed' |
| tank.aux_present | True | None | 'confirmed' |
| tank.aux_setpoint | 326.15 | 'K' | 'confirmed' |
| tank.charge_inlet_node | 4 | None | 'confirmed' |
| tank.charge_method | 'direct_fluid_exchange' | None | 'confirmed' |
| tank.charge_outlet_node | 8 | None | 'confirmed' |
| tank.coil_effectiveness | 0.3878 | '1' | 'confirmed' |
| tank.conduction_model | 'none' | None | 'confirmed' |
| tank.delivery_temp_min | 318.15 | 'K' | 'confirmed' |
| tank.diameter | 1.725 | 'm' | 'confirmed' |
| tank.draw_outlet_node | 1 | None | 'confirmed' |
| tank.effective_conductivity | 0.9 | 'W/(m*K)' | 'confirmed' |
| tank.height | 2.267 | 'm' | 'confirmed' |
| tank.loss_distribution | 'by_surface_area' | None | 'confirmed' |
| tank.makeup_inlet_node | 7 | None | 'confirmed' |
| tank.mixing_model | 'instant_inversion_mixing' | None | 'confirmed' |
| tank.node_count | 6 | None | 'confirmed' |
| tank.safety_policy | False | None | 'confirmed' |
| tank.stored_temp_min_safety | 313.808 | 'K' | 'confirmed' |
| tank.volume | 150.0 | 'L' | 'confirmed' |
| tc.booster_present | True | None | 'confirmed' |
| tc.booster_pump_efficiency | 0.22 | '1' | 'confirmed' |
| tc.carbon.capacity | 8.686 | 'kg' | 'confirmed' |
| tc.carbon.disinfectant_removal_model | 'species_removal_table' | None | 'confirmed' |
| tc.carbon.pressure_drop_model | 'constant' | None | 'confirmed' |
| tc.carbon.replacement_rule | 'time' | None | 'confirmed' |
| tc.conductivity_to_tds_factor | 0.0959 | '1' | 'confirmed' |
| tc.feed_pressure_available | 101325.0 | 'Pa' | 'confirmed' |
| tc.membrane.area | 0.369 | 'm2' | 'confirmed' |
| tc.membrane.capacity | 1.291 | 'kg' | 'confirmed' |
| tc.membrane.flux_model | 'constant_recovery_only' | None | 'confirmed' |
| tc.membrane.fouling_model | 'none' | None | 'confirmed' |
| tc.membrane.fouling_rate | 0.284815274969 | '1/(m3*s)' | 'confirmed' |
| tc.membrane.operating_pressure | 600000.0 | 'Pa' | 'confirmed' |
| tc.membrane.pretreatment_note | 'sediment and carbon filters (demo configuration)' | None | 'confirmed' |
| tc.membrane.pump_efficiency | 0.22 | '1' | 'confirmed' |
| tc.membrane.recovery | 0.5 | '1' | 'confirmed' |
| tc.membrane.replacement_rule | 'permeability_loss' | None | 'confirmed' |
| tc.membrane.temp_correction | 'none' | None | 'confirmed' |
| tc.membrane.type | 'low_pressure_ro' | None | 'confirmed' |
| tc.membrane.water_permeability | '3e-11' | 'm/(s*Pa)' | 'confirmed' |
| tc.pathway_stage_lists | 'A: sediment,carbon; B: sediment,carbon,UV; C: sediment,carbon,low_pressure_ro,remineralisation,UV' | None | 'confirmed' |
| tc.rated_product_flow | 3.2859477291666673e-06 | 'm3/s' | 'confirmed' |
| tc.remin.enabled | True | None | 'confirmed' |
| tc.remin.energy_per_volume | 1103552.027 | 'J/m3' | 'confirmed' |
| tc.remin.method | 'Ca/Mg remineralisation' | None | 'confirmed' |
| tc.sediment.capacity | 1.12 | 'kg' | 'confirmed' |
| tc.sediment.pressure_drop_model | 'constant' | None | 'confirmed' |
| tc.sediment.replacement_rule | 'volume' | None | 'confirmed' |
| tc.sensor_cost_and_power_note | 'sensor and monitoring values are demo assumptions' | None | 'confirmed' |
| tc.uf.backwash_energy | 4589.489 | 'J' | 'confirmed' |
| tc.uf.backwash_interval | '12 h (demo assumption)' | None | 'confirmed' |
| tc.uf.backwash_volume | 216.903 | 'L' | 'confirmed' |
| tc.uf.capacity | 8.872 | 'kg' | 'confirmed' |
| tc.uf.pressure_drop_model | 'vs_loading_table' | None | 'confirmed' |
| tc.uf.recovery | 0.8823 | '1' | 'confirmed' |
| tc.uf.replacement_rule | 'time' | None | 'confirmed' |
| tc.use_conductivity_to_tds | True | None | 'confirmed' |
| tc.uv.ballast_efficiency | 0.538 | '1' | 'confirmed' |
| tc.uv.dose_accounting | False | None | 'confirmed' |
| tc.uv.lamp_intensity | 1.961 | 'W/m2' | 'confirmed' |
| tc.uv.lamp_life | 54658.903 | 's' | 'confirmed' |
| tc.uv.lamp_power | 167.881 | 'W' | 'confirmed' |
| tc.uv.operation_policy | 'on_with_flow' | None | 'confirmed' |
| tc.uv.power_basis | 'wall_side' | None | 'confirmed' |
| tc.uv.reactor_volume | 464.028 | 'L' | 'confirmed' |
| tc.uv.target_dose | 25914.069 | 'J/m2' | 'confirmed' |
| tc.uv.transmittance_source | 'feed_water_quality_series' | None | 'confirmed' |
| tc.uv.warmup_time | 78314.434 | 's' | 'confirmed' |
| ver.analytical_test_tol_rel | 0.6427 | '1' | 'confirmed' |
| ver.calibration_parameter_list | 'none; do not calibrate demo defaults' | None | 'confirmed' |
| ver.calibration_period | 'not calibrated; exploratory demonstration only' | None | 'confirmed' |
| ver.energy_balance_tol_abs | 3184.578 | 'J' | 'confirmed' |
| ver.energy_balance_tol_rel | 0.8834 | '1' | 'confirmed' |
| ver.mass_balance_tol_rel | 0.8539 | '1' | 'confirmed' |
| ver.nodecount_convergence_tol | 0.1661 | '1' | 'confirmed' |
| ver.timestep_convergence_tol | 0.5069 | '1' | 'confirmed' |
| ver.validation_period | 'not validated; exploratory demonstration only' | None | 'confirmed' |

## Tables

- `consumable_costs`: loaded
- `controller_rules`: loaded
- `decay_test_data`: loaded
- `initial_tank_profile`: loaded
- `pathway_costs`: loaded
- `pressure_drop_vs_loading`: loaded
- `product_quality_limits`: loaded
- `pvt_curves`: loaded
- `scale_scenarios`: loaded
- `sensors`: loaded
- `species_registry`: loaded
- `treatment_removal`: loaded
- `validation_acceptance`: loaded

## Time Series

- `dhw_draw`: loaded
- `drinking_demand`: loaded
- `feed_water_quality`: loaded
- `measured_pv_only`: loaded
- `measured_pvt`: loaded
- `measured_tank_profile`: loaded
- `soiling_events`: loaded
- `storage_flows`: loaded
- `tank_ambient`: loaded
- `tariffs`: loaded
- `weather`: loaded

---

No blocking issues found.