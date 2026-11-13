"""Local desktop interface for AquaSolar inputs and output definitions."""

from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import yaml
from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[2]
PARAMETERS_DIR = ROOT / "inputs" / "parameters"
INPUT_INDEX = ROOT / "inputs" / "input_index.yaml"

PARAMETER_FIELDS = (
    ("value", "Value"),
    ("unit", "Unit"),
    ("status", "Status"),
    ("source_type", "Source type"),
    ("source_ref", "Source reference"),
    ("uncertainty.kind", "Uncertainty kind"),
    ("uncertainty.value", "Uncertainty value"),
    ("uncertainty.distribution", "Uncertainty distribution"),
    ("valid_range.min", "Valid range minimum"),
    ("valid_range.max", "Valid range maximum"),
    ("entered_by", "Entered by"),
    ("entered_on", "Entered on"),
    ("notes", "Notes"),
)

STEP_OUTPUTS = (
    ("P_el", "PVT electrical power", "W", "pvt/runner.py; pvt/collector.py"),
    ("Q_u", "Useful thermal power", "W", "pvt/runner.py; pvt/thermal.py"),
    ("T_f_out", "Collector fluid outlet temperature", "K", "pvt/collector.py"),
    ("T_cell", "PV cell temperature", "K", "pvt/collector.py"),
    ("converged", "PVT solver convergence flag", "boolean", "pvt/coupled.py"),
    ("T_tank_in", "Fluid temperature entering tank", "K", "integrator.py"),
    ("Q_loop_loss", "Collector-loop heat loss", "W", "integrator.py"),
    ("tank_state", "Tank state after this step", "state", "tank/step.py"),
    ("selected_pathway", "Selected water-treatment pathway", "category", "mnt/oracle.py"),
    ("treatment_quality", "Treated-water quality values", "varies", "water_treatment/train.py"),
    ("P_pvt", "PV power in electrical balance", "W", "electrical/balance.py"),
    ("P_aux_heater", "Auxiliary heater power", "W", "integrator.py"),
    ("P_pump", "Pump power", "W", "solar_loop/pump.py"),
    ("P_load", "Other electrical load", "W", "electrical/balance.py"),
    ("P_grid_import", "Grid import power", "W", "electrical/balance.py"),
    ("P_grid_export", "Grid export power", "W", "electrical/balance.py"),
    ("battery_soc", "Battery state of charge", "fraction", "electrical/balance.py"),
    ("ledgers", "Component calculation ledgers", "records", "integrator.py"),
)

SUMMARY_OUTPUTS = (
    ("total_steps", "Number of simulation steps", "count", "simulate.py"),
    ("duration", "Total simulated duration", "s", "simulate.py"),
    ("energy_summary.P_pvt_total", "Total PVT electrical energy", "J", "simulate.py"),
    ("energy_summary.Q_u_total", "Total useful heat", "J", "simulate.py"),
    ("energy_summary.Q_loss_total", "Total tank heat loss", "J", "simulate.py"),
    ("energy_summary.P_grid_import_total", "Total grid-import energy", "J", "simulate.py"),
    ("energy_summary.P_grid_export_total", "Total grid-export energy", "J", "simulate.py"),
    ("energy_summary.P_pvt_avg", "Average PVT electrical power", "W", "simulate.py"),
    ("energy_summary.Q_u_avg", "Average useful thermal power", "W", "simulate.py"),
    ("nonconverged_steps", "PVT solver steps that did not converge", "count", "pvt/runner.py"),
    ("electrical_summary.self_consumption", "Average self-consumption fraction", "fraction", "simulate.py"),
    ("treatment_summary.pathway_counts", "Steps per treatment pathway", "counts", "simulate.py"),
)

PVT_SERIES_FIELDS = (
    "POA_W_m2",
    "GHI_W_m2",
    "T_ambient_K",
    "T_f_out_K",
    "T_cell_K",
    "P_el_W",
    "Q_u_W",
    "E_el_Wh",
    "E_heat_Wh",
)


def _read_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return yaml.safe_load(stream)


def load_parameter_catalog() -> list[dict[str, Any]]:
    """Load every parameter entry and its input-index requirements."""
    index = _read_yaml(INPUT_INDEX) or {}
    definitions = {
        row["id"]: row for row in index.get("parameters", [])
    }
    catalog: list[dict[str, Any]] = []
    for path in sorted(PARAMETERS_DIR.glob("*.yaml")):
        file_data = _read_yaml(path) or {}
        for parameter in file_data.get("parameters", []):
            definition = definitions.get(parameter["id"], {})
            catalog.append(
                {
                    "id": parameter["id"],
                    "file": path,
                    "group": file_data.get("title", path.stem),
                    "description": parameter.get("description", ""),
                    "phase": definition.get("phase", parameter.get("needed_by_phase")),
                    "required_when": definition.get(
                        "required_when", parameter.get("required_when", "always")
                    ),
                    "allowed": parameter.get("allowed_values", definition.get("allowed")),
                    "source_type": parameter.get("source_type") or "unassigned",
                    "source_ref": parameter.get("source_ref") or "No source recorded",
                    "parameter": parameter,
                }
            )
    return catalog


def load_data_input_catalog() -> list[dict[str, Any]]:
    """Describe every configured table/time-series input and its columns."""
    catalog = []
    for folder_name in ("timeseries", "tables"):
        folder = ROOT / "inputs" / folder_name
        for meta_path in sorted(folder.glob("*.meta.yaml")):
            meta = _read_yaml(meta_path) or {}
            csv_path = meta_path.with_name(
                f"{meta_path.name.removesuffix('.meta.yaml')}.csv"
            )
            row_count = 0
            if csv_path.exists():
                with csv_path.open(encoding="utf-8", newline="") as stream:
                    row_count = max(sum(1 for _ in csv.reader(stream)) - 1, 0)
            for column in meta.get("columns", []):
                catalog.append(
                    {
                        "file": f"inputs/{folder_name}/{csv_path.name}",
                        "name": column.get("name", ""),
                        "description": column.get("description", ""),
                        "unit": column.get("unit"),
                        "required": column.get("required", False),
                        "rows": row_count,
                        "source": column.get(
                            "sensor_or_source", meta.get("provenance_ref", "Not specified")
                        ),
                    }
                )
    return catalog


def load_metric_catalog() -> list[dict[str, str]]:
    """Read the named output metrics from the metric definitions register."""
    path = ROOT / "docs" / "metric_definitions.md"
    metrics = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == len(("id", "name", "definition", "num", "den", "time", "unit", "scenarios", "status")):
            metric_id, name, definition, _, _, _, unit, _, _ = cells
        else:
            continue
        if re.fullmatch(r"M-[A-Z]+-\d+", metric_id):
            metrics.append(
                {
                    "id": metric_id,
                    "name": name,
                    "definition": definition,
                    "unit": unit,
                    "source": "docs/metric_definitions.md; reporting/metrics.py",
                }
            )
    return metrics


def available_weather_files(folder: Path | None = None) -> list[str]:
    """Return weather CSV paths with the columns required by the PVT runner."""
    weather_dir = folder or ROOT / "inputs" / "timeseries"
    required = {"timestamp", "ghi", "dni", "dhi", "t_ambient", "wind_speed"}
    files = []
    for path in sorted(weather_dir.glob("*.csv")):
        try:
            with path.open(encoding="utf-8", newline="") as stream:
                columns = set(next(csv.reader(stream), []))
        except OSError:
            continue
        if required.issubset(columns):
            try:
                files.append(str(path.relative_to(ROOT)))
            except ValueError:
                files.append(str(path))
    return files


def read_pvt_series(path: Path) -> list[dict[str, Any]]:
    """Read and validate the hourly result columns used by the plotting UI."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"timestamp", *PVT_SERIES_FIELDS}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Result CSV is missing columns: {', '.join(sorted(missing))}")
        rows = []
        for line_number, row in enumerate(reader, start=2):
            try:
                parsed = {
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    **{field: float(row[field]) for field in PVT_SERIES_FIELDS},
                }
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid result on CSV line {line_number}: {exc}") from exc
            rows.append(parsed)
    if not rows:
        raise ValueError("Result CSV contains no hourly records.")
    return rows


def _get_nested(data: dict[str, Any], key: str) -> Any:
    value: Any = data
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _set_nested(data: dict[str, Any], key: str, value: Any) -> None:
    parts = key.split(".")
    target = data
    for part in parts[:-1]:
        child = target.get(part)
        if not isinstance(child, dict):
            child = {}
            target[part] = child
        target = child
    target[parts[-1]] = value


def save_parameter_entry(
    path: Path, parameter_id: str, updated: dict[str, Any]
) -> None:
    """Update an entry in place while preserving YAML comments and formatting."""
    round_trip = YAML()
    round_trip.preserve_quotes = True
    with path.open(encoding="utf-8") as stream:
        data = round_trip.load(stream)
    rows = data.get("parameters", [])
    for item in rows:
        if item.get("id") == parameter_id:
            for key, _label in PARAMETER_FIELDS:
                _set_nested(item, key, _get_nested(updated, key))
            break
    else:
        raise ValueError(f"Could not find {parameter_id} in {path.name}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        round_trip.dump(data, stream)


class AquaSolarUI:
    """Tkinter app to edit parameter files and inspect inputs/outputs."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AquaSolar | Inputs and Outputs")
        self.root.geometry("1180x780")
        self.catalog = load_parameter_catalog()
        self.by_id = {row["id"]: row for row in self.catalog}
        self.variables: dict[str, tk.StringVar] = {}
        self.current_id: str | None = None
        self.run_process: subprocess.Popen[str] | None = None
        self.active_scenario_id: str | None = None
        self.run_paths: dict[str, Path] = {}

        self._build_layout()
        self._populate_parameter_tree()
        self._populate_data_tree()
        self._populate_output_tree()
        self._update_status()
        self._load_latest_run_summary()

    def _build_layout(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font="Segoe UI 18 bold")
        style.configure("Section.TLabel", font="Segoe UI 11 bold")
        outer = ttk.Frame(self.root, padding="16")
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="AquaSolar project inputs", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            outer,
            text=(
                "Edit parameters, inspect input data, run PVT scenarios, and "
                "explore graphical results."
            ),
        ).pack(anchor="w", pady=("2", "12"))

        self.notebook = ttk.Notebook(outer)
        self.notebook.pack(fill="both", expand=True)
        self.parameter_tab = ttk.Frame(self.notebook, padding="10")
        self.data_tab = ttk.Frame(self.notebook, padding="10")
        self.output_tab = ttk.Frame(self.notebook, padding="10")
        self.analysis_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.parameter_tab, text="Parameters")
        self.notebook.add(self.data_tab, text="Data inputs")
        self.notebook.add(self.output_tab, text="Outputs")
        self.notebook.add(self.analysis_tab, text="Run & plots")
        self._build_parameter_tab()
        self._build_data_tab()
        self._build_output_tab()
        self._build_analysis_tab()

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=("10", "0"))
        self.status_label = ttk.Label(footer, text="")
        self.status_label.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Validate inputs", command=self._validate).pack(
            side="right", padx=("8", "0")
        )
        ttk.Button(footer, text="Save parameter", command=self._save_current).pack(
            side="right"
        )
        self.run_button = ttk.Button(
            footer, text="Run scenario", command=self._run_pvt_only
        )
        self.run_button.pack(side="right", padx=("0", "8"))

    def _build_parameter_tab(self) -> None:
        pane = ttk.Panedwindow(self.parameter_tab, orient="horizontal")
        pane.pack(fill="both", expand=True)
        tree_frame = ttk.Frame(pane, width="380")
        form_frame = ttk.Frame(pane, padding=("14", "0", "0", "0"))
        pane.add(tree_frame, weight=2)
        pane.add(form_frame, weight="3")
        ttk.Label(tree_frame, text="Input parameters", style="Section.TLabel").pack(
            anchor="w", pady=("0", "6")
        )
        self.parameter_tree = ttk.Treeview(
            tree_frame, columns=("status", "source", "phase"), show="tree headings"
        )
        self.parameter_tree.heading("#0", text="Parameter")
        self.parameter_tree.heading("status", text="Status")
        self.parameter_tree.heading("source", text="Source")
        self.parameter_tree.heading("phase", text="Phase")
        self.parameter_tree.column("#0", width="190")
        self.parameter_tree.column("status", width="75", anchor="center")
        self.parameter_tree.column("source", width="95")
        self.parameter_tree.column("phase", width="45", anchor="center")
        scroll = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.parameter_tree.yview
        )
        self.parameter_tree.configure(yscrollcommand=scroll.set)
        self.parameter_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.parameter_tree.bind("<<TreeviewSelect>>", self._select_parameter)

        self.form_title = ttk.Label(form_frame, text="Select a parameter", style="Section.TLabel")
        self.form_title.pack(anchor="w")
        self.form_description = ttk.Label(
            form_frame, text="", wraplength="620", justify="left"
        )
        self.form_description.pack(anchor="w", pady=("4", "12"))
        self.requirement_label = ttk.Label(
            form_frame, text="", wraplength="620", justify="left"
        )
        self.requirement_label.pack(anchor="w", pady=("0", "10"))
        form = ttk.Frame(form_frame)
        form.pack(fill="both", expand=True, anchor="n")
        self.form = form

    def _build_data_tab(self) -> None:
        ttk.Label(
            self.data_tab,
            text="Input data columns read from metadata files",
            style="Section.TLabel",
        ).pack(anchor="w", pady=("0", "8"))
        self.data_tree = ttk.Treeview(
            self.data_tab,
            columns=("file", "unit", "required", "rows", "description", "source"),
            show="headings",
        )
        for key, label, width in (
            ("file", "File", "230"),
            ("unit", "Unit", "90"),
            ("required", "Required", "75"),
            ("rows", "Rows", "70"),
            ("description", "Column / description", "360"),
            ("source", "Source", "320"),
        ):
            self.data_tree.heading(key, text=label)
            self.data_tree.column(key, width=width, anchor="w")
        self.data_tree.pack(fill="both", expand=True)

    def _build_output_tab(self) -> None:
        ttk.Label(
            self.output_tab,
            text="Output definitions",
            style="Section.TLabel",
        ).pack(anchor="w")
        self.output_note_label = ttk.Label(
            self.output_tab,
            text=(
                "Run scenario executes the limited exploratory PVT-only path. "
                "It does not run the tank, DHW, electrical bus, or water-treatment model."
            ),
            wraplength="1040",
            justify="left",
        )
        self.output_note_label.pack(anchor="w", pady=("4", "10"))
        self.output_tree = ttk.Treeview(
            self.output_tab,
            columns=("kind", "description", "unit", "source", "value"),
            show="tree headings",
        )
        self.output_tree.heading("#0", text="Output variable")
        self.output_tree.heading("kind", text="Type")
        self.output_tree.heading("description", text="Meaning")
        self.output_tree.heading("unit", text="Unit")
        self.output_tree.heading("source", text="Source / definition")
        self.output_tree.heading("value", text="Current value")
        self.output_tree.column("#0", width="240")
        self.output_tree.column("kind", width="100")
        self.output_tree.column("description", width="330")
        self.output_tree.column("unit", width="90")
        self.output_tree.column("source", width="250")
        self.output_tree.column("value", width="140")
        self.output_tree.pack(fill="both", expand=True, pady=("8", "0"))

    def _build_analysis_tab(self) -> None:
        ttk.Label(
            self.analysis_tab,
            text="Run exploratory PVT scenarios and inspect saved hourly results.",
            style="Section.TLabel",
        ).pack(anchor="w", pady=("0", "8"))
        controls = ttk.Frame(self.analysis_tab)
        controls.pack(fill="x", pady=("0", "8"))
        ttk.Label(controls, text="Scenario ID").grid(row=0, column=0, sticky="w")
        self.scenario_var = tk.StringVar(
            value=datetime.now().strftime("scenario-%Y%m%d-%H%M%S")
        )
        ttk.Entry(controls, textvariable=self.scenario_var, width="28").grid(
            row=0, column=1, sticky="w", padx=("6", "18")
        )
        ttk.Label(controls, text="Weather CSV").grid(row=0, column=2, sticky="w")
        self.weather_var = tk.StringVar()
        self.weather_combo = ttk.Combobox(
            controls,
            textvariable=self.weather_var,
            values=available_weather_files(),
            state="readonly",
            width="48",
        )
        self.weather_combo.grid(row=0, column="3", sticky="ew", padx=("6", "6"))
        if self.weather_combo["values"]:
            default_weather = "inputs/timeseries/weather.csv"
            self.weather_var.set(
                default_weather
                if default_weather in self.weather_combo["values"]
                else self.weather_combo["values"][0]
            )
        ttk.Button(
            controls, text="Refresh runs", command=self._refresh_run_catalog
        ).grid(row=0, column="4", sticky="e")
        ttk.Label(controls, text="Saved run").grid(row=1, column=0, sticky="w", pady=("8", "0"))
        self.run_var = tk.StringVar()
        self.run_combo = ttk.Combobox(
            controls, textvariable=self.run_var, state="readonly", width="28"
        )
        self.run_combo.grid(row=1, column=1, sticky="w", padx=("6", "18"), pady=("8", "0"))
        self.run_combo.bind("<<ComboboxSelected>>", self._plot_selected_run)
        ttk.Label(controls, text="Plot").grid(row=1, column=2, sticky="w", pady=("8", "0"))
        self.plot_var = tk.StringVar(value="Electrical and useful heat")
        self.plot_combo = ttk.Combobox(
            controls,
            textvariable=self.plot_var,
            values=(
                "Electrical and useful heat",
                "Solar irradiance",
                "Collector temperatures",
                "Cumulative energy",
                "Power duration curve",
            ),
            state="readonly",
            width="32",
        )
        self.plot_combo.grid(row=1, column="3", sticky="w", padx=("6", "6"), pady=("8", "0"))
        self.plot_combo.bind("<<ComboboxSelected>>", self._plot_selected_run)
        controls.columnconfigure("3", weight=1)

        self.analysis_note = ttk.Label(
            self.analysis_tab,
            text=(
                "Choose a saved run to plot it. The Matplotlib toolbar supports "
                "zoom, pan, and saving figures."
            ),
            wraplength="1040",
            justify="left",
        )
        self.analysis_note.pack(anchor="w", pady=("0", "4"))
        self.figure = Figure(
            figsize=(float("9"), float("4.5")), dpi=int("100")
        )
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.analysis_tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(
            self.canvas, self.analysis_tab, pack_toolbar=False
        )
        toolbar.update()
        toolbar.pack(side="bottom", fill="x")

    def _populate_parameter_tree(self) -> None:
        groups: dict[str, str] = {}
        for row in self.catalog:
            group = row["group"]
            if group not in groups:
                groups[group] = self.parameter_tree.insert(
                    "", "end", text=group, open=True, values=("", "")
                )
            parameter = row["parameter"]
            self.parameter_tree.insert(
                groups[group],
                "end",
                iid=row["id"],
                text=row["id"],
                values=(
                    parameter.get("status", "draft"),
                    row.get("source_type", "unassigned"),
                    row.get("phase", ""),
                ),
            )

    def _populate_data_tree(self) -> None:
        for row in load_data_input_catalog():
            description = row["name"]
            if row["description"]:
                description += f" — {row['description']}"
            self.data_tree.insert(
                "",
                "end",
                values=(
                    row["file"],
                    row["unit"] or "—",
                    "yes" if row["required"] else "no",
                    row["rows"],
                    description,
                    row["source"],
                ),
            )

    def _populate_output_tree(self) -> None:
        self.output_items: dict[str, str] = {}
        step = self.output_tree.insert("", "end", text="Per-step outputs", open=True)
        for name, description, unit, source in STEP_OUTPUTS:
            iid = f"step:{name}"
            self.output_items[iid] = self.output_tree.insert(
                step,
                "end",
                iid=iid,
                text=name,
                values=("series", description, unit, source, "—"),
            )
        summary = self.output_tree.insert("", "end", text="Run summaries", open=True)
        for name, description, unit, source in SUMMARY_OUTPUTS:
            iid = f"summary:{name}"
            self.output_items[iid] = self.output_tree.insert(
                summary,
                "end",
                iid=iid,
                text=name,
                values=("summary", description, unit, source, "—"),
            )
        metrics = self.output_tree.insert("", "end", text="Named project metrics", open=True)
        for metric in load_metric_catalog():
            iid = f"metric:{metric['id']}"
            self.output_items[iid] = self.output_tree.insert(
                metrics,
                "end",
                iid=iid,
                text=metric["id"],
                values=(
                    "metric",
                    f"{metric['name']} — {metric['definition']}",
                    metric["unit"],
                    metric["source"],
                    "—",
                ),
            )
    def _select_parameter(self, *_args: Any) -> None:
        selection = self.parameter_tree.selection()
        if not selection or selection[0] not in self.by_id:
            return
        try:
            self._save_form_to_memory()
        except ValueError as exc:
            messagebox.showerror("Invalid parameter value", str(exc))
            if self.current_id is not None:
                self.parameter_tree.selection_set(self.current_id)
            return
        self._render_parameter(self.by_id[selection[0]])

    def _render_parameter(self, row: dict[str, Any]) -> None:
        for child in self.form.winfo_children():
            child.destroy()
        self.variables.clear()
        parameter = row["parameter"]
        self.current_id = row["id"]
        self.form_title.configure(text=row["id"])
        self.form_description.configure(text=row["description"])
        self.requirement_label.configure(
            text=f"Phase {row.get('phase', '—')}  |  Required when: {row.get('required_when', 'always')}"
        )
        allowed = row.get("allowed")
        for key, label in PARAMETER_FIELDS:
            index = len(self.variables)
            value = _get_nested(parameter, key)
            text = "" if value is None else str(value)
            variable = tk.StringVar(value=text)
            self.variables[key] = variable
            ttk.Label(self.form, text=label).grid(
                row=index, column=0, sticky="w", padx=("0", "14"), pady="4"
            )
            if key == "status":
                widget: tk.Widget = ttk.Combobox(
                    self.form,
                    textvariable=variable,
                    values=("draft", "confirmed", "not_applicable"),
                    state="readonly",
                    width="48",
                )
            elif key == "source_type":
                widget = ttk.Combobox(
                    self.form,
                    textvariable=variable,
                    values=("", "measured", "datasheet", "literature", "standard", "assumption"),
                    state="readonly",
                    width="48",
                )
            elif key == "value" and allowed:
                widget = ttk.Combobox(
                    self.form,
                    textvariable=variable,
                    values=tuple(str(value) for value in allowed),
                    width="48",
                )
            else:
                widget = ttk.Entry(self.form, textvariable=variable, width="52")
            widget.grid(row=index, column=1, sticky="ew", pady="4")
        self.form.columnconfigure(1, weight=1)

    def _save_form_to_memory(self) -> None:
        if self.current_id is None or not self.variables:
            return
        parameter = self.by_id[self.current_id]["parameter"]
        for key, variable in self.variables.items():
            raw = variable.get().strip()
            value: Any = None
            if raw:
                if key == "value":
                    kind = self.by_id[self.current_id]["parameter"].get(
                        "quantity_kind"
                    )
                    if kind in {"text", "categorical"}:
                        value = raw
                    else:
                        try:
                            value = yaml.safe_load(raw)
                        except yaml.YAMLError as exc:
                            raise ValueError(
                                f"{self.current_id}: invalid value: {exc}"
                            ) from exc
                        if isinstance(value, (dict, list)):
                            raise ValueError(
                                f"{self.current_id}: value must be a scalar"
                            )
                elif key in {
                    "uncertainty.value",
                    "valid_range.min",
                    "valid_range.max",
                }:
                    try:
                        value = float(raw)
                    except ValueError as exc:
                        raise ValueError(f"{self.current_id}: {raw!r} must be numeric") from exc
                else:
                    value = raw
            _set_nested(parameter, key, value)

    def _save_current(self) -> None:
        if self.current_id is None:
            messagebox.showinfo("Select a parameter", "Choose a parameter to edit first.")
            return
        self._persist_current(show_confirmation=True)

    def _persist_current(self, show_confirmation: bool) -> bool:
        if self.current_id is None:
            return True
        try:
            self._save_form_to_memory()
            path = self.by_id[self.current_id]["file"]
            updated = self.by_id[self.current_id]["parameter"]
            save_parameter_entry(path, self.current_id, updated)
            self.parameter_tree.set(
                self.current_id, "status", updated.get("status", "draft")
            )
            self.parameter_tree.set(
                self.current_id,
                "source",
                updated.get("source_type") or "unassigned",
            )
            self.by_id[self.current_id]["source_type"] = (
                updated.get("source_type") or "unassigned"
            )
            self.by_id[self.current_id]["source_ref"] = (
                updated.get("source_ref") or "No source recorded"
            )
            self._update_status()
            if show_confirmation:
                messagebox.showinfo("Saved", f"Saved {self.current_id} to {path.name}.")
            return True
        except (OSError, ValueError, yaml.YAMLError) as exc:
            messagebox.showerror("Could not save parameter", str(exc))
            return False

    def _validate(self) -> None:
        if not self._persist_current(show_confirmation=False):
            return
        result = subprocess.run(
            [sys.executable, "-m", "aquasolar", "check-inputs"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )
        status_path = ROOT / "inputs" / "STATUS.md"
        if result.returncode == 0:
            messagebox.showinfo("Inputs valid", f"Input validation passed.\n\n{status_path}")
        else:
            details = result.stderr.strip() or result.stdout.strip()
            if status_path.exists():
                details = status_path.read_text(encoding="utf-8")
            messagebox.showwarning("Inputs need attention", details or "Input validation failed.")

    def _run_pvt_only(self) -> None:
        if self.run_process is not None:
            return
        if not self._persist_current(show_confirmation=False):
            return
        scenario_id = self.scenario_var.get().strip()
        weather_path = self.weather_var.get().strip()
        if not scenario_id:
            messagebox.showerror("Scenario ID required", "Enter a unique scenario ID.")
            return
        if not weather_path:
            messagebox.showerror(
                "Weather CSV required",
                "No weather CSV with the required PVT input columns was found.",
            )
            return
        self.active_scenario_id = scenario_id
        try:
            self.run_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "aquasolar",
                    "run",
                    scenario_id,
                    "--weather",
                    weather_path,
                ],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            )
        except OSError as exc:
            messagebox.showerror("Could not start scenario", str(exc))
            return
        self.run_button.configure(state="disabled", text="Running scenario...")
        self.status_label.configure(text=f"Running exploratory scenario {scenario_id}...")
        self.root.after(int("200"), self._poll_pvt_run)

    def _poll_pvt_run(self) -> None:
        process = self.run_process
        if process is None:
            return
        if process.poll() is None:
            self.root.after(int("200"), self._poll_pvt_run)
            return
        stdout, stderr = process.communicate()
        self.run_process = None
        self.run_button.configure(state="normal", text="Run scenario")
        if process.returncode:
            messagebox.showerror(
                "PVT-only run failed", stderr.strip() or stdout.strip()
            )
            self.status_label.configure(text="PVT-only run failed; see error dialog.")
            return
        self._load_latest_run_summary(self.active_scenario_id)
        self.notebook.select(self.analysis_tab)
        messagebox.showinfo("Scenario complete", stdout.strip())

    def _refresh_run_catalog(self, selected_scenario: str | None = None) -> None:
        result_dir = ROOT / "outputs" / "pvt_only"
        summaries = sorted(
            result_dir.glob("*.summary.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ) if result_dir.exists() else []
        if not summaries:
            self.run_paths.clear()
            self.run_combo.configure(values=())
            self.run_var.set("")
            return
        self.run_paths.clear()
        unreadable = []
        for path in summaries:
            try:
                with path.open(encoding="utf-8") as stream:
                    summary = json.load(stream)
            except (OSError, json.JSONDecodeError) as exc:
                unreadable.append(f"{path.name}: {exc}")
                continue
            scenario_id = summary.get("scenario_id")
            if summary.get("scope") == "PVT-only exploratory" and scenario_id:
                self.run_paths[scenario_id] = path
        scenarios = list(self.run_paths)
        self.run_combo.configure(values=scenarios)
        if unreadable:
            self.status_label.configure(
                text="Could not read saved run summaries: " + "; ".join(unreadable)
            )
        target = selected_scenario if selected_scenario in self.run_paths else (
            scenarios[0] if scenarios else ""
        )
        self.run_var.set(target)
        if target:
            self._load_run_summary(self.run_paths[target])
            self._draw_selected_run()

    def _load_latest_run_summary(self, selected_scenario: str | None = None) -> None:
        self._refresh_run_catalog(selected_scenario)

    def _load_run_summary(self, summary_path: Path) -> None:
        try:
            with summary_path.open(encoding="utf-8") as stream:
                summary = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            self.status_label.configure(
                text=f"Could not read PVT result summary {summary_path.name}: {exc}"
            )
            return
        if summary.get("scope") != "PVT-only exploratory" or not summary.get("success"):
            self.status_label.configure(
                text=f"Latest result {summary_path.name} has an unexpected format."
            )
            return
        summary_values = {
            "total_steps": summary.get("steps"),
            "duration": summary.get("duration_hours", 0.0) * float("3600.0"),
            "energy_summary.P_pvt_total": summary.get(
                "electrical_energy_joules"
            ),
            "energy_summary.Q_u_total": summary.get("useful_heat_joules"),
            "energy_summary.P_pvt_avg": summary.get(
                "average_electrical_power_w"
            ),
            "energy_summary.Q_u_avg": summary.get("average_useful_heat_w"),
            "nonconverged_steps": summary.get("nonconverged_steps"),
        }
        for key, value in summary_values.items():
            iid = f"summary:{key}"
            if iid in self.output_items and value is not None:
                self.output_tree.set(iid, "value", f"{value:.3f}")
        metrics = summary.get("metrics", {})
        for metric_id, value in metrics.items():
            iid = f"metric:{metric_id}"
            if iid in self.output_items:
                self.output_tree.set(iid, "value", f"{value:.3f}")
        rows_label = f"{summary.get('steps')} hourly records; see {summary.get('results_csv')}"
        for name in ("P_el", "Q_u", "T_f_out", "T_cell", "converged"):
            iid = f"step:{name}"
            if iid in self.output_items:
                self.output_tree.set(iid, "value", rows_label)
        self.output_note_label.configure(
            text=(
                f"Showing {summary['scenario_id']} from {summary_path.name}. "
                "PVT-only exploratory results; no tank, DHW, electrical bus, "
                "or water-treatment simulation."
            )
        )

    def _plot_selected_run(self, *_args: Any) -> None:
        self._draw_selected_run()

    def _draw_selected_run(self) -> None:
        scenario_id = self.run_var.get()
        summary_path = self.run_paths.get(scenario_id)
        if summary_path is None:
            return
        try:
            with summary_path.open(encoding="utf-8") as stream:
                summary = json.load(stream)
            result_path = ROOT / summary["results_csv"]
            rows = read_pvt_series(result_path)
        except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
            messagebox.showerror("Could not load simulation results", str(exc))
            return

        self.figure.clear()
        axis = self.figure.add_subplot(1, 1, 1)
        timestamps = [row["timestamp"] for row in rows]
        plot_kind = self.plot_var.get()
        if plot_kind == "Electrical and useful heat":
            axis.plot(timestamps, [row["P_el_W"] for row in rows], label="Electrical power")
            axis.plot(timestamps, [row["Q_u_W"] for row in rows], label="Useful heat")
            axis.set_ylabel("Power (W)")
        elif plot_kind == "Solar irradiance":
            axis.plot(timestamps, [row["POA_W_m2"] for row in rows], label="Plane of array")
            axis.plot(timestamps, [row["GHI_W_m2"] for row in rows], label="Global horizontal")
            axis.set_ylabel("Irradiance (W/m²)")
        elif plot_kind == "Collector temperatures":
            for field, label in (
                ("T_ambient_K", "Ambient"),
                ("T_f_out_K", "Fluid outlet"),
                ("T_cell_K", "PV cell"),
            ):
                axis.plot(
                    timestamps,
                    [row[field] - float("273.15") for row in rows],
                    label=label,
                )
            axis.set_ylabel("Temperature (°C)")
        elif plot_kind == "Cumulative energy":
            electrical = []
            thermal = []
            electrical_total = 0.0
            thermal_total = 0.0
            for row in rows:
                electrical_total += row["E_el_Wh"]
                thermal_total += row["E_heat_Wh"]
                electrical.append(electrical_total)
                thermal.append(thermal_total)
            axis.plot(timestamps, electrical, label="Electrical energy")
            axis.plot(timestamps, thermal, label="Useful heat")
            axis.set_ylabel("Cumulative energy (Wh)")
        else:
            electrical = sorted(
                (row["P_el_W"] for row in rows), reverse=True
            )
            thermal = sorted((row["Q_u_W"] for row in rows), reverse=True)
            axis.plot(range(1, len(rows) + 1), electrical, label="Electrical power")
            axis.plot(range(1, len(rows) + 1), thermal, label="Useful heat")
            axis.set_xlabel("Hours ranked from highest to lowest")
            axis.set_ylabel("Power (W)")

        axis.set_title(f"{scenario_id} — {plot_kind}")
        if plot_kind != "Power duration curve":
            axis.set_xlabel("Time")
            self.figure.autofmt_xdate()
        axis.grid(True, alpha=float("0.3"))
        axis.legend()
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.analysis_note.configure(
            text=(
                f"{scenario_id} | {len(rows)} hourly records | "
                f"{summary.get('electrical_energy_kwh', float('0.0')):.2f} kWh electric | "
                f"{summary.get('useful_heat_kwh', float('0.0')):.2f} kWh useful heat. "
                "Exploratory PVT-only outputs."
            )
        )

    def _update_status(self) -> None:
        counts = {"confirmed": 0, "draft": 0, "not_applicable": 0}
        for row in self.catalog:
            state = row["parameter"].get("status", "draft")
            counts[state] = counts.get(state, 0) + 1
        self.status_label.configure(
            text=(
                f"{len(self.catalog)} parameters | "
                f"{counts['confirmed']} confirmed | {counts['draft']} draft | "
                f"{counts['not_applicable']} not applicable"
            )
        )


def main() -> None:
    """Launch the local parameter-entry interface."""
    root = tk.Tk()
    AquaSolarUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
