"""API tests for the local browser input workbench."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from aquasolar import cli
from aquasolar.pvt.runner import _REQUIRED_PARAMETERS
from aquasolar.web import create_app


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _make_project(root: Path) -> None:
    _write_yaml(
        root / "inputs" / "input_index.yaml",
        {
            "parameters": [
                {
                    "file": "demo",
                    "id": "demo.limit",
                    "kind": "fraction",
                    "required_when": "always",
                    "allowed": None,
                }
            ]
        },
    )
    parameter_path = root / "inputs" / "parameters" / "demo.yaml"
    parameter_path.parent.mkdir(parents=True, exist_ok=True)
    parameter_path.write_text(
        "parameters:\n"
        "  - id: demo.limit # preserve this note\n"
        "    description: Demo limit\n"
        "    value: 0.5\n"
        "    unit: '1'\n"
        "    status: confirmed\n"
        "    source_type: assumption\n"
        "    source_ref: test fixture\n"
        "    valid_range:\n"
        "      min: 0.0\n"
        "      max: 1.0\n",
        encoding="utf-8",
    )
    for folder, filename, content, columns in (
        (
            "tables",
            "sample.csv",
            "sample_id,value\nA,1\n",
            [
                {"name": "sample_id", "required": True},
                {
                    "name": "value",
                    "required": True,
                    "quantity_kind": "count",
                },
            ],
        ),
        (
            "timeseries",
            "weather.csv",
            "timestamp,ghi\n2025-01-01T00:00:00+00:00,0\n",
            [
                {
                    "name": "timestamp",
                    "required": True,
                    "quantity_kind": "timestamp",
                },
                {
                    "name": "ghi",
                    "required": True,
                    "quantity_kind": "irradiance",
                    "unit": "W/m2",
                },
            ],
        ),
    ):
        meta_path = root / "inputs" / folder / f"{Path(filename).stem}.meta.yaml"
        _write_yaml(
            meta_path,
            {
                "file": filename,
                "delimiter": "comma",
                "decimal_separator": "period",
                "header_row": True,
                "interval": "1 hour" if folder == "timeseries" else None,
                "columns": columns,
            },
        )
        meta_path.with_name(filename).write_text(content, encoding="utf-8")
    _write_yaml(
        root / "inputs" / "module_registry.yaml",
        {
            "modules": [
                {
                    "id": "pvt_runner",
                    "name": "PVT runner",
                    "operational_status": "operational",
                    "enabled": True,
                    "parameter_files": ["demo"],
                    "parameter_ids": ["demo.limit"],
                    "data_kinds": ["timeseries"],
                    "requirements": ["Complete the PVT input set."],
                    "description": "Test PVT runner.",
                },
                {
                    "id": "tank_storage",
                    "name": "Tank storage",
                    "operational_status": "prototype",
                    "enabled": False,
                    "parameter_files": ["demo"],
                    "data_kinds": [],
                    "requirements": ["Complete tank requirements."],
                    "description": "Test unintegrated module.",
                },
            ]
        },
    )


def test_web_catalog_and_validation_endpoints_load_project(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))

    page = client.get("/")
    catalog = client.get("/api/catalog")
    report = client.get("/api/validation")

    assert page.status_code == 200
    assert "AquaSolar" in page.text
    assert catalog.status_code == 200
    assert [row["id"] for row in catalog.json()["parameters"]] == ["demo.limit"]
    assert len(catalog.json()["data_files"]) == 2
    assert report.status_code == 200
    assert report.json()["ok"] is True
    modules = client.get("/api/modules")
    assert modules.status_code == 200
    tank = next(
        module for module in modules.json() if module["id"] == "tank_storage"
    )
    assert tank["readiness"] == "not_operational"
    assert tank["requirements"] == ["Complete tank requirements."]


def test_model_trace_matches_runner_requirements_and_uses_valid_graph_edges(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))

    trace = client.get("/api/model/trace")

    assert trace.status_code == 200
    payload = trace.json()
    assert payload["required_parameter_ids"] == list(_REQUIRED_PARAMETERS)
    node_ids = {
        row["id"]
        for key in ("inputs", "steps", "outputs")
        for row in payload[key]
    }
    assert all(
        edge["source"] in node_ids and edge["target"] in node_ids
        for edge in payload["edges"]
    )
    assert {"hourly_csv", "summary_json"} <= {
        output["id"] for output in payload["outputs"]
    }


def test_module_toggles_require_preview_and_disable_pvt_runs(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    registry_path = tmp_path / "inputs" / "module_registry.yaml"
    original_registry = registry_path.read_text(encoding="utf-8")
    changes = {"module_overrides": {"pvt_runner": False}}

    preview = client.post("/api/validation/preview", json=changes)

    assert preview.status_code == 200
    assert registry_path.read_text(encoding="utf-8") == original_registry
    applied = client.post(
        "/api/validation/apply",
        json={
            **changes,
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
        },
    )

    assert applied.status_code == 200
    saved_modules = yaml.safe_load(registry_path.read_text(encoding="utf-8"))["modules"]
    pvt_module = next(module for module in saved_modules if module["id"] == "pvt_runner")
    assert pvt_module["enabled"] is False
    assert pvt_module["operational_status"] == "operational"
    readiness = client.get(
        "/api/run-readiness", params={"weather": "inputs/timeseries/weather.csv"}
    )
    assert readiness.status_code == 200
    assert any(
        issue["code"] == "module.pvt_runner.disabled"
        for issue in readiness.json()["issues"]
    )
    blocked_run = client.post(
        "/api/runs",
        json={
            "scenario_id": "disabled-pvt",
            "weather": "inputs/timeseries/weather.csv",
        },
    )
    assert blocked_run.status_code == 409
    assert any(
        issue["code"] == "module.pvt_runner.disabled"
        for issue in blocked_run.json()["detail"]["run_readiness"]["issues"]
    )


def test_enabling_unimplemented_module_does_not_block_pvt_run(tmp_path, monkeypatch):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    from aquasolar import web

    monkeypatch.setattr(web, "load_pvt_parameters", lambda _path: {})
    monkeypatch.setattr(
        web,
        "load_pvt_weather",
        lambda _path: ([{"timestamp": "2025-01-01T00:00:00+00:00"}] * 2, 3600),
    )
    changes = {"module_overrides": {"tank_storage": True}}
    preview = client.post("/api/validation/preview", json=changes)
    applied = client.post(
        "/api/validation/apply",
        json={
            **changes,
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
        },
    )

    assert preview.status_code == 200
    assert applied.status_code == 200
    modules = client.get("/api/modules")
    tank_module = next(
        module for module in modules.json() if module["id"] == "tank_storage"
    )
    assert tank_module["enabled"] is True
    assert tank_module["readiness"] == "not_operational"
    readiness = client.get(
        "/api/run-readiness", params={"weather": "inputs/timeseries/weather.csv"}
    )
    assert readiness.json()["ok"] is True


def test_module_registry_rejects_non_boolean_and_unknown_toggles(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))

    invalid_type = client.post(
        "/api/validation/preview",
        json={"module_overrides": {"pvt_runner": "false"}},
    )
    unknown_id = client.post(
        "/api/validation/preview",
        json={"module_overrides": {"missing_module": True}},
    )

    assert invalid_type.status_code == 422
    assert unknown_id.status_code == 400


def test_cli_run_is_blocked_when_operational_pvt_module_is_disabled(tmp_path, monkeypatch, capsys):
    _make_project(tmp_path)
    registry_path = tmp_path / "inputs" / "module_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    registry["modules"][0]["enabled"] = False
    _write_yaml(registry_path, registry)
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)

    exit_code = cli.cmd_run_pvt_only("disabled-case")

    assert exit_code == 1
    assert "PVT runner is disabled" in capsys.readouterr().err


def test_parameter_preview_and_explicit_apply_preserve_yaml_comments(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    path = tmp_path / "inputs" / "parameters" / "demo.yaml"
    original = path.read_text(encoding="utf-8")
    body = {"parameter_overrides": {"demo.limit": {"value": 0.7}}}

    preview = client.post("/api/validation/preview", json=body)
    not_confirmed = client.post("/api/validation/apply", json=body)

    assert preview.status_code == 200
    assert preview.json()["ok"] is True
    assert preview.json()["preview_token"]
    assert not_confirmed.status_code == 400
    assert path.read_text(encoding="utf-8") == original

    applied = client.post(
        "/api/validation/apply",
        json={
            **body,
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
        },
    )
    assert applied.status_code == 200
    saved = path.read_text(encoding="utf-8")
    assert "value: 0.7" in saved
    assert "# preserve this note" in saved


def test_apply_requires_matching_preview_of_exact_changes(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    path = tmp_path / "inputs" / "parameters" / "demo.yaml"
    original = path.read_text(encoding="utf-8")
    preview = client.post(
        "/api/validation/preview",
        json={"parameter_overrides": {"demo.limit": {"value": 0.7}}},
    )

    stale = client.post(
        "/api/validation/apply",
        json={
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
            "parameter_overrides": {"demo.limit": {"value": 0.8}},
        },
    )
    assert stale.status_code == 409
    assert path.read_text(encoding="utf-8") == original

    applied = client.post(
        "/api/validation/apply",
        json={
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
            "parameter_overrides": {"demo.limit": {"value": 0.7}},
        },
    )
    assert applied.status_code == 200
    assert "value: 0.7" in path.read_text(encoding="utf-8")


def test_file_preview_does_not_write_and_apply_rejects_unsafe_paths(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    path = tmp_path / "inputs" / "tables" / "sample.csv"
    original = path.read_text(encoding="utf-8")
    preview = client.post(
        "/api/validation/preview",
        json={"file_overrides": {"inputs/tables/sample.csv": "sample_id,value\nB,2\n"}},
    )
    rejected = client.post(
        "/api/validation/apply",
        json={
            "confirmed": True,
            "file_overrides": {"inputs/../outside.csv": "bad"},
        },
    )

    assert preview.status_code == 200
    assert path.read_text(encoding="utf-8") == original
    assert rejected.status_code == 400
    assert path.read_text(encoding="utf-8") == original


def _new_weather_uploads(
    filename: str = "weather-alt",
    csv_content: str | None = None,
) -> dict[str, str]:
    csv_name = f"{filename}.csv"
    return {
        f"inputs/timeseries/{csv_name}": csv_content
        or (
            "timestamp,ghi,dni,dhi,t_ambient,wind_speed\n"
            "2025-01-01T10:00:00+00:00,800,600,200,22,2\n"
            "2025-01-01T11:00:00+00:00,700,500,200,23,2\n"
        ),
        f"inputs/timeseries/{filename}.meta.yaml": yaml.safe_dump(
            {
                "file": csv_name,
                "delimiter": "comma",
                "decimal_separator": "period",
                "header_row": True,
                "interval": "1 hour",
                "columns": [
                    {
                        "name": "timestamp",
                        "required": True,
                        "quantity_kind": "timestamp",
                    },
                    *[
                        {
                            "name": name,
                            "required": True,
                            "quantity_kind": kind,
                            "unit": unit,
                        }
                        for name, kind, unit in (
                            ("ghi", "irradiance", "W/m2"),
                            ("dni", "irradiance", "W/m2"),
                            ("dhi", "irradiance", "W/m2"),
                            ("t_ambient", "temperature", "C"),
                            ("wind_speed", None, "m/s"),
                        )
                    ],
                ],
            },
            sort_keys=False,
        ),
    }


def test_new_weather_pair_requires_preview_and_applies_to_catalog(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    uploads = _new_weather_uploads()
    csv_path = tmp_path / "inputs" / "timeseries" / "weather-alt.csv"
    metadata_path = tmp_path / "inputs" / "timeseries" / "weather-alt.meta.yaml"

    preview = client.post(
        "/api/validation/preview", json={"file_overrides": uploads}
    )
    assert preview.status_code == 200
    assert csv_path.exists() is False
    assert metadata_path.exists() is False

    applied = client.post(
        "/api/validation/apply",
        json={
            "file_overrides": uploads,
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
        },
    )

    assert applied.status_code == 200
    assert csv_path.read_text(encoding="utf-8") == uploads[
        "inputs/timeseries/weather-alt.csv"
    ]
    assert metadata_path.exists()
    assert any(
        item["file"] == "inputs/timeseries/weather-alt.csv"
        for item in client.get("/api/catalog").json()["data_files"]
    )
    weather = client.get("/api/weather").json()
    assert any(
        item["file"] == "inputs/timeseries/weather-alt.csv" and item["valid"]
        for item in weather
    )


def test_new_weather_upload_requires_pair_and_rejects_invalid_pair(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))
    uploads = _new_weather_uploads(csv_content="timestamp,ghi\nnot-a-date,invalid\n")
    csv_path = tmp_path / "inputs" / "timeseries" / "weather-alt.csv"
    metadata_path = tmp_path / "inputs" / "timeseries" / "weather-alt.meta.yaml"

    incomplete = client.post(
        "/api/validation/preview",
        json={
            "file_overrides": {
                "inputs/timeseries/weather-alt.csv": uploads[
                    "inputs/timeseries/weather-alt.csv"
                ]
            }
        },
    )
    preview = client.post(
        "/api/validation/preview", json={"file_overrides": uploads}
    )
    rejected = client.post(
        "/api/validation/apply",
        json={
            "file_overrides": uploads,
            "confirmed": True,
            "preview_token": preview.json()["preview_token"],
        },
    )

    assert incomplete.status_code == 400
    assert preview.status_code == 200
    assert preview.json()["error_count"] > 0
    assert rejected.status_code == 422
    assert csv_path.exists() is False
    assert metadata_path.exists() is False


def test_saved_runs_include_historical_input_snapshot(tmp_path):
    _make_project(tmp_path)
    result_dir = tmp_path / "outputs" / "pvt_only"
    result_dir.mkdir(parents=True)
    (result_dir / "snapshot-run.summary.json").write_text(
        json.dumps(
            {
                "scenario_id": "snapshot-run",
                "input_parameters": {
                    "pvt_th.U_L": {
                        "value": 12,
                        "unit": "W/(m2*K)",
                        "source_type": "datasheet",
                        "source_ref": "collector sheet",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (result_dir / "snapshot-run.csv").write_text(
        "timestamp,POA_W_m2,GHI_W_m2,T_ambient_K,T_f_out_K,T_cell_K,"
        "P_el_W,Q_u_W,E_el_Wh,E_heat_Wh\n"
        "2025-01-01T10:00:00+00:00,0,0,295,295,295,0,0,0,0\n",
        encoding="utf-8",
    )

    runs = TestClient(create_app(tmp_path)).get("/api/runs").json()

    assert runs[0]["input_parameters"]["pvt_th.U_L"]["source_ref"] == "collector sheet"


def test_run_preflight_blocks_missing_pvt_requirements(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))

    readiness = client.get(
        "/api/run-readiness",
        params={"weather": "inputs/timeseries/weather.csv"},
    )
    run = client.post(
        "/api/runs",
        json={
            "scenario_id": "test-run",
            "weather": "inputs/timeseries/weather.csv",
        },
    )

    assert readiness.status_code == 200
    assert readiness.json()["ok"] is False
    assert run.status_code == 409
    assert "PVT run is blocked" in run.json()["detail"]["message"]


def test_mutation_routes_reject_nonlocal_origins(tmp_path):
    _make_project(tmp_path)
    client = TestClient(create_app(tmp_path))

    response = client.post(
        "/api/validation/apply",
        headers={"Origin": "https://example.com"},
        json={"confirmed": True},
    )

    assert response.status_code == 403


def test_read_only_mode_disables_mutations(tmp_path, monkeypatch):
    _make_project(tmp_path)
    parameter_path = tmp_path / "inputs" / "parameters" / "demo.yaml"
    original = parameter_path.read_text(encoding="utf-8")
    monkeypatch.setenv("AQUASOLAR_READ_ONLY", "true")
    client = TestClient(create_app(tmp_path))

    assert client.get("/api/config").json() == {"read_only": True}
    response = client.post(
        "/api/validation/apply",
        json={
            "confirmed": True,
            "parameter_overrides": {"demo.limit": {"value": 0.8}},
        },
    )

    assert response.status_code == 403
    assert parameter_path.read_text(encoding="utf-8") == original
