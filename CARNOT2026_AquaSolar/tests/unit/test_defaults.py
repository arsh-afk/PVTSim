"""Tests for the source-labelled exploratory input preset."""

from __future__ import annotations

import yaml

from aquasolar.defaults import apply_demo_defaults


def _write_parameters(root):
    parameter_dir = root / "inputs" / "parameters"
    parameter_dir.mkdir(parents=True)
    (parameter_dir / "demo.yaml").write_text(
        "# Preserve this comment\n"
        "parameters:\n"
        "  - id: site.latitude\n"
        "    quantity_kind: angle\n"
        "    value: null\n"
        "    unit: null\n"
        "    status: draft\n"
        "  - id: demo.fraction\n"
        "    quantity_kind: fraction\n"
        "    value: null\n"
        "    unit: null\n"
        "    status: draft\n"
        "  - id: pvt_th.T_fluid_max\n"
        "    quantity_kind: temperature\n"
        "    value: null\n"
        "    unit: K\n"
        "    status: draft\n",
        encoding="utf-8",
    )
    return parameter_dir / "demo.yaml"


def test_demo_defaults_are_reproducible_source_labelled_and_idempotent(tmp_path):
    file_path = _write_parameters(tmp_path)

    first = apply_demo_defaults(tmp_path)
    first_data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    first_values = {
        row["id"]: row["value"] for row in first_data["parameters"]
    }
    manifest_path = tmp_path / "inputs" / "provenance" / "demo_defaults.yaml"

    assert first["updated"] == 2
    assert first_data["parameters"][0]["value"] == 25.79
    assert first_data["parameters"][0]["source_type"] == "literature"
    assert first_data["parameters"][0]["source_ref"].endswith(
        "AquaSolar_TRNSYS_Master_Direction.md#3.2"
    )
    assert first_data["parameters"][1]["source_type"] == "assumption"
    assert first_data["parameters"][1]["source_ref"].endswith(
        "demo_defaults.yaml#demo.fraction"
    )
    unresolved_limit = first_data["parameters"][2]
    assert unresolved_limit["value"] is None
    assert unresolved_limit["status"] == "draft"
    assert "# Preserve this comment" in file_path.read_text(encoding="utf-8")

    second = apply_demo_defaults(tmp_path)
    second_data = yaml.safe_load(file_path.read_text(encoding="utf-8"))

    assert second["updated"] == 0
    assert {row["id"]: row["value"] for row in second_data["parameters"]} == first_values
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest_rows = {row["id"]: row for row in manifest["parameters"]}
    assert manifest_rows["site.latitude"]["generated_by_this_preset"]
    assert manifest_rows["demo.fraction"]["generated_by_this_preset"]
    assert manifest_rows["pvt_th.T_fluid_max"]["value"] is None
    assert not manifest_rows["pvt_th.T_fluid_max"]["generated_by_this_preset"]
