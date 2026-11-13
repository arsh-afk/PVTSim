"""Tank module tests."""

from __future__ import annotations

import pytest

from aquasolar.tank.grid import TankGrid, create_tank_grid, tank_grid_state
from aquasolar.tank.step import tank_step
from aquasolar.tank.mixing import ideal_mixing, stratified_mixing, partial_mixing, mixing_energy_check
from aquasolar.tank.draw import draw_from_tank, draw_profile
from aquasolar.tank.auxiliary_heating import aux_heating


class TestTankGrid:
    """Tests for TankGrid data structure."""

    def test_grid_initialization(self):
        grid = TankGrid(
            n_nodes=1 + (1 + 1) * (1 + 1),  # 5 nodes
            volume_total=float("0.3"),
            height=float("1.5"),
            diameter=float("0.5"),
        )
        assert grid.n_nodes == 5
        assert len(grid.T) == 5
        assert len(grid.m) == 5
        assert grid.average_temperature() == pytest.approx(float("293.15"))

    def test_temperature_set_get(self):
        grid = TankGrid(3, float("0.3"), float("1.5"), float("0.5"))
        grid.set_temperature(0, float("330.0"))
        assert grid.get_temperature(0) == float("330.0")
        assert grid.top_temperature() == float("330.0")

    def test_energy_conservation(self):
        grid = TankGrid(3, float("0.3"), float("1.5"), float("0.5"))
        e1 = grid.total_energy()
        assert e1 > 0.0


class TestTankMixing:
    """Tests for mixing models."""

    def test_ideal_mixing_energy_conserved(self):
        T = [float("340.0"), float("320.0"), float("300.0")]
        m = [float("50.0"), float("50.0"), float("50.0")]
        T_new = ideal_mixing(T, m)

        # Uniform
        assert T_new[0] == T_new[1] == T_new[2]
        assert T_new[0] == pytest.approx(float("320.0"))

        # Energy conservation check
        check = mixing_energy_check(T, T_new, m)
        assert check["difference"] == pytest.approx(0.0, abs=float("1e-6"))

    def test_stratified_stable_no_mix(self):
        # Hot on top, cold on bottom (stable) -> no change
        T = [float("340.0"), float("320.0"), float("300.0")]
        m = [float("50.0"), float("50.0"), float("50.0")]
        T_new = stratified_mixing(T, m, float("0.5"))
        assert T_new == T

    def test_stratified_unstable_mixes(self):
        # Cold on top, hot below (unstable) -> should mix adjacent
        T = [float("300.0"), float("340.0"), float("300.0")]
        m = [float("50.0"), float("50.0"), float("50.0")]
        T_new = stratified_mixing(T, m, float("0.5"))
        assert T_new[0] > float("300.0")  # Top got warmer


class TestTankDraw:
    """Tests for domestic hot water draw."""

    def test_draw_hot_water(self):
        grid = TankGrid(3, float("0.3"), float("1.5"), float("0.5"))
        grid.set_temperature(0, float("340.0"))
        grid.set_temperature(1, float("330.0"))
        grid.set_temperature(2, float("310.0"))

        vol, temp, ledger = draw_from_tank(
            grid=grid,
            draw_volume=float("0.02"),
            target_temp=float("323.15"),  # 50°C
            T_cold=float("293.15"),       # 20°C
        )
        assert vol > 0.0
        assert temp == pytest.approx(float("323.15"), abs=float("0.5"))
        assert ledger["hot_volume"] > 0.0


class TestAuxHeater:
    """Tests for auxiliary electric heating."""

    def test_aux_turns_on_when_cold(self):
        grid = TankGrid(3, float("0.3"), float("1.5"), float("0.5"))
        # Top is at 293.15 K, target is 328.15 K (55°C)
        Q_aux, ledger = aux_heating(
            grid=grid,
            target_temp=float("328.15"),
            max_power=float("2000.0"),
            efficiency=1.0,
            deadband=float("2.0"),
            dt=float("60.0"),
        )
        assert Q_aux > 0.0
        assert ledger["status"] == "heating"
        assert grid.top_temperature() > float("293.15")

    def test_aux_stays_off_when_hot(self):
        grid = TankGrid(3, float("0.3"), float("1.5"), float("0.5"))
        grid.set_temperature(0, float("335.0"))
        Q_aux, ledger = aux_heating(
            grid=grid,
            target_temp=float("328.15"),
            max_power=float("2000.0"),
        )
        assert Q_aux == 0.0
        assert ledger["status"] == "off"
