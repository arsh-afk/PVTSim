"""PVT module tests."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from aquasolar.pvt.electrical import electrical_output, electrical_output_series
from aquasolar.pvt.thermal import useful_heat, useful_heat_no_flow
from aquasolar.pvt.pv_only import pv_only_reference
from aquasolar.pvt.collector import pvt_solve, PVTCoupledResult
from aquasolar.pvt.coupled import coupled_solve


class TestElectricalOutput:
    """Tests for PVT electrical output."""

    def test_basic_output(self):
        """Test basic electrical output calculation."""
        T_cell = float("320.0")  # 47°C
        G_eff = float("800.0")  # W/m²
        eta_ref = float("0.18")
        T_ref = float("298.15")  # 25°C
        beta = float("-0.004")  # 1/K
        phi_soil = float("0.95")
        A = float("2.0")  # m²

        P_el, ledger = electrical_output(T_cell, G_eff, eta_ref, T_ref, beta, phi_soil, A)

        assert P_el > 0.0
        assert P_el < G_eff * A  # Efficiency < 1
        assert ledger["component"] == "pvt_electrical"
        assert ledger["quantity"] == "electrical_power"

    def test_temperature_coefficient(self):
        """Test that higher temperature reduces efficiency."""
        eta_ref = float("0.18")
        T_ref = float("298.15")
        beta = float("0.004")  # Positive coefficient means efficiency drops with temperature
        G_eff = float("800.0")
        phi_soil = float("1.0")
        A = float("2.0")

        T_cold = float("300.0")
        T_hot = float("350.0")

        P_cold, _ = electrical_output(T_cold, G_eff, eta_ref, T_ref, beta, phi_soil, A)
        P_hot, _ = electrical_output(T_hot, G_eff, eta_ref, T_ref, beta, phi_soil, A)

        assert P_cold > P_hot

    def test_zero_irradiance(self):
        """Test zero output when no irradiance."""
        P_el, _ = electrical_output(float("300.0"), float("0.0"), float("0.18"), float("298.15"), float("-0.004"), float("1.0"), float("2.0"))
        assert P_el == 0.0

    def test_soiling_factor(self):
        """Test soiling factor reduces output."""
        G_eff = float("800.0")
        A = float("2.0")
        eta_ref = float("0.18")
        T_ref = float("298.15")
        beta = float("-0.004")

        P_clean, _ = electrical_output(float("300.0"), G_eff, eta_ref, T_ref, beta, float("1.0"), A)
        P_soiled, _ = electrical_output(float("300.0"), G_eff, eta_ref, T_ref, beta, float("0.8"), A)

        assert P_soiled < P_clean


class TestThermalOutput:
    """Tests for PVT thermal output."""

    def test_basic_output(self):
        """Test basic thermal output calculation."""
        T_f_in = float("300.0")
        m_dot = float("0.02")  # kg/s
        G_eff = float("800.0")
        P_el = float("200.0")
        T_amb = float("290.0")
        wind_speed = float("2.0")
        A = float("2.0")
        tau_alpha = float("0.85")
        F_R = float("0.9")
        U_L = float("5.0")  # W/(m²·K)

        Q_u, ledger = useful_heat(T_f_in, m_dot, G_eff, P_el, T_amb, wind_speed, A, tau_alpha, F_R, U_L)

        assert isinstance(Q_u, float)
        assert ledger["component"] == "pvt_thermal"

    def test_no_flow(self):
        """Test thermal output with no flow."""
        G_eff = float("800.0")
        T_amb = float("290.0")
        A = float("2.0")
        tau_alpha = float("0.85")
        U_L = float("5.0")

        Q_u, ledger = useful_heat_no_flow(G_eff, T_amb, A, tau_alpha, U_L)

        assert Q_u == 0.0


class TestPVOnlyReference:
    """Tests for PV-only reference."""

    def test_pv_only_basic(self):
        """Test PV-only reference output."""
        G_eff = float("800.0")
        T_amb = float("290.0")
        wind_speed = float("2.0")
        eta_ref = float("0.18")
        T_ref = float("298.15")
        beta = float("-0.004")
        phi_soil = float("1.0")
        A = float("2.0")

        T_cell, P_el, ledger = pv_only_reference(
            G_eff, T_amb, wind_speed, eta_ref, T_ref, beta, phi_soil, A,
            pv_only_model="simple"
        )

        assert T_cell > T_amb
        assert P_el >= 0.0
        assert "component" in ledger


class TestCollectorSolve:
    """Tests for coupled PVT solver."""

    @pytest.fixture
    def registry(self):
        """Create a test registry."""
        return {
            "pvt_el.eta_ref": float("0.18"),
            "pvt_el.T_ref": float("298.15"),
            "pvt_el.beta": float("-0.004"),
            "pvt_th.collector_area": float("2.0"),
            "pvt_th.tau_alpha": float("0.85"),
            "pvt_th.F_R": float("0.9"),
            "pvt_th.U_L": float("5.0"),
            "pvt_th.R_cell_fluid": float("0.1"),
            "loop.fluid_cp": float("4180.0"),
            "soiling_factor": float("1.0"),
        }

    def test_pvt_solve(self, registry):
        """Test basic PVT solve."""
        result = pvt_solve(
            T_in=float("300.0"),
            m_dot=float("0.02"),
            G_eff=float("800.0"),
            T_amb=float("290.0"),
            wind_speed=float("2.0"),
            registry=registry,
        )

        assert isinstance(result, PVTCoupledResult)
        assert result.converged
        assert result.P_el >= 0.0
        assert result.T_f_out >= result.T_f_in

    def test_coupled_heat_uses_registered_inlet_temperature_equation(self, registry):
        T_in = float("300.0")
        G_eff = float("800.0")
        T_amb = float("290.0")

        T_out, _T_cell, P_el, Q_u, converged, _iterations = coupled_solve(
            T_in=T_in,
            m_dot=float("0.02"),
            G_eff=G_eff,
            T_amb=T_amb,
            wind_speed=float("2.0"),
            registry=registry,
        )

        absorbed_power_per_area = (
            registry["pvt_th.tau_alpha"] * G_eff
            - P_el / registry["pvt_th.collector_area"]
        )
        expected_Q_u = registry["pvt_th.collector_area"] * registry["pvt_th.F_R"] * (
            absorbed_power_per_area
            - registry["pvt_th.U_L"] * (T_in - T_amb)
        )
        assert converged
        assert T_out > T_in
        assert Q_u == pytest.approx(expected_Q_u)

    def test_coupled_solver_does_not_exceed_fluid_temperature_limit(self, registry):
        registry["pvt_th.T_fluid_max"] = float("301.0")

        T_out, _T_cell, _P_el, _Q_u, converged, _iterations = coupled_solve(
            T_in=float("300.0"),
            m_dot=float("0.02"),
            G_eff=float("800.0"),
            T_amb=float("290.0"),
            wind_speed=float("2.0"),
            registry=registry,
        )

        assert not converged
        assert T_out <= registry["pvt_th.T_fluid_max"]

    def test_zero_flow(self, registry):
        """Test PVT solve with zero flow."""
        result = pvt_solve(
            T_in=float("300.0"),
            m_dot=float("0.0"),
            G_eff=float("800.0"),
            T_amb=float("290.0"),
            wind_speed=float("2.0"),
            registry=registry,
            use_coupled=False,
        )

        assert result.Q_u == 0.0
        assert result.converged

    def test_night_time(self, registry):
        """Test PVT solve at night."""
        result = pvt_solve(
            T_in=float("300.0"),
            m_dot=float("0.02"),
            G_eff=float("0.0"),
            T_amb=float("290.0"),
            wind_speed=float("2.0"),
            registry=registry,
        )

        assert result.P_el == 0.0
        assert result.Q_u <= 0.0  # May lose heat
