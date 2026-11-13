"""Electrical balance module tests."""

from __future__ import annotations

import pytest

from aquasolar.electrical.balance import electrical_balance, battery_dispatch


class TestElectricalBalance:
    """Tests for electrical balance."""

    def test_surplus_export(self):
        """Test surplus PVT exported to grid."""
        flows, ledger = electrical_balance(
            P_pvt=5000.0,
            P_aux_heater=0.0,
            P_pump=100.0,
            P_load=1000.0,
            grid_export_limit=10000.0,
        )

        assert flows["P_grid_export"] > 0.0
        assert flows["P_grid_import"] == 0.0
        assert flows["P_curtailment"] == 0.0

    def test_deficit_import(self):
        """Test deficit imported from grid."""
        flows, ledger = electrical_balance(
            P_pvt=1000.0,
            P_aux_heater=2000.0,
            P_pump=100.0,
            P_load=2000.0,
            grid_import_limit=10000.0,
        )

        assert flows["P_grid_import"] > 0.0
        assert flows["P_grid_export"] == 0.0

    def test_battery_charge(self):
        """Test battery charging from excess PV."""
        flows, ledger = electrical_balance(
            P_pvt=5000.0,
            P_aux_heater=0.0,
            P_pump=100.0,
            P_load=1000.0,
            P_battery_charge=1000.0,
            battery_capacity=10000.0,
            battery_soc=0.5,
        )

        assert flows["P_battery_charge"] == 1000.0
        assert flows["battery_soc"] > 0.5

    def test_battery_discharge(self):
        """Test battery discharging to meet load."""
        flows, ledger = electrical_balance(
            P_pvt=1000.0,
            P_aux_heater=0.0,
            P_pump=100.0,
            P_load=3000.0,
            P_battery_discharge=1000.0,
            battery_capacity=10000.0,
            battery_soc=0.8,
        )

        assert flows["P_battery_discharge"] == 1000.0
        assert flows["battery_soc"] < 0.8

    def test_export_curtailment(self):
        """Test export curtailment when grid limit reached."""
        flows, ledger = electrical_balance(
            P_pvt=10000.0,
            P_aux_heater=0.0,
            P_pump=100.0,
            P_load=1000.0,
            grid_export_limit=5000.0,
        )

        assert flows["P_grid_export"] == 5000.0
        assert flows["P_curtailment"] > 0.0


class TestBatteryDispatch:
    """Tests for battery dispatch strategies."""

    def test_self_consumption_charge(self):
        """Test charging from excess PV."""
        charge, discharge, reason = battery_dispatch(
            P_pvt=5000.0,
            P_load=2000.0,
            battery_soc=0.5,
            battery_capacity=10000.0,
            battery_max_charge=3000.0,
            battery_max_discharge=3000.0,
            grid_import_price=0.30,
            grid_export_price=0.10,
            strategy="self_consumption",
        )

        assert charge > 0.0
        assert discharge == 0.0
        assert reason == "charge_excess_pv"

    def test_self_consumption_discharge(self):
        """Test discharging to meet load."""
        charge, discharge, reason = battery_dispatch(
            P_pvt=1000.0,
            P_load=3000.0,
            battery_soc=0.8,
            battery_capacity=10000.0,
            battery_max_charge=3000.0,
            battery_max_discharge=3000.0,
            grid_import_price=0.30,
            grid_export_price=0.10,
            strategy="self_consumption",
        )

        assert charge == 0.0
        assert discharge > 0.0
        assert reason == "discharge_for_load"

    def test_soc_limits(self):
        """Test SOC limits respected."""
        # Full battery - no charging
        charge, discharge, _ = battery_dispatch(
            P_pvt=5000.0,
            P_load=1000.0,
            battery_soc=1.0,
            battery_capacity=10000.0,
            battery_max_charge=3000.0,
            battery_max_discharge=3000.0,
            grid_import_price=0.30,
            grid_export_price=0.10,
            strategy="self_consumption",
        )
        assert charge == 0.0

        # Empty battery - no discharging
        charge, discharge, _ = battery_dispatch(
            P_pvt=1000.0,
            P_load=3000.0,
            battery_soc=0.0,
            battery_capacity=10000.0,
            battery_max_charge=3000.0,
            battery_max_discharge=3000.0,
            grid_import_price=0.30,
            grid_export_price=0.10,
            strategy="self_consumption",
        )
        assert discharge == 0.0
