"""Tests for the input and output definitions shown by the desktop UI."""

from aquasolar.ui import (
    STEP_OUTPUTS,
    SUMMARY_OUTPUTS,
    available_weather_files,
    load_data_input_catalog,
    load_metric_catalog,
    load_parameter_catalog,
    read_pvt_series,
    save_parameter_entry,
)


def test_parameter_catalog_covers_every_parameter_file():
    parameters = load_parameter_catalog()

    assert parameters
    assert len({row["id"] for row in parameters}) == len(parameters)
    assert all(row["file"].exists() for row in parameters)
    assert all(
        row["source_type"]
        == (row["parameter"].get("source_type") or "unassigned")
        for row in parameters
    )
    assert all(
        row["source_ref"]
        == (row["parameter"].get("source_ref") or "No source recorded")
        for row in parameters
    )


def test_data_catalog_includes_weather_fields():
    data_inputs = load_data_input_catalog()

    assert any(
        row["file"].endswith("weather.csv")
        and row["name"] == "ghi"
        and row["source"] != "Not specified"
        for row in data_inputs
    )


def test_metric_catalog_includes_all_registered_groups():
    metrics = load_metric_catalog()

    assert len(metrics) == 39
    assert {metric["id"][:4] for metric in metrics} >= {
        "M-PV",
        "M-TH",
        "M-EL",
        "M-WQ",
        "M-MN",
        "M-EC",
        "M-EN",
        "M-SC",
    }


def test_output_definitions_include_source_labels():
    assert STEP_OUTPUTS
    assert SUMMARY_OUTPUTS
    assert all(len(output) == 4 and output[3] for output in STEP_OUTPUTS)
    assert all(len(output) == 4 and output[3] for output in SUMMARY_OUTPUTS)


def test_weather_file_picker_only_lists_compatible_csvs(tmp_path):
    (tmp_path / "weather.csv").write_text(
        "timestamp,ghi,dni,dhi,t_ambient,wind_speed\n",
        encoding="utf-8",
    )
    (tmp_path / "not_weather.csv").write_text(
        "timestamp,temperature\n",
        encoding="utf-8",
    )

    assert available_weather_files(tmp_path) == [str(tmp_path / "weather.csv")]


def test_result_series_reader_loads_timestamps_and_numeric_columns(tmp_path):
    result_path = tmp_path / "scenario.csv"
    result_path.write_text(
        "timestamp,POA_W_m2,GHI_W_m2,T_ambient_K,T_f_out_K,T_cell_K,"
        "P_el_W,Q_u_W,E_el_Wh,E_heat_Wh\n"
        "2025-01-01T10:00:00+00:00,800,600,293,300,305,120,250,120,250\n",
        encoding="utf-8",
    )

    rows = read_pvt_series(result_path)

    assert rows[0]["timestamp"].isoformat() == "2025-01-01T10:00:00+00:00"
    assert rows[0]["P_el_W"] == 120
    assert rows[0]["Q_u_W"] == 250


def test_saving_parameter_preserves_yaml_comments(tmp_path):
    parameter_file = tmp_path / "site.yaml"
    parameter_file.write_text(
        "parameters:\n"
        "  - id: site.latitude\n"
        "    description: Site latitude # keep this comment\n"
        "    value: null\n"
        "    unit: null\n"
        "    status: draft\n"
        "    uncertainty:\n"
        "      kind: null\n"
        "      value: null\n"
        "      distribution: null\n"
        "    valid_range:\n"
        "      min: null\n"
        "      max: null\n",
        encoding="utf-8",
    )

    save_parameter_entry(
        parameter_file,
        "site.latitude",
        {
            "id": "site.latitude",
            "value": 25.8,
            "unit": "degree",
            "status": "confirmed",
            "uncertainty": {},
            "valid_range": {},
        },
    )

    saved = parameter_file.read_text(encoding="utf-8")
    assert "value: 25.8" in saved
    assert "status: confirmed" in saved
    assert "# keep this comment" in saved
