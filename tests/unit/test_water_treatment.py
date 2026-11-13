"""Water treatment module tests."""

from __future__ import annotations

import pytest

from aquasolar.water_treatment.stages import (
    sediment_filter,
    carbon_filter,
    uv_disinfection,
    ultrafiltration,
    nanofiltration,
    remineralization,
)
from aquasolar.water_treatment.train import pathway_a, pathway_b, pathway_c, run_treatment_train


class TestSedimentFilter:
    """Tests for sediment filter stage."""

    def test_removes_turbidity_and_tss(self):
        quality_in = {"turbidity": 10.0, "tss": 50.0}
        parameters = {"turbidity_removal": 0.95, "tss_removal": 0.90}

        quality_out, ledger = sediment_filter(0.001, quality_in, 60.0, parameters)

        assert quality_out["turbidity"] == pytest.approx(0.5)
        assert quality_out["tss"] == pytest.approx(5.0)
        assert ledger["stage"] == "sediment_filter"


class TestCarbonFilter:
    """Tests for carbon filter stage."""

    def test_removes_organics_and_chlorine(self):
        quality_in = {"doc": 5.0, "chlorine": 1.0, "voc": 0.5}
        parameters = {"doc_removal": 0.8, "chlorine_removal": 0.99, "voc_removal": 0.9}

        quality_out, ledger = carbon_filter(0.001, quality_in, 60.0, parameters)

        assert quality_out["doc"] == pytest.approx(1.0)
        assert quality_out["chlorine"] == pytest.approx(0.01)
        assert quality_out["voc"] == pytest.approx(0.05)


class TestUVDisinfection:
    """Tests for UV disinfection stage."""

    def test_log_reduction(self):
        quality_in = {"ecoli": 10000.0, "total_coliform": 50000.0, "virus": 1000.0}
        parameters = {"uv_dose": 40.0, "log_reduction_bacteria": 4.0, "log_reduction_virus": 3.0}

        quality_out, ledger = uv_disinfection(0.001, quality_in, 60.0, parameters)

        assert quality_out["ecoli"] == pytest.approx(1.0)
        assert quality_out["total_coliform"] == pytest.approx(5.0)
        assert quality_out["virus"] == pytest.approx(1.0)


class TestUltrafiltration:
    """Tests for ultrafiltration stage."""

    def test_high_log_removal(self):
        quality_in = {"tss": 100.0, "turbidity": 20.0, "ecoli": 1000.0, "virus": 100.0}
        parameters = {
            "tss_removal": 6.0, "turbidity_removal": 5.0,
            "bacteria_removal": 6.0, "virus_removal": 4.0
        }

        quality_out, ledger = ultrafiltration(0.001, quality_in, 60.0, parameters)

        assert quality_out["tss"] <= 100.0 * 1e-6
        assert quality_out["turbidity"] <= 20.0 * 1e-5
        assert quality_out["ecoli"] <= 1000.0 * 1e-6


class TestNanofiltration:
    """Tests for nanofiltration stage."""

    def test_removes_hardness_and_tds(self):
        quality_in = {"hardness": 200.0, "doc": 5.0, "tds": 500.0, "ecoli": 1000.0}
        parameters = {
            "hardness_removal": 0.9, "doc_removal": 0.95,
            "sulfate_removal": 0.9, "tds_removal": 0.7,
            "bacteria_removal": 6.0, "virus_removal": 4.0
        }

        quality_out, ledger = nanofiltration(0.001, quality_in, 60.0, parameters)

        assert quality_out["hardness"] == pytest.approx(20.0)
        assert quality_out["doc"] == pytest.approx(0.25)
        assert quality_out["tds"] == pytest.approx(150.0)


class TestRemineralization:
    """Tests for remineralization stage."""

    def test_adds_minerals(self):
        quality_in = {"hardness": 10.0, "alkalinity": 10.0, "ph": 5.5}
        parameters = {"target_hardness": 100.0, "target_alkalinity": 80.0, "target_ph": 7.5}

        quality_out, ledger = remineralization(0.001, quality_in, 60.0, parameters)

        assert quality_out["hardness"] == 100.0
        assert quality_out["alkalinity"] == 80.0
        assert quality_out["ph"] == 7.5
        assert ledger["hardness_added"] == 90.0


class TestPathways:
    """Tests for complete treatment pathways."""

    def test_pathway_a(self):
        quality_in = {"turbidity": 10.0, "doc": 5.0, "ecoli": 1000.0}
        parameters = {
            "sediment": {"turbidity_removal": 0.95, "tss_removal": 0.9},
            "carbon": {"doc_removal": 0.8, "chlorine_removal": 0.99, "voc_removal": 0.9},
            "uv": {"uv_dose": 40.0, "log_reduction_bacteria": 4.0, "log_reduction_virus": 3.0},
        }

        quality_out, ledgers = pathway_a(0.001, quality_in, 60.0, parameters)

        assert len(ledgers) == 3
        assert quality_out["turbidity"] < quality_in["turbidity"]
        assert quality_out["doc"] < quality_in["doc"]
        assert quality_out["ecoli"] < quality_in["ecoli"]

    def test_pathway_b(self):
        quality_in = {"turbidity": 20.0, "tss": 100.0, "ecoli": 10000.0, "virus": 1000.0}
        parameters = {
            "sediment": {"turbidity_removal": 0.95, "tss_removal": 0.9},
            "carbon": {"doc_removal": 0.8, "chlorine_removal": 0.99, "voc_removal": 0.9},
            "uf": {"tss_removal": 6.0, "turbidity_removal": 5.0, "bacteria_removal": 6.0, "virus_removal": 4.0},
            "uv": {"uv_dose": 40.0, "log_reduction_bacteria": 4.0, "log_reduction_virus": 3.0},
        }

        quality_out, ledgers = pathway_b(0.001, quality_in, 60.0, parameters)

        assert len(ledgers) == 4
        assert quality_out["ecoli"] < 1.0

    def test_pathway_c(self):
        quality_in = {"hardness": 300.0, "tds": 800.0, "ecoli": 1000.0}
        parameters = {
            "nf": {"hardness_removal": 0.9, "doc_removal": 0.95, "sulfate_removal": 0.9, "tds_removal": 0.7, "bacteria_removal": 6.0, "virus_removal": 4.0},
            "remin": {"target_hardness": 100.0, "target_alkalinity": 80.0, "target_ph": 7.5},
            "uv": {"uv_dose": 40.0, "log_reduction_bacteria": 4.0, "log_reduction_virus": 3.0},
        }

        quality_out, ledgers = pathway_c(0.001, quality_in, 60.0, parameters)

        assert len(ledgers) == 3
        assert quality_out["hardness"] == 100.0  # Remineralized
        assert quality_out["tds"] < quality_in["tds"]

    def test_run_treatment_train(self):
        quality_in = {"turbidity": 10.0, "ecoli": 1000.0}
        parameters = {
            "sediment": {"turbidity_removal": 0.95, "tss_removal": 0.9},
            "carbon": {"doc_removal": 0.8, "chlorine_removal": 0.99, "voc_removal": 0.9},
            "uv": {"uv_dose": 40.0, "log_reduction_bacteria": 4.0, "log_reduction_virus": 3.0},
        }

        quality_out, ledgers = run_treatment_train("A", 0.001, quality_in, 60.0, parameters)
        assert len(ledgers) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
