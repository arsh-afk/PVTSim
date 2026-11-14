"""Interactive whole-system screening for the AquaSolar villa concept.

This module composes the existing, project-parameterised PVT collector with an
explicitly labelled *screening* model of the rest of the reported system:
a hot-water tank with a household draw profile, a pump on/off controller,
an electrical bus with an optional battery, a reverse-osmosis/brine-reuse
water balance, and simple operating-cost totals.

It is not the validated transient model described in the CMAT report. Its
outputs are not calibrated engineering, safety, or potable-water results.
Every assumption that is not a registered project parameter is returned with
the result so the workbench can show it beside the numbers.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from aquasolar.pvt.runner import load_pvt_parameters, load_pvt_weather

SECONDS_PER_HOUR = float(3600)
HOURS_PER_DAY = float(24)
KELVIN_OFFSET = float(273.15)
WATER_SPECIFIC_HEAT = float(4.186)  # kJ/(kg K); density taken as 1 kg/L
LITRES_PER_CUBIC_METRE = float(1000)
JOULES_PER_KWH = float("3.6e6")
PROFILE_HOURS = int("24")

# Screening envelope. These are model-boundary guards, not physical claims.
LIMITS: dict[str, tuple[float, float]] = {
    "collector_area": (float(1), float(200)),
    "tank_volume": (float(20), float(5000)),
    "tank_heat_loss": (float("0.1"), float(50)),
    "daily_draw": (float(5), float(1000)),
    "delivery_temperature": (float(35), float(80)),
    "mains_temperature": (float(2), float(40)),
    "draw_peaking": (float(1), float(3)),
    "pump_set_gain": (float(1), float(60)),
    "ambient_cutout": (float(0), float(30)),
    "pump_power": (float("0.5"), float(500)),
    "backup_efficiency": (float("0.5"), float(1)),
    "auxiliary_cop": (float(1), float(6)),
    "battery_capacity": (float(0), float(200)),
    "battery_efficiency": (float("0.5"), float(1)),
    "battery_initial": (float(0), float(100)),
    "ro_recovery": (float("0.05"), float("0.95")),
    "drinking_water": (float(0), float(500)),
    "ro_salinity": (float(50), float(40000)),
    "ro_specific_energy": (float("0.3"), float(20)),
    "electricity_tariff": (float(0), float(5)),
    "export_price": (float(0), float(5)),
    "collector_cost_per_m2": (float(0), float(20000)),
    "tank_cost": (float(0), float(200000)),
    "battery_cost_per_kwh": (float(0), float(10000)),
    "ro_cost": (float(0), float(200000)),
    "lifetime": (float(1), float(50)),
    "discount_rate": (float(0), float("0.3")),
    "bottled_water_price": (float(0), float("0.5")),
    "baseline_heater_cop": (float("0.5"), float(6)),
    "baseline_kettle_load": (float(0), float(5000)),
}

_NUMERIC_FIELDS = tuple(LIMITS)
_CHOICES = {
    "draw_strategy": {"household", "square_wave"},
    "electrical_mode": {"grid_tie", "island"},
}
_DEFAULT_SEED = int("20261114")


@dataclass(frozen=True)
class DesignInputs:
    """User-facing screening switches, expressed in everyday units."""

    collector_area: float = 6.0
    tank_volume: float = 150.0
    tank_heat_loss: float = 2.0
    draw_strategy: str = "household"
    daily_draw: float = 150.0
    delivery_temperature: float = 50.0
    mains_temperature: float = 28.0
    draw_peaking: float = 1.0
    pump_set_gain: float = 8.0
    ambient_cutout: float = 5.0
    pump_power: float = 6.0
    backup_efficiency: float = 0.95
    auxiliary_cop: float = 1.0
    electrical_mode: str = "grid_tie"
    battery_capacity: float = 0.0
    battery_efficiency: float = 0.9
    battery_initial: float = 50.0
    ro_recovery: float = 0.5
    drinking_water: float = 25.0
    ro_salinity: float = 500.0
    ro_specific_energy: float = 2.1
    electricity_tariff: float = 0.45
    export_price: float = 0.0
    collector_cost_per_m2: float = 450.0
    tank_cost: float = 2500.0
    battery_cost_per_kwh: float = 400.0
    ro_cost: float = 1200.0
    lifetime: float = 20.0
    discount_rate: float = 0.06
    bottled_water_price: float = 0.002
    baseline_heater_cop: float = 1.0
    baseline_kettle_load: float = 0.0


@dataclass
class DesignResult:
    """JSON-serialisable screening result returned to the workbench."""

    inputs: dict[str, Any]
    hourly: list[dict[str, Any]]
    summary: dict[str, Any]
    drivers: dict[str, Any]
    assumptions: list[dict[str, str]]
    status: dict[str, Any]
    ensemble: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _literals(seed: int, count: int, low: float, high: float) -> tuple[float, ...]:
    """Deterministic seeded spread for the uncertainty band (reproducible)."""
    state = seed & int("2147483647")
    values = []
    for _ in range(count):
        state = (int("1103515245") * state + int("12345")) & int("2147483647")
        values.append(low + (high - low) * (state / int("2147483647")))
    return tuple(values)


def _quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        return 0.0
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    fraction = position - lower
    return sorted_values[lower] + (
        sorted_values[upper] - sorted_values[lower]
    ) * fraction


def _require_number(name: str, value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Change {name.replace('_', ' ')} must be a number."
        ) from exc
    if not math.isfinite(number):
        raise ValueError(f"Change {name.replace('_', ' ')} must be finite.")
    low, high = LIMITS[name]
    if number < low or number > high:
        raise ValueError(
            f"Change {name.replace('_', ' ')} is outside the screening range "
            f"{low:g} to {high:g}."
        )
    return number


def _validate(payload: dict[str, Any] | DesignInputs | None) -> DesignInputs:
    data = asdict(payload) if isinstance(payload, DesignInputs) else dict(payload or {})
    known = set(DesignInputs.__annotations__)
    unknown = set(data) - known
    if unknown:
        raise ValueError(f"Unsupported change(s): {', '.join(sorted(unknown))}")
    merged = {**asdict(DesignInputs()), **data}
    for key in _NUMERIC_FIELDS:
        merged[key] = _require_number(key, merged[key])
    for key, allowed in _CHOICES.items():
        if merged[key] not in allowed:
            raise ValueError(
                f"{key.replace('_', ' ')} must be one of {', '.join(sorted(allowed))}."
            )
    if merged["mains_temperature"] >= merged["delivery_temperature"]:
        raise ValueError(
            "Mains temperature must stay below the delivery temperature."
        )
    return DesignInputs(**merged)


def profile_fractions(kind: str, peaking: float = 1.0) -> tuple[float, ...]:
    """Return 24 per-hour draw fractions for the selected strategy.

    ``household`` follows the two-peak villa use described in the report
    narrative; ``square_wave`` spreads the draw evenly. ``peaking`` raises the
    evening share of either profile and is normalised back to one day.
    """
    if kind == "square_wave":
        values = [1.0] * PROFILE_HOURS
    elif kind == "household":
        values = [
            0.0, 0.0, 0.0, 0.0, 0.0,
            0.06, 0.06, 0.055, 0.025, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            0.045, 0.09, 0.09, 0.075, 0.02, 0.0,
        ]
    else:
        raise ValueError("Draw strategy must be household or square_wave.")
    excess = max(peaking - 1.0, 0.0)
    if excess:
        for hour in range(10, PROFILE_HOURS):
            values[hour] *= 1.0 + excess
    total = sum(values)
    if total <= 0:
        raise ValueError("Draw strategy has no positive hours.")
    return tuple(value / total for value in values)


def _battery_round_trip(efficiency: float) -> float:
    return math.sqrt(efficiency)


def _annualise(
    capex: float,
    lifetime: float,
    discount_rate: float,
    operating_cost: float,
    annual_savings: float,
) -> dict[str, float]:
    years = max(int(round(lifetime)), 1)
    factor = sum(
        1.0 / (1.0 + discount_rate) ** year for year in range(1, years + 1)
    )
    lifecycle = capex + operating_cost * factor
    discounted_savings = annual_savings * factor
    if annual_savings > 0:
        payback = capex / annual_savings
    else:
        payback = float("inf")
    if discount_rate > 0:
        growth = (1.0 + discount_rate) ** years
        crf = discount_rate * growth / (growth - 1.0)
    else:
        crf = 1.0 / years
    return {
        "crf": crf,
        "lifecycle_cost": lifecycle,
        "discounted_savings": discounted_savings,
        "net_present_value": discounted_savings - lifecycle,
        "simple_payback_years": payback,
        "annualised_capex": capex * crf,
    }


def _round(value: float, places: int = 3) -> float:
    return float(round(value, places))


def _solar_geometry(rows, parameters) -> list[float]:
    """Plane-of-array irradiance for each weather interval, shading applied."""
    import pandas as pd
    import pvlib
    from datetime import timedelta

    centers = pd.DatetimeIndex(
        [row["timestamp"] + timedelta(hours=0.5) for row in rows]
    )
    position = pvlib.solarposition.get_solarposition(
        centers,
        parameters["site.latitude"],
        parameters["site.longitude"],
        altitude=parameters["site.elevation"],
    )
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=parameters["site.collector_tilt"],
        surface_azimuth=parameters["site.surface_azimuth"],
        solar_zenith=position["apparent_zenith"],
        solar_azimuth=position["azimuth"],
        dni=pd.Series([row["dni"] for row in rows], index=centers),
        ghi=pd.Series([row["ghi"] for row in rows], index=centers),
        dhi=pd.Series([row["dhi"] for row in rows], index=centers),
        albedo=parameters["site.ground_albedo"],
        model="isotropic",
    )["poa_global"].fillna(0.0).clip(lower=0.0)
    shading = 1.0 - parameters["site.shading_loss_factor"]
    return [float(value) * shading for value in poa]


def _simulate(
    rows: list[dict[str, Any]],
    poa: list[float],
    parameters: dict[str, Any],
    inputs: DesignInputs,
    record_hourly: bool,
) -> dict[str, Any]:
    from aquasolar.pvt.collector import pvt_solve

    fractions = profile_fractions(inputs.draw_strategy, inputs.draw_peaking)
    tank_heat_capacity = inputs.tank_volume * WATER_SPECIFIC_HEAT  # kJ/K
    battery_round_trip = _battery_round_trip(inputs.battery_efficiency)
    battery_soc = inputs.battery_capacity * inputs.battery_initial / float(100)
    fluid_cp = float(parameters["loop.fluid_cp"])
    base_area = float(parameters["pvt_th.collector_area"])
    if base_area <= 0:
        raise ValueError("The registered collector area must be positive.")
    modules = inputs.collector_area / base_area
    flow = float(parameters["loop.mass_flow_fixed"]) * modules
    temperature_cap = float(parameters["pvt_th.T_fluid_max"])
    use_heat_pump = inputs.auxiliary_cop > 1.0 + float("1e-9")

    tank_c = inputs.mains_temperature
    pump_on = False
    nonconverged = 0
    sunny_steps = 0
    totals = {
        key: 0.0
        for key in (
            "pvt_kwh", "pump_kwh", "ro_kwh", "backup_kwh", "backup_thermal_kwh",
            "load_kwh", "import_kwh", "export_kwh", "battery_in_kwh",
            "battery_out_kwh", "curtailed_kwh", "unserved_kwh", "heat_kwh",
            "hot_water_kwh", "delivered_kwh", "draw_litres", "pump_hours",
            "spilled_heat_kwh",
        )
    }
    hourly: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        ambient_c = float(row["t_ambient"])
        irradiance = poa[index]
        hour = int(row["timestamp"].hour)
        draw = inputs.daily_draw * fractions[hour]
        storage_kwh = max(
            tank_heat_capacity * (tank_c - inputs.mains_temperature)
            / SECONDS_PER_HOUR,
            0.0,
        )

        available_gain = max(
            (parameters["pvt_th.tau_alpha"] - parameters["pvt_el.eta_ref"])
            * irradiance
            - parameters["pvt_th.U_L"] * (tank_c - ambient_c),
            0.0,
        )
        estimated_temperature_gain = (
            available_gain
            * parameters["pvt_th.F_R"]
            * base_area
            / (max(float(parameters["loop.mass_flow_fixed"]), float("1e-9")) * fluid_cp)
        )
        threshold = inputs.pump_set_gain
        if pump_on:
            threshold -= inputs.ambient_cutout
        pump_on = (
            irradiance > 0
            and estimated_temperature_gain > threshold
            and tank_c < temperature_cap - float("0.5")
        )

        pvt_w = 0.0
        useful_w = 0.0
        pump_w = 0.0
        converged = True
        if pump_on:
            inlet_c = min(tank_c, temperature_cap - float(2))
            result = pvt_solve(
                T_in=inlet_c + KELVIN_OFFSET,
                m_dot=flow,
                G_eff=irradiance,
                T_amb=ambient_c + KELVIN_OFFSET,
                wind_speed=float(row["wind_speed"]),
                registry={**parameters, "pvt_th.collector_area": inputs.collector_area},
            )
            if result.converged:
                pvt_w = result.P_el
                useful_w = result.Q_u
                pump_w = inputs.pump_power
                # Check the outlet does not exceed the stored tank limit.
                if result.T_f_out > temperature_cap + float("0.5"):
                    useful_w = 0.0
                    pump_w = 0.0
                    converged = False
            else:
                converged = False
                nonconverged += 1

        net_heat_w = useful_w - pump_w
        tank_energy_kwh = storage_kwh + net_heat_w / float(1000)
        if tank_energy_kwh < 0:
            tank_energy_kwh = 0.0

        # Hot-water draw mixes tank water down to the delivery setpoint.

        needed_kwh = (
            draw * WATER_SPECIFIC_HEAT
            * (inputs.delivery_temperature - inputs.mains_temperature)
            / SECONDS_PER_HOUR
        )
        from_tank_kwh = min(needed_kwh, tank_energy_kwh)
        tank_energy_kwh = max(tank_energy_kwh - from_tank_kwh, 0.0)
        backup_thermal_kwh = max(needed_kwh - from_tank_kwh, 0.0)
        backup_elec_kwh = (
            backup_thermal_kwh / inputs.auxiliary_cop
            if use_heat_pump
            else backup_thermal_kwh / inputs.backup_efficiency
        )

        tank_temperature_before_loss = (
            inputs.mains_temperature
            + tank_energy_kwh * SECONDS_PER_HOUR / tank_heat_capacity
            if tank_heat_capacity > 0
            else inputs.mains_temperature
        )
        tank_loss_kwh = max(
            inputs.tank_heat_loss * (tank_temperature_before_loss - ambient_c)
            / float(1000),
            0.0,
        )
        recovered = min(tank_loss_kwh, tank_energy_kwh)
        tank_energy_kwh -= recovered
        tank_c = (
            inputs.mains_temperature
            + tank_energy_kwh * SECONDS_PER_HOUR / tank_heat_capacity
            if tank_heat_capacity > 0
            else inputs.mains_temperature
        )
        if tank_c > temperature_cap:
            totals["spilled_heat_kwh"] += (
                tank_energy_kwh
                - tank_heat_capacity * (temperature_cap - inputs.mains_temperature)
                / SECONDS_PER_HOUR
            )
            tank_c = temperature_cap
            tank_energy_kwh = (
                tank_heat_capacity * (temperature_cap - inputs.mains_temperature)
                / SECONDS_PER_HOUR
            )

        ro_elec_kwh = (
            inputs.drinking_water
            / max(inputs.ro_recovery, float("1e-9"))
            * inputs.ro_specific_energy
            / LITRES_PER_CUBIC_METRE
            / HOURS_PER_DAY
        )
        pvt_kwh = pvt_w / float(1000)
        pump_kwh = pump_w / float(1000)
        load_kwh = pump_kwh + ro_elec_kwh + backup_elec_kwh
        surplus = pvt_kwh - load_kwh
        grid_import = 0.0
        grid_export = 0.0
        battery_in = 0.0
        battery_out = 0.0
        if surplus >= 0:
            room = max(inputs.battery_capacity - battery_soc, 0.0)
            battery_in = min(surplus * battery_round_trip, room)
            battery_soc += battery_in
            leftover = surplus - battery_in / battery_round_trip
            if inputs.electrical_mode == "grid_tie":
                grid_export = max(leftover, 0.0)
            else:
                totals["curtailed_kwh"] += max(leftover, 0.0)
        else:
            deficit = -surplus
            available = battery_soc * battery_round_trip
            battery_out = min(deficit, available)
            battery_soc -= battery_out / battery_round_trip
            deficit -= battery_out
            if inputs.electrical_mode == "grid_tie":
                grid_import = deficit
            elif deficit > 0:
                totals["unserved_kwh"] += deficit

        totals["pvt_kwh"] += pvt_kwh
        totals["pump_kwh"] += pump_kwh
        totals["ro_kwh"] += ro_elec_kwh
        totals["backup_kwh"] += backup_elec_kwh
        totals["backup_thermal_kwh"] += backup_thermal_kwh
        totals["load_kwh"] += load_kwh
        totals["import_kwh"] += grid_import
        totals["export_kwh"] += grid_export
        totals["battery_in_kwh"] += battery_in
        totals["battery_out_kwh"] += battery_out
        totals["heat_kwh"] += useful_w / float(1000)
        totals["hot_water_kwh"] += needed_kwh
        totals["delivered_kwh"] += from_tank_kwh
        totals["draw_litres"] += draw
        totals["pump_hours"] += 1.0 if pump_w > 0 else 0.0
        sunny_steps += 1 if irradiance > 0 else 0

        if record_hourly:
            hourly.append(
                {
                    "timestamp": row["timestamp"].isoformat(),
                    "T_ambient_C": _round(ambient_c),
                    "POA_W_m2": _round(irradiance),
                    "T_tank_C": _round(tank_c),
                    "pump_on": 1 if pump_w > 0 else 0,
                    "draw_litres": _round(draw),
                    "P_el_kW": _round(pvt_kwh),
                    "Q_u_kW": _round(useful_w / float(1000)),
                    "backup_kW": _round(backup_elec_kwh),
                    "ro_kW": _round(ro_elec_kwh),
                    "load_kW": _round(load_kwh),
                    "battery_soc_kWh": _round(battery_soc),
                    "import_kWh": _round(grid_import),
                    "export_kWh": _round(grid_export),
                    "hot_water_kWh": _round(needed_kwh),
                    "tank_from_solar_kWh": _round(from_tank_kwh),
                    "converged": 1 if converged else 0,
                }
            )

    return {
        "totals": totals,
        "hourly": hourly,
        "nonconverged": nonconverged,
        "sunny_steps": sunny_steps,
    }


def _summarise(
    simulated: dict[str, Any],
    inputs: DesignInputs,
    steps: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    totals = simulated["totals"]
    days = steps / HOURS_PER_DAY
    if days <= 0:
        raise ValueError("The weather file has no complete days.")
    factor = float(365) / days

    def annual(key: str) -> float:
        return totals.get(key, 0.0) * factor
    def finite_or_none(value: float) -> float | None:
        return _round(value) if math.isfinite(value) else None

    pvt_annual = annual("pvt_kwh")
    heat_annual = annual("heat_kwh")
    hot_water_annual = annual("hot_water_kwh")
    delivered_annual = annual("delivered_kwh")
    load_annual = annual("load_kwh")
    import_annual = annual("import_kwh")
    export_annual = annual("export_kwh")
    backup_annual = annual("backup_kwh")
    backup_thermal_annual = annual("backup_thermal_kwh")
    solar_fraction = (
        (hot_water_annual - backup_thermal_annual)
        / hot_water_annual
        if hot_water_annual > 0
        else 0.0
    )
    solar_fraction = min(max(solar_fraction, 0.0), 1.0)
    self_sufficiency = min(max(1.0 - import_annual / load_annual, 0.0), 1.0) if load_annual > 0 else 0.0
    drinking_m3 = inputs.drinking_water * float(365) / LITRES_PER_CUBIC_METRE
    feed_m3 = (
        inputs.drinking_water / inputs.ro_recovery * float(365) / LITRES_PER_CUBIC_METRE
    )
    brine_m3 = max(feed_m3 - drinking_m3, 0.0)
    brine_salinity = inputs.ro_salinity / (1.0 - inputs.ro_recovery)
    feed_salinity = inputs.ro_salinity
    operating_cost = (
        import_annual * inputs.electricity_tariff
        - export_annual * inputs.export_price
    )
    capex = (
        inputs.collector_cost_per_m2 * inputs.collector_area
        + inputs.tank_cost
        + inputs.battery_cost_per_kwh * inputs.battery_capacity
        + inputs.ro_cost
    )
    baseline_heating_kwh = hot_water_annual / inputs.baseline_heater_cop
    baseline_electric_kwh = baseline_heating_kwh + load_annual - backup_annual
    comparison_savings = (
        (baseline_electric_kwh - import_annual) * inputs.electricity_tariff
        + export_annual * inputs.export_price
        + inputs.bottled_water_price * inputs.drinking_water * float(365)
    )
    economics = _annualise(
        capex,
        inputs.lifetime,
        inputs.discount_rate,
        operating_cost,
        comparison_savings,
    )
    baseline_cost = (
        baseline_electric_kwh * inputs.electricity_tariff
        + inputs.baseline_kettle_load * inputs.electricity_tariff
        + inputs.bottled_water_price * inputs.drinking_water * float(365)
    )
    system_cost = operating_cost + export_annual * inputs.export_price
    avoided_annual_cost = baseline_cost - system_cost
    payback_years = capex / avoided_annual_cost if avoided_annual_cost > 0 else 0.0
    lifecost = _annualise(capex, inputs.lifetime, inputs.discount_rate, operating_cost, 0.0)
    summary = {
        "annual_pvt_kwh": _round(pvt_annual),
        "annual_heat_kwh": _round(heat_annual),
        "annual_hot_water_kwh": _round(hot_water_annual),
        "annual_backup_kwh": _round(backup_annual),
        "annual_load_kwh": _round(load_annual),
        "annual_import_kwh": _round(import_annual),
        "annual_export_kwh": _round(export_annual),
        "annual_pump_kwh": _round(annual("pump_kwh")),
        "annual_ro_kwh": _round(annual("ro_kwh")),
        "solar_heating_fraction": _round(solar_fraction),
        "tank_supply_fraction": _round(delivered_annual / hot_water_annual if hot_water_annual else 0.0),
        "self_sufficiency": _round(self_sufficiency),
        "net_electricity_kwh": _round(pvt_annual - load_annual),
        "drinking_water_m3_year": _round(drinking_m3),
        "feed_water_m3_year": _round(feed_m3),
        "brine_m3_year": _round(brine_m3),
        "brine_salinity_mg_l": _round(brine_salinity),
        "feed_salinity_mg_l": _round(feed_salinity),
        "operating_cost_year": _round(operating_cost),
        "capex": _round(capex),
        "payback_years": finite_or_none(payback_years),
        "net_present_value": _round(avoided_annual_cost - lifecost["annualised_capex"]),
        "annual_baseline_cost": _round(baseline_cost),
        "annual_system_cost": _round(system_cost),
        "annual_cost_savings": _round(avoided_annual_cost),
        "annualised_capex": _round(lifecost["annualised_capex"]),
        "lcoh_aed_per_m3": _round(
            (lifecost["annualised_capex"] + operating_cost) / drinking_m3
            if drinking_m3 > 0
            else 0.0
        ),
        "pump_hours_year": _round(annual("pump_hours")),
        "spilled_heat_kwh": _round(annual("spilled_heat_kwh")),
        "unserved_kwh": _round(annual("unserved_kwh")),
        "currency": "AED",
    }
    drivers = {
        "collector_area": _round(inputs.collector_area),
        "tank_volume": _round(inputs.tank_volume),
        "battery": _round(inputs.battery_capacity),
        "delivery_temperature": _round(inputs.delivery_temperature),
    }
    return summary, drivers


def experiment(
    rows: list[dict[str, Any]],
    poa: list[float],
    parameters: dict[str, Any],
    inputs: DesignInputs,
    sweep: str,
) -> list[dict[str, Any]]:
    """One-at-a-time sensitivity sweep for the three headline design levers."""
    if sweep not in {"collector_area", "tank_volume", "battery_capacity"}:
        raise ValueError("Unsupported sweep.")
    base = asdict(inputs)
    if sweep == "collector_area":
        values = (2.0, 4.0, 6.0, 9.0, 12.0, 18.0)
    elif sweep == "tank_volume":
        values = (75.0, 150.0, 250.0, 400.0, 800.0)
    else:
        values = (0.0, 2.0, 5.0, 10.0)
    results = []
    for value in values:
        candidate = _validate({**base, sweep: value})
        simulated = _simulate(rows, poa, parameters, candidate, record_hourly=False)
        summary, _ = _summarise(simulated, candidate, len(rows))
        results.append(
            {
                "value": value,
                "solar_heating_fraction": summary["solar_heating_fraction"],
                "self_sufficiency": summary["self_sufficiency"],
                "net_electricity_kwh": summary["net_electricity_kwh"],
                "payback_years": summary["payback_years"],
            }
        )
    return results


def ensemble(
    rows: list[dict[str, Any]],
    poa: list[float],
    parameters: dict[str, Any],
    inputs: DesignInputs,
    runs: int = int("12"),
    seed: int = _DEFAULT_SEED,
) -> list[dict[str, Any]]:
    """Small reproducible ensemble over the least-evidenced screening inputs.

    This is not the report's 40-run Monte Carlo; it is a seeded, transparent
    band that shows how much of the answer depends on unevidenced values.
    """
    fields = (
        ("tank_heat_loss", float("0.5"), float(4.0)),
        ("mains_temperature", float(22), float(34)),
        ("delivery_temperature", float(45), float(60)),
        ("backup_efficiency", 0.85, 1.0),
        ("ro_recovery", 0.35, 0.65),
        ("bottled_water_price", 0.0005, 0.004),
    )
    base = asdict(inputs)
    results = []
    for member in range(runs):
        candidate = dict(base)
        for field_index, (field_name, low, high) in enumerate(fields):
            sample_seed = seed + member * int("65537") + field_index * int("104729")
            value = _literals(sample_seed, 1, low, high)[0]
            candidate[field_name] = value
        simulated = _simulate(rows, poa, parameters, _validate(candidate), record_hourly=False)
        summary, _ = _summarise(simulated, _validate(candidate), len(rows))
        results.append(
            {
                "member": member,
                "solar_heating_fraction": summary["solar_heating_fraction"],
                "self_sufficiency": summary["self_sufficiency"],
                "payback_years": summary["payback_years"],
            }
        )
    return results


def _band(values: list[float | None]) -> dict[str, float]:
    ordered = sorted(
        float(value)
        for value in values
        if isinstance(value, (int, float)) and math.isfinite(value)
    )
    if not ordered:
        return {"p05": 0.0, "median": 0.0, "p95": 0.0}
    return {
        "p05": _quantile(ordered, 0.05),
        "median": _quantile(ordered, 0.5),
        "p95": _quantile(ordered, 0.95),
    }


def run_design_screening(
    project_root: Path,
    weather_path: Path,
    overrides: dict[str, Any] | None = None,
    *,
    with_experiments: bool = True,
) -> DesignResult:
    """Run the interactive whole-system screening calculation.

    PVT physics comes from the validated project parameters and the existing
    coupled collector solver. Facility sizing comes from the user's changes.
    """
    inputs = _validate(overrides)
    parameters = load_pvt_parameters(project_root / "inputs" / "parameters")
    rows, interval_seconds = load_pvt_weather(weather_path)
    if interval_seconds != SECONDS_PER_HOUR:
        raise ValueError("Design mode currently needs hourly weather records.")
    poa = _solar_geometry(rows, parameters)

    simulated = _simulate(rows, poa, parameters, inputs, record_hourly=True)
    summary, drivers = _summarise(simulated, inputs, len(rows))
    sensitivity = []
    if with_experiments:
        for sweep in ("collector_area", "tank_volume", "battery_capacity"):
            sensitivity.append(
                {"parameter": sweep, "points": experiment(rows, poa, parameters, inputs, sweep)}
            )
        members = ensemble(rows, poa, parameters, inputs)
        band = {
            key: _band([member[key] for member in members])
            for key in ("solar_heating_fraction", "self_sufficiency", "payback_years")
        }
    else:
        members = []
        band = {}
    summary["sensitivity"] = sensitivity
    summary["ensemble"] = band

    assumptions = [
        {
            "name": "Scope",
            "value": "Interactive screening only",
            "note": "Recombines validated PVT physics with simplified storage, draw, RO, and dispatch; not the report's full transient model or TRNSYS cross-check.",
        },
        {
            "name": "Weather window",
            "value": f"{len(rows):,} hourly records",
            "note": "Annual figures scale this window to 365 days; a single-season file is not a full-year result.",
        },
        {
            "name": "Draw profile",
            "value": f"{inputs.draw_strategy.replace('_', ' ')}, {inputs.draw_peaking:g}× evening",
            "note": "Hourly fractions are screening assumptions, not measured villa data.",
        },
        {
            "name": "Tank",
            "value": f"{inputs.tank_volume:g} L, UA {inputs.tank_heat_loss:g} W/K",
            "note": "One well-mixed node; no stratification, pipe loss, or draw-induced mixing.",
        },
        {
            "name": "Pump control",
            "value": f"set-gain {inputs.pump_set_gain:g} K, cut-out {inputs.ambient_cutout:g} K",
            "note": "Irradiance- and tank-temperature threshold controller with hysteresis; pump power is fixed.",
        },
        {
            "name": "Backup heat",
            "value": (
                f"COP {inputs.auxiliary_cop:g}"
                if inputs.auxiliary_cop > 1.0 + float("1e-9")
                else f"η {inputs.backup_efficiency:g}"
            ),
            "note": "Covers only the draw energy the tank could not supply; no standby loss.",
        },
        {
            "name": "Electrical bus",
            "value": inputs.electrical_mode.replace("_", " "),
            "note": "PVT DC, pump, RO, and backup loads share one bus; battery round-trip efficiency is split symmetrically. Grid-tied surplus is exported; island surplus is curtailed.",
        },
        {
            "name": "Reverse osmosis",
            "value": f"{inputs.ro_recovery * 100:g}% recovery",
            "note": "Product and brine flows follow report Eq. (6); contaminants, pressure, and membrane fouling are not modelled.",
        },
        {
            "name": "Economics",
            "value": f"{inputs.lifetime:g} years, {inputs.discount_rate * 100:g}% discount",
            "note": "Simple payback compares annual net-import cost with an electric-geyser plus bottled-water baseline; capital/tariffs are user assumptions, not calibrated report inputs.",
        },
    ]
    status = {
        "converged": simulated["nonconverged"] == 0,
        "nonconverged_steps": simulated["nonconverged"],
        "steps": len(rows),
        "sunny_steps": simulated["sunny_steps"],
        "ensemble_runs": len(members),
        "scope": "screening",
    }
    return DesignResult(
        inputs=asdict(inputs),
        hourly=simulated["hourly"],
        summary=summary,
        drivers=drivers,
        assumptions=assumptions,
        status=status,
        ensemble=members,
    )
