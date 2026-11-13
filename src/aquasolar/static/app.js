const state = {
  readOnly: false,
  catalog: { parameters: [], data_files: [], metrics: [], outputs: [] },
  report: null,
  trace: null,
  modules: [],
  modelError: null,
  weather: [],
  runs: [],
  selectedParameter: null,
  selectedDataFile: null,
  stagedParameters: {},
  stagedFiles: {},
  stagedModules: {},
  previewToken: null,
  selectedTraceNode: null,
  selectedTraceRunId: "",
  selectedRuns: [],
  selectedVariables: [],
  seriesByRun: {},
  seriesErrors: {},
  variablesInitialized: false,
  selectionLoadId: 0,
  zoomRange: null,
  zoomHistory: [],
  hoverTime: null,
  dragRange: null,
  tablePage: 0,
  tableSort: { key: "timestamp", direction: "ascending" },
  weatherUpload: { csv: null, metadata: null },
  newWeatherPath: null,
  drawFrame: null,
  activeJob: null,
  pollTimer: null,
  tempUnit: (function() {
    try {
      return localStorage.getItem("aquasolar_temp_unit") || "C";
    } catch (e) {
      return "C";
    }
  })(),
};

const ANALYSIS_VARIABLES = {
  GHI_W_m2: { label: "Global horizontal irradiance", unit: "W/m²", group: "Weather drivers" },
  DNI_W_m2: { label: "Direct normal irradiance", unit: "W/m²", group: "Weather drivers" },
  DHI_W_m2: { label: "Diffuse horizontal irradiance", unit: "W/m²", group: "Weather drivers" },
  POA_W_m2: { label: "Plane-of-array irradiance", unit: "W/m²", group: "Weather drivers" },
  T_ambient_K: { label: "Ambient temperature", unit: "K", group: "Weather drivers" },
  wind_speed_m_s: { label: "Wind speed", unit: "m/s", group: "Weather drivers" },
  mass_flow_kg_s: { label: "Mass flow", unit: "kg/s", group: "PVT outputs" },
  P_el_W: { label: "Electrical power", unit: "W", group: "PVT outputs" },
  Q_u_W: { label: "Useful heat", unit: "W", group: "PVT outputs" },
  T_f_out_K: { label: "Fluid outlet temperature", unit: "K", group: "PVT outputs" },
  T_cell_K: { label: "Cell temperature", unit: "K", group: "PVT outputs" },
  E_el_Wh: { label: "Electrical energy per step", unit: "Wh", group: "PVT outputs" },
  E_heat_Wh: { label: "Thermal energy per step", unit: "Wh", group: "PVT outputs" },
};

const TEMPERATURE_VARIABLES = new Set(["T_ambient_K", "T_f_out_K", "T_cell_K"]);

function isTemperatureVariable(column) {
  return TEMPERATURE_VARIABLES.has(column) || (typeof column === "string" && (column.startsWith("T_") || column.endsWith("_K")));
}

function getVariableLabel(column) {
  return ANALYSIS_VARIABLES[column]?.label || column;
}

function getVariableUnit(column) {
  if (isTemperatureVariable(column)) {
    return state.tempUnit === "C" ? "°C" : "K";
  }
  return ANALYSIS_VARIABLES[column]?.unit || "";
}

function getVariableValue(column, rawValue) {
  const num = Number(rawValue);
  if (!Number.isFinite(num)) return num;
  if (isTemperatureVariable(column)) {
    return state.tempUnit === "C" ? num - 273.15 : num;
  }
  return num;
}

function setTemperatureUnit(unit) {
  if (unit !== "C" && unit !== "K") return;
  state.tempUnit = unit;
  try {
    localStorage.setItem("aquasolar_temp_unit", unit);
  } catch (err) {}
  updateTempUnitButtons();
  renderVariablePicker();
  renderAnalysis();
  renderParameterList();
  if (state.selectedParameter) {
    openParameter(state.selectedParameter);
  }
}

function updateTempUnitButtons() {
  document.querySelectorAll(".temp-unit-btn").forEach((btn) => {
    const active = btn.dataset.tempUnit === state.tempUnit;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

const SERIES_COLORS = ["#4472c4", "#70ad47", "#ed7d31", "#8062ad", "#c65354", "#1c9298", "#697b8c"];
const DEFAULT_VARIABLES = ["POA_W_m2", "P_el_W", "Q_u_W", "T_f_out_K"];
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;
const MAX_TABLE_ROWS = 100;
const VIEW_LABELS = Object.freeze({
  overview: "Overview",
  parameters: "Parameters",
  data: "Data files",
  validation: "Validation",
  model: "Model",
  runs: "Runs & plots",
});
const VIEW_NAMES = new Set(Object.keys(VIEW_LABELS));

const byId = (id) => document.getElementById(id);
const parameterList = byId("parameter-list");
const dataList = byId("data-list");
const findingList = byId("finding-list");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#39;",
  })[char]);
}

function display(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function matchesSearch(text, query) {
  const haystack = String(text).toLowerCase();
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
  return terms.every((term) => haystack.includes(term));
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  let payload;
  try {
    payload = await response.json();
  } catch (error) {
    throw new Error(`Server returned an unreadable response (${response.status}).`);
  }
  if (!response.ok) {
    const detail = payload.detail;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return payload;
}

function setGlobalError(message) {
  byId("readiness-stamp").innerHTML = `<span class="severity-pill error">Unavailable</span>`;
  byId("next-action-title").textContent = "Could not load project";
  byId("next-action-copy").textContent = message;
  byId("summary-errors").textContent = "!";
}

function showView(name, { updateHistory = true, focusHeading = true } = {}) {
  if (!VIEW_NAMES.has(name)) return;
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("is-visible", view.id === `view-${name}`);
  });
  document.querySelectorAll(".nav-link").forEach((button) => {
    const active = button.dataset.view === name;
    button.classList.toggle("is-active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
    if (active) button.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
  const label = VIEW_LABELS[name];
  byId("view-crumb").textContent = label;
  document.title = `${label} · AquaSolar`;
  if (updateHistory && window.location.hash !== `#${name}`) {
    window.history.pushState({ view: name }, "", `${window.location.pathname}${window.location.search}#${name}`);
  }
  if (focusHeading) {
    window.scrollTo(0, 0);
    document.querySelector(`#view-${name} h1`)?.focus({ preventScroll: true });
  }
  if (name === "runs") window.requestAnimationFrame(drawAnalysisCanvases);
  if (name === "model") {
    renderTraceGraph();
    renderTraceRunSnapshot();
  }
}

function stagedCount() {
  return Object.keys(state.stagedParameters).length
    + Object.keys(state.stagedFiles).length
    + Object.keys(state.stagedModules).length;
}

function updateStagedState() {
  const count = stagedCount();
  byId("save-state").textContent = count
    ? `${count} staged change${count === 1 ? "" : "s"} · not saved`
    : "No staged changes";
  byId("apply-staged").disabled = count === 0;
  byId("start-run").disabled = count > 0 || !byId("start-run").dataset.ready;
}

function effectiveParameter(row) {
  const parameter = structuredClone(row);
  const changes = state.stagedParameters[row.id] || {};
  for (const [path, value] of Object.entries(changes)) {
    const parts = path.split(".");
    let target = parameter;
    for (const part of parts.slice(0, -1)) {
      target[part] = target[part] || {};
      target = target[part];
    }
    target[parts.at(-1)] = value;
  }
  return parameter;
}

function filterParameters() {
  const query = byId("parameter-search").value.trim().toLowerCase();
  const status = byId("parameter-status-filter").value;
  const group = byId("parameter-group-filter").value;
  return state.catalog.parameters.filter((row) => {
    const effective = effectiveParameter(row);
    if (!isParameterVisible(row)) return false;
    const text = [
      row.id,
      row.description,
      row.group,
      row.source_ref,
      row.required_when,
      row.kind,
    ].join(" ").toLowerCase();
    return (!query || matchesSearch(text, query))
      && (!status || effective.status === status)
      && (!group || row.group === group);
  });
}

function renderParameterList() {
  const rows = filterParameters();
  if (state.selectedParameter && !isParameterVisible(
    state.catalog.parameters.find((row) => row.id === state.selectedParameter) || {},
  )) {
    state.selectedParameter = null;
    byId("parameter-detail").innerHTML = `<div class="empty-state"><span class="empty-mark">P</span><h2>Select a parameter</h2><p>Disabled-module inputs remain saved but are hidden from this browser.</p></div>`;
  }
  byId("parameter-count").textContent = `${rows.length} of ${state.catalog.parameters.length} parameters`;
  byId("nav-parameter-count").textContent = state.catalog.parameters.filter(isParameterVisible).length;
  if (!rows.length) {
    parameterList.innerHTML = `<p class="empty-list">No parameters match these search and filter settings.</p>`;
    return;
  }
  parameterList.innerHTML = rows.map((row) => {
    const parameter = effectiveParameter(row);
    const selected = row.id === state.selectedParameter ? " is-selected" : "";
    const isStaged = Boolean(state.stagedParameters[row.id]);
    let valueHint = "";
    if (row.kind === "temperature" && Number.isFinite(Number(parameter.value))) {
      const u = (parameter.unit || "").trim().toLowerCase();
      const n = Number(parameter.value);
      if (u === "k" || !u || u === "kelvin") {
        valueHint = `<span>·</span><strong>${(n - 273.15).toFixed(1)} °C</strong>`;
      } else if (u === "degc" || u === "c" || u === "celsius") {
        valueHint = `<span>·</span><strong>${(n + 273.15).toFixed(1)} K</strong>`;
      }
    }
    return `<button class="record-item${selected}" role="listitem" data-parameter-id="${escapeHtml(row.id)}">
      <span class="record-topline"><span class="record-id">${escapeHtml(row.id)}</span><span class="status-pill ${escapeHtml(parameter.status || "draft")}">${escapeHtml(isStaged ? "staged" : parameter.status || "draft")}</span></span>
      <span class="record-description">${escapeHtml(row.description || row.group)}</span>
      <span class="record-meta"><span>${escapeHtml(row.group)}</span><span>·</span><span>Phase ${escapeHtml(row.phase ?? "—")}</span>${valueHint}</span>
    </button>`;
  }).join("");
}

function inputForParameter(row, parameter, path, title, wide = false) {
  const value = path.split(".").reduce((target, key) => target?.[key], parameter);
  const kind = path === "value" ? row.kind : null;
  const classes = `parameter-field${wide ? " wide" : ""}`;
  if (path === "status") {
    return `<label class="${classes}">${escapeHtml(title)}<select data-param-field="${path}">
      ${["draft", "confirmed", "not_applicable"].map((item) => `<option value="${item}" ${value === item ? "selected" : ""}>${item.replaceAll("_", " ")}</option>`).join("")}
    </select></label>`;
  }
  if (path === "source_type") {
    const options = ["", "measured", "datasheet", "literature", "standard", "assumption"];
    return `<label class="${classes}">${escapeHtml(title)}<select data-param-field="${path}">
      ${options.map((item) => `<option value="${item}" ${value === item ? "selected" : ""}>${item || "Unassigned"}</option>`).join("")}
    </select></label>`;
  }
  if (path === "value" && row.allowed?.length) {
    return `<label class="${classes}">${escapeHtml(title)}<select data-param-field="${path}">
      <option value="">Select…</option>
      ${row.allowed.map((item) => `<option value="${escapeHtml(item)}" ${String(value) === String(item) ? "selected" : ""}>${escapeHtml(item)}</option>`).join("")}
    </select></label>`;
  }
  if (path === "value" && kind === "boolean") {
    return `<label class="${classes}">${escapeHtml(title)}<select data-param-field="${path}">
      <option value="">Select…</option><option value="true" ${value === true ? "selected" : ""}>true</option><option value="false" ${value === false ? "selected" : ""}>false</option>
    </select></label>`;
  }
  if (path === "notes") {
    return `<label class="${classes}">${escapeHtml(title)}<textarea data-param-field="${path}">${escapeHtml(value ?? "")}</textarea></label>`;
  }
  const numeric = path === "value" ? [
    "activation_energy", "angle", "area", "area_thermal_resistance",
    "areal_heat_capacity", "concentration", "count", "currency",
    "currency_per_energy", "currency_per_time", "currency_per_volume",
    "density", "dimensionless", "emission_per_energy", "emission_per_volume",
    "energy", "energy_per_volume", "flow_mass", "flow_volumetric", "fraction",
    "heat_transfer_coefficient", "irradiance", "length", "loading_capacity",
    "mass", "permeability", "power", "pressure", "rate_per_temperature",
    "rate_per_time", "rate_per_volume", "specific_heat", "temperature",
    "temperature_difference", "thermal_conductance", "thermal_conductivity",
    "time", "uv_dose", "uv_intensity", "volume",
  ].includes(kind) : path.endsWith(".value");
  return `<label class="${classes}">${escapeHtml(title)}<input data-param-field="${path}" type="${numeric ? "number" : "text"}" ${numeric ? 'step="any"' : ""} value="${escapeHtml(value ?? "")}"></label>`;
}

function openParameter(parameterId) {
  const row = state.catalog.parameters.find((item) => item.id === parameterId);
  if (!row) return;
  state.selectedParameter = parameterId;
  renderParameterList();
  const parameter = effectiveParameter(row);
  const requirement = row.required_when || "always";
  const fields = [
    inputForParameter(row, parameter, "value", `Value${row.unit ? ` (${row.unit})` : ""}`),
    inputForParameter(row, parameter, "unit", "Unit"),
    inputForParameter(row, parameter, "status", "Status"),
    inputForParameter(row, parameter, "source_type", "Source type"),
    inputForParameter(row, parameter, "source_ref", "Source reference", true),
    inputForParameter(row, parameter, "valid_range.min", "Valid range minimum"),
    inputForParameter(row, parameter, "valid_range.max", "Valid range maximum"),
    inputForParameter(row, parameter, "uncertainty.kind", "Uncertainty kind"),
    inputForParameter(row, parameter, "uncertainty.value", "Uncertainty value"),
    inputForParameter(row, parameter, "uncertainty.distribution", "Uncertainty distribution"),
    inputForParameter(row, parameter, "entered_by", "Entered by"),
    inputForParameter(row, parameter, "entered_on", "Entered on"),
    inputForParameter(row, parameter, "notes", "Notes", true),
  ].join("");
  const allowed = row.allowed?.length ? row.allowed.join(", ") : "No categorical choices";
  let tempHelper = "";
  if (row.kind === "temperature" && Number.isFinite(Number(parameter.value))) {
    const u = (parameter.unit || "").trim().toLowerCase();
    const n = Number(parameter.value);
    if (u === "k" || !u || u === "kelvin") {
      const cVal = (n - 273.15).toFixed(2);
      tempHelper = `<div class="temp-param-helper">
        <span>Current: <strong>${n} K</strong> &nbsp;⇄&nbsp; Equivalent: <strong>${cVal} °C</strong></span>
        <button type="button" class="button button-quiet button-sm" id="convert-param-temp" data-to="degC" data-val="${cVal}">Convert input to °C (${cVal} degC)</button>
      </div>`;
    } else if (u === "degc" || u === "c" || u === "celsius") {
      const kVal = (n + 273.15).toFixed(2);
      tempHelper = `<div class="temp-param-helper">
        <span>Current: <strong>${n} °C</strong> &nbsp;⇄&nbsp; Equivalent: <strong>${kVal} K</strong></span>
        <button type="button" class="button button-quiet button-sm" id="convert-param-temp" data-to="K" data-val="${kVal}">Convert input to Kelvin (${kVal} K)</button>
      </div>`;
    }
  }
  byId("parameter-detail").innerHTML = `
    <div class="detail-header">
      <p class="eyebrow">${escapeHtml(row.group)} · PARAMETER</p>
      <h2>${escapeHtml(row.id)}</h2>
      <p>${escapeHtml(row.description || "No description recorded.")}</p>
    </div>
    <div class="definition-grid">
      <div class="definition-cell"><span>Requirement</span><strong>${escapeHtml(requirement)}</strong></div>
      <div class="definition-cell"><span>Phase / kind</span><strong>${escapeHtml(row.phase ?? "—")} · ${escapeHtml(row.kind ?? "—")}</strong></div>
      <div class="definition-cell"><span>Allowed values</span><strong>${escapeHtml(allowed)}</strong></div>
      <div class="definition-cell"><span>Current source</span><strong>${escapeHtml(parameter.source_ref || "No source recorded")}</strong></div>
    </div>
    ${tempHelper}
    <div class="parameter-form">${fields}</div>
    <div class="detail-actions"><button class="button button-quiet" id="revert-parameter" type="button">Discard this parameter's edits</button><button class="button button-quiet" id="validate-parameter" type="button">Preview validation</button></div>`;
}

function readParameterFieldValue(input, row) {
  const path = input.dataset.paramField;
  const raw = input.value;
  if (raw === "") return null;
  if (path === "value" && row.kind === "boolean") return raw === "true";
  const numericKind = input.type === "number";
  if (numericKind) {
    const number = Number(raw);
    return Number.isFinite(number) ? number : null;
  }
  return raw;
}

function stageParameterInput(input) {
  const row = state.catalog.parameters.find((item) => item.id === state.selectedParameter);
  if (!row) return;
  const path = input.dataset.paramField;
  const value = readParameterFieldValue(input, row);
  const changes = state.stagedParameters[row.id] || {};
  changes[path] = value;
  state.stagedParameters[row.id] = changes;
  state.previewToken = null;
  renderParameterList();
  updateStagedState();
}

function filterDataFiles() {
  const query = byId("data-search").value.trim().toLowerCase();
  const kind = byId("data-kind-filter").value;
  return state.catalog.data_files.filter((file) => {
    if (!isDataFileVisible(file)) return false;
    const columns = (file.columns || []).map((column) => `${column.name} ${column.description}`).join(" ");
    const text = `${file.file} ${file.description} ${columns}`.toLowerCase();
    return (!kind || file.kind === kind) && (!query || matchesSearch(text, query));
  });
}

function renderDataList() {
  const files = filterDataFiles();
  byId("data-count").textContent = `${files.length} of ${state.catalog.data_files.length} files`;
  byId("nav-data-count").textContent = state.catalog.data_files.filter(isDataFileVisible).length;
  if (!files.length) {
    dataList.innerHTML = `<p class="empty-list">No data files or columns match your search.</p>`;
    return;
  }
  dataList.innerHTML = files.map((file) => {
    const selected = state.selectedDataFile === file.file ? " is-selected" : "";
    const findings = (state.report?.issues || []).filter((item) =>
      item.file === file.file || item.file === file.metadata_file
    );
    const issueLabel = findings.some((item) => item.severity === "error")
      ? `<span class="severity-pill error">Error</span>`
      : findings.length ? `<span class="severity-pill warning">${findings.length} findings</span>` : "";
    return `<button class="record-item${selected}" role="listitem" data-data-file="${escapeHtml(file.file)}">
      <span class="record-topline"><span class="record-id">${escapeHtml(file.file.split("/").at(-1))}</span>${issueLabel || `<span class="status-pill confirmed">${file.rows} rows</span>`}</span>
      <span class="record-description">${escapeHtml(file.description || file.kind)}</span>
      <span class="record-meta"><span>${escapeHtml(file.kind)}</span><span>·</span><span>${file.columns.length} columns</span><span>·</span><span>${file.rows} rows</span></span>
    </button>`;
  }).join("");
}

function dataPreviewRows(file) {
  const staged = state.stagedFiles[file.file];
  if (staged !== undefined) {
    const lines = staged.split(/\r?\n/).filter(Boolean).slice(0, 6);
    return `<pre class="sample-preview">${escapeHtml(lines.join("\n"))}</pre>`;
  }
  if (!file.sample_rows?.length) return `<p class="muted">No sample records in this file.</p>`;
  const headers = Object.keys(file.sample_rows[0]);
  return `<div class="data-preview"><table class="sample-table"><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr></thead><tbody>${file.sample_rows.map((row) => `<tr>${headers.map((header) => `<td>${escapeHtml(row[header])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function openDataFile(path) {
  const file = state.catalog.data_files.find((item) => item.file === path);
  if (!file) return;
  state.selectedDataFile = path;
  renderDataList();
  const findings = (state.report?.issues || []).filter((item) =>
    item.file === file.file || item.file === file.metadata_file
  );
  const columns = (file.columns || []).map((column) => `
    <tr><td>${escapeHtml(column.name)}</td><td>${escapeHtml(column.quantity_kind || "—")}</td><td>${escapeHtml(column.unit || "—")}</td><td>${column.required ? "Required" : "Optional"}</td></tr>
  `).join("");
  const findingsHtml = findings.length
    ? `<div class="validation-summary">${findings.slice(0, 6).map((item) => `<span class="severity-pill ${escapeHtml(item.severity)}">${escapeHtml(item.severity)} · ${escapeHtml(item.code)}</span>`).join("")}</div>`
    : `<p class="muted">No current findings for this file.</p>`;
  byId("data-detail").innerHTML = `
    <div class="detail-header">
      <p class="eyebrow">${escapeHtml(file.kind.toUpperCase())} · ${file.rows} RECORDS</p>
      <h2>${escapeHtml(file.file.split("/").at(-1))}</h2>
      <p>${escapeHtml(file.description || "No description recorded.")}</p>
      ${file.csv_error ? `<p class="error-message">${escapeHtml(file.csv_error)}</p>` : ""}
      ${file.metadata_error ? `<p class="error-message">Metadata error: ${escapeHtml(file.metadata_error)}</p>` : ""}
    </div>
    <div class="definition-grid">
      <div class="definition-cell"><span>CSV file</span><strong>${escapeHtml(file.file)}</strong></div>
      <div class="definition-cell"><span>Metadata</span><strong>${escapeHtml(file.metadata_file)}</strong></div>
    </div>
    <h3>Column contract</h3>
    <div class="data-preview"><table class="metadata-table"><thead><tr><th>Column</th><th>Kind</th><th>Unit</th><th>Requirement</th></tr></thead><tbody>${columns}</tbody></table></div>
    <h3 class="subsection-heading">Current findings</h3>${findingsHtml}
    <h3 class="subsection-heading">Sample / staged preview</h3>${dataPreviewRows(file)}
    <div class="upload-row"><label>Replace CSV <input type="file" accept=".csv,text/csv" data-upload-file="${escapeHtml(file.file)}"></label><label>Replace metadata <input type="file" accept=".yaml,.yml,text/yaml" data-upload-file="${escapeHtml(file.metadata_file)}"></label><span>Files are staged only; use Preview &amp; apply to save.</span></div>`;
}

function renderValidation() {
  const report = state.report;
  if (!report) return;
  byId("summary-errors").textContent = report.error_count;
  byId("summary-warnings").textContent = report.warning_count;
  const totalInputs = state.catalog.parameters.length + state.catalog.data_files.length;
  byId("summary-inputs").textContent = totalInputs;
  byId("nav-parameter-count").textContent = state.catalog.parameters.filter(isParameterVisible).length;
  byId("nav-data-count").textContent = state.catalog.data_files.filter(isDataFileVisible).length;
  byId("nav-error-count").textContent = report.error_count;
  byId("validation-summary").innerHTML = `
    <span class="severity-pill ${report.error_count ? "error" : "info"}">${report.error_count} blocking errors</span>
    <span class="severity-pill warning">${report.warning_count} warnings</span>
    <span class="count-pill">${report.issues.length} total findings</span>
    ${stagedCount() ? `<span class="count-pill">Preview includes staged edits</span>` : ""}`;
  byId("readiness-stamp").innerHTML = report.error_count
    ? `<span class="severity-pill error">${report.error_count} blockers</span>`
    : `<span class="status-dot"></span><span>No blocking input errors</span>`;
  byId("next-action-title").textContent = report.error_count
    ? "Resolve blocking input findings"
    : report.warning_count ? "Review data-quality warnings" : "Inputs pass validation";
  byId("next-action-copy").textContent = report.error_count
    ? "Open a finding to jump to the parameter or data file that needs attention."
    : report.warning_count
      ? "No blocking issues were found; warnings identify incomplete provenance or metadata."
      : "Registered parameters and data files have no reported issues.";

  const categories = [...new Set(report.issues.map((item) => item.code.split(".")[0]))].sort();
  const categorySelect = byId("finding-category-filter");
  const selectedCategory = categorySelect.value;
  categorySelect.innerHTML = `<option value="">All categories</option>${categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join("")}`;
  categorySelect.value = categories.includes(selectedCategory) ? selectedCategory : "";

  const query = byId("finding-search").value.trim().toLowerCase();
  const severity = byId("severity-filter").value;
  const category = categorySelect.value;
  const issues = report.issues.filter((item) => {
    const text = `${item.code} ${item.file} ${item.location} ${item.message} ${item.expected} ${item.found}`.toLowerCase();
    return (!severity || item.severity === severity)
      && (!category || item.code.split(".")[0] === category)
      && (!query || matchesSearch(text, query));
  });
  if (!issues.length) {
    findingList.innerHTML = `<p class="empty-list">No findings match these filters.</p>`;
    return;
  }
  findingList.innerHTML = issues.map((item, index) => `
    <article class="finding-card ${escapeHtml(item.severity)}">
      <span class="severity-pill ${escapeHtml(item.severity)}">${escapeHtml(item.severity)}</span>
      <div class="finding-body">
        <h3>${escapeHtml(item.message)}</h3>
        <p>${escapeHtml(item.code)}${item.suggestion ? ` · ${escapeHtml(item.suggestion)}` : ""}</p>
        <p class="finding-location">${escapeHtml(item.file)}${item.location ? ` · ${escapeHtml(item.location)}` : ""}</p>
        ${item.expected || item.found ? `<p>Expected: ${escapeHtml(item.expected || "—")} · Found: ${escapeHtml(item.found || "—")}</p>` : ""}
      </div>
      <button class="finding-action" data-finding-index="${index}" type="button">Open</button>
    </article>`).join("");
  findingList.querySelectorAll("[data-finding-index]").forEach((button) => {
    button.addEventListener("click", () => openFinding(issues[Number(button.dataset.findingIndex)]));
  });
}

function openFinding(issue) {
  if (issue.file.startsWith("inputs/parameters/")) {
    const parameter = state.catalog.parameters.find((item) => item.id === issue.location || issue.location.startsWith(`${item.id}.`));
    if (parameter) {
      showView("parameters");
      openParameter(parameter.id);
      return;
    }
  }
  const data = state.catalog.data_files.find((item) =>
    item.file === issue.file || item.metadata_file === issue.file
  );
  if (data) {
    showView("data");
    openDataFile(data.file);
    return;
  }
  showView("validation");
}

function searchItems() {
  const items = [];
  for (const row of state.catalog.parameters.filter(isParameterVisible)) {
    items.push({
      type: "parameter",
      id: row.id,
      label: row.id,
      description: `${row.description || ""} · ${row.group}`,
      search: `${row.id} ${row.description} ${row.group} ${row.source_ref} ${row.required_when}`,
    });
  }
  for (const file of state.catalog.data_files.filter(isDataFileVisible)) {
    items.push({
      type: "data",
      id: file.file,
      label: file.file,
      description: `${file.description || file.kind} · ${(file.columns || []).map((column) => column.name).join(", ")}`,
      search: `${file.file} ${file.description} ${file.kind} ${(file.columns || []).map((column) => `${column.name} ${column.description}`).join(" ")}`,
    });
  }
  for (const item of [...state.catalog.outputs, ...state.catalog.metrics]) {
    items.push({
      type: "output",
      id: item.id,
      label: item.id,
      description: `${item.name || ""} · ${item.description || ""}`,
      search: `${item.id} ${item.name} ${item.description} ${item.unit}`,
    });
  }
  for (const run of state.runs) {
    items.push({
      type: "run",
      id: run.scenario_id,
      label: run.scenario_id,
      description: `${run.scope || "Saved run"} · ${run.valid ? `${run.rows} rows` : run.validation_error}`,
      search: `${run.scenario_id} ${run.scope} ${run.file}`,
    });
  }
  for (const finding of state.report?.issues || []) {
    items.push({
      type: "finding",
      id: `${finding.code} ${finding.location}`,
      label: finding.location || finding.file,
      description: `${finding.severity}: ${finding.message}`,
      search: `${finding.code} ${finding.file} ${finding.location} ${finding.message}`,
      finding,
    });
  }
  return items;
}

function renderGlobalSearch() {
  const query = byId("global-search").value.trim().toLowerCase();
  const results = byId("global-results");
  if (query.length < 2) {
    results.hidden = true;
    byId("global-search").setAttribute("aria-expanded", "false");
    return;
  }
  const matches = searchItems().filter((item) => matchesSearch(item.search, query)).slice(0, 12);
  results.innerHTML = matches.length
    ? matches.map((item, index) => `<button class="search-result" role="option" data-result-index="${index}" type="button"><strong>${escapeHtml(item.label)}</strong><span>${escapeHtml(item.description)}</span></button>`).join("")
    : `<p class="empty-list">No project items match “${escapeHtml(query)}”.</p>`;
  results.hidden = false;
  byId("global-search").setAttribute("aria-expanded", "true");
  results.querySelectorAll("[data-result-index]").forEach((button) => {
    button.addEventListener("click", () => {
      const item = matches[Number(button.dataset.resultIndex)];
      results.hidden = true;
      byId("global-search").setAttribute("aria-expanded", "false");
      byId("global-search").value = "";
      if (item.type === "parameter") {
        showView("parameters");
        openParameter(item.id);
      } else if (item.type === "data") {
        showView("data");
        openDataFile(item.id);
      } else if (item.type === "finding") {
        showView("validation");
        openFinding(item.finding);
      } else if (item.type === "run") {
        showView("runs");
        if (!state.selectedRuns.includes(item.id)) {
          state.selectedRuns = [...state.selectedRuns, item.id];
        }
        renderRunPicker();
        loadSelectedRuns();
      } else {
        showView("runs");
        if (ANALYSIS_VARIABLES[item.id]) {
          state.selectedVariables = [item.id];
          renderVariablePicker();
          renderAnalysis();
        }
      }
    });
  });
}

async function refreshValidation() {
  try {
    state.report = await request("/api/validation");
    renderValidation();
    renderParameterList();
    renderDataList();
    await refreshRunReadiness();
  } catch (error) {
    setGlobalError(error.message);
  }
}

async function previewStaged() {
  const payload = {
    parameter_overrides: state.stagedParameters,
    file_overrides: state.stagedFiles,
    module_overrides: state.stagedModules,
  };
  const preview = await request("/api/validation/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.previewToken = preview.preview_token;
  state.report = preview;
  renderValidation();
  renderParameterList();
  renderDataList();
  await refreshRunReadiness();
}

async function applyStaged() {
  const uploadedWeatherPath = state.newWeatherPath?.file || null;
  const payload = {
    parameter_overrides: state.stagedParameters,
    file_overrides: state.stagedFiles,
    module_overrides: state.stagedModules,
    preview_token: state.previewToken,
  };
  state.report = await request("/api/validation/apply", {
    method: "POST",
    body: JSON.stringify({ ...payload, confirmed: true }),
  });
  state.stagedParameters = {};
  state.stagedFiles = {};
  state.stagedModules = {};
  state.weatherUpload = { csv: null, metadata: null };
  state.newWeatherPath = null;
  state.previewToken = null;
  byId("weather-csv-upload").value = "";
  byId("weather-meta-upload").value = "";
  byId("weather-upload-status").textContent = uploadedWeatherPath
    ? "Weather files saved. The new dataset is now available for preflight."
    : "Choose both files with the same base filename.";
  state.catalog = await request("/api/catalog");
  await loadModel();
  renderParameterGroups();
  renderParameterList();
  renderDataList();
  updateStagedState();
  renderValidation();
  await loadWeather(uploadedWeatherPath);
  await refreshRunReadiness();
}

function renderParameterGroups() {
  const select = byId("parameter-group-filter");
  const groups = [...new Set(
    state.catalog.parameters.filter(isParameterVisible).map((row) => row.group),
  )].sort();
  select.innerHTML = `<option value="">All groups</option>${groups.map((group) => `<option value="${escapeHtml(group)}">${escapeHtml(group)}</option>`).join("")}`;
}

function moduleEnabled(module) {
  return state.stagedModules[module.id] ?? module.enabled;
}

function moduleOwnsParameter(module, row) {
  if (module.parameter_ids?.length) return module.parameter_ids.includes(row.id);
  const filename = row.file?.split("/").at(-1)?.replace(/\.ya?ml$/i, "");
  return (module.parameter_files || []).includes(filename);
}

function isParameterVisible(row) {
  const owners = state.modules.filter((module) => moduleOwnsParameter(module, row));
  return !owners.length || owners.some(moduleEnabled);
}

function isDataFileVisible(file) {
  const owners = state.modules.filter((module) =>
    (module.data_kinds || []).includes(file.kind)
  );
  return !owners.length || owners.some(moduleEnabled);
}

async function loadModel() {
  try {
    const [trace, modules] = await Promise.all([
      request("/api/model/trace"),
      request("/api/modules"),
    ]);
    state.trace = trace;
    state.modules = modules;
    state.modelError = null;
    byId("model-load-status").textContent = `Verified scope: ${trace.scope}. ${trace.required_parameter_ids.length} required parameter values and ${trace.steps.length} calculation steps.`;
    renderModuleList();
    renderParameterGroups();
    renderParameterList();
    renderDataList();
    renderTraceGraph();
    renderTraceRunSelect();
    renderTraceRunSnapshot();
  } catch (error) {
    state.modelError = error.message;
    byId("model-load-status").textContent = `Could not load the calculation trace or module registry: ${error.message}`;
    byId("module-list").innerHTML = `<p class="error-message">Module registry unavailable: ${escapeHtml(error.message)}</p>`;
    byId("trace-graph").innerHTML = `<p class="error-message">Calculation trace unavailable.</p>`;
  }
}

function setModelTab(name) {
  document.querySelectorAll("[data-model-tab]").forEach((button) => {
    const selected = button.dataset.modelTab === name;
    button.classList.toggle("is-active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
  document.querySelectorAll(".model-panel").forEach((panel) => {
    panel.hidden = panel.id !== `model-panel-${name}`;
  });
}

function stageModuleToggle(input) {
  const module = state.modules.find((item) => item.id === input.dataset.moduleToggle);
  if (!module) return;
  if (input.checked === module.enabled) {
    delete state.stagedModules[module.id];
  } else {
    state.stagedModules[module.id] = input.checked;
  }
  state.previewToken = null;
  renderModuleList();
  renderParameterGroups();
  renderParameterList();
  renderDataList();
  renderGlobalSearch();
  updateStagedState();
}

function parameterSnapshotTable(parameterIds, snapshot = null) {
  const rows = parameterIds.map((id) => {
    const row = state.catalog.parameters.find((parameter) => parameter.id === id);
    const recorded = snapshot?.[id];
    const current = row ? effectiveParameter(row) : null;
    const entry = recorded || current;
    if (!entry) {
      return `<tr><td>${escapeHtml(id)}</td><td colspan="4">Not present in the current catalog</td></tr>`;
    }
    return `<tr><td><code>${escapeHtml(id)}</code></td><td>${escapeHtml(display(entry.value))}</td><td>${escapeHtml(entry.unit || row?.unit || "—")}</td><td>${escapeHtml(entry.status || "—")}</td><td>${escapeHtml(entry.source_ref || "—")}</td></tr>`;
  }).join("");
  return `<div class="trace-table-wrap"><table class="trace-table"><thead><tr><th>Parameter</th><th>Value</th><th>Unit</th><th>Status</th><th>Source</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function relatedTraceNodes(nodeId) {
  const edges = state.trace?.edges || [];
  const upstream = new Set([nodeId]);
  const downstream = new Set([nodeId]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const edge of edges) {
      if (upstream.has(edge.target) && !upstream.has(edge.source)) {
        upstream.add(edge.source);
        changed = true;
      }
      if (downstream.has(edge.source) && !downstream.has(edge.target)) {
        downstream.add(edge.target);
        changed = true;
      }
    }
  }
  return { upstream, downstream };
}

function traceNodeButton(node, kind, related = { upstream: new Set(), downstream: new Set() }) {
  const selected = node.id === state.selectedTraceNode;
  const relation = selected ? " is-selected"
    : related.upstream.has(node.id) ? " is-upstream"
      : related.downstream.has(node.id) ? " is-downstream" : "";
  let detail = "";
  if (kind === "inputs") {
    detail = node.kind === "weather"
      ? `${(node.columns || []).length} required weather columns`
      : `${(node.parameter_ids || []).length} parameter values`;
  } else if (kind === "steps") {
    detail = node.unit || "calculation";
  } else {
    detail = `${(node.fields || []).length} saved fields`;
  }
  return `<button type="button" class="trace-node${relation}" data-trace-node="${escapeHtml(node.id)}" data-trace-kind="${kind}" aria-pressed="${selected}">
    <strong>${escapeHtml(node.label)}</strong><small>${escapeHtml(detail)}</small>
  </button>`;
}

function renderTraceGraph() {
  const container = byId("trace-graph");
  if (!state.trace) {
    if (state.modelError) container.innerHTML = `<p class="error-message">${escapeHtml(state.modelError)}</p>`;
    return;
  }
  const related = state.selectedTraceNode
    ? relatedTraceNodes(state.selectedTraceNode)
    : { upstream: new Set(), downstream: new Set() };
  const lanes = [
    ["inputs", "Inputs", state.trace.inputs],
    ["steps", "Equations and transformations", state.trace.steps],
    ["outputs", "Outputs", state.trace.outputs],
  ];
  container.innerHTML = lanes.map(([kind, label, nodes]) => `<section class="trace-lane" aria-label="${escapeHtml(label)}">
    <h2>${escapeHtml(label)}</h2>
    <div class="trace-node-list">${nodes.map((node) => traceNodeButton(node, kind, related)).join("")}</div>
  </section>`).join("");
  if (state.selectedTraceNode) renderTraceDetail(state.selectedTraceNode);
}

function renderTraceDetail(nodeId) {
  const container = byId("trace-detail");
  const input = state.trace.inputs.find((item) => item.id === nodeId);
  const step = state.trace.steps.find((item) => item.id === nodeId);
  const output = state.trace.outputs.find((item) => item.id === nodeId);
  if (input) {
    const body = input.kind === "weather"
      ? `<p>Selected hourly file: <code>${escapeHtml(byId("weather-select").value || "No compatible weather selected")}</code></p>
        <div class="trace-table-wrap"><table class="trace-table"><thead><tr><th>Column</th><th>Required data</th><th>Unit</th><th>Notes</th></tr></thead><tbody>${input.columns.map((column) => `<tr><td><code>${escapeHtml(column.id)}</code></td><td>${escapeHtml(column.label)}</td><td>${escapeHtml(column.unit)}</td><td>${escapeHtml(column.note || "Used by the PVT weather loader.")}</td></tr>`).join("")}</tbody></table></div>`
      : parameterSnapshotTable(input.parameter_ids);
    container.innerHTML = `<p class="eyebrow">INPUT GROUP</p><h2>${escapeHtml(input.label)}</h2><p>Current workbench values are shown below; choose a saved run to compare its recorded snapshot.</p>${body}`;
    return;
  }
  if (step) {
    const ids = step.parameter_ids || [];
    const dependencyLabels = (step.depends_on || []).map((id) =>
      state.trace.steps.find((item) => item.id === id)?.label || id
    );
    container.innerHTML = `<p class="eyebrow">CALCULATION STEP · ${escapeHtml(step.unit || "")}</p>
      <h2>${escapeHtml(step.label)}</h2><p>${escapeHtml(step.description || "")}</p>
      <div class="formula-block"><span>Implemented formula / rule</span><code>${escapeHtml(step.formula || "No equation is recorded for this step.")}</code></div>
      <dl class="trace-facts"><div><dt>Input groups</dt><dd>${escapeHtml((step.input_groups || []).map((id) => state.trace.inputs.find((item) => item.id === id)?.label || id).join(", ") || "Previous calculation outputs")}</dd></div><div><dt>Prior calculations</dt><dd>${escapeHtml(dependencyLabels.join(", ") || "None")}</dd></div><div><dt>Code source</dt><dd><code>${escapeHtml(step.source || "—")}</code></dd></div></dl>
      ${ids.length ? `<h3>Current parameter values</h3>${parameterSnapshotTable(ids)}` : ""}`;
    return;
  }
  if (output) {
    container.innerHTML = `<p class="eyebrow">SAVED OUTPUT</p><h2>${escapeHtml(output.label)}</h2><p>${escapeHtml(output.description)}</p>
      <div class="trace-table-wrap"><table class="trace-table"><thead><tr><th>Field</th><th>Unit / shape</th></tr></thead><tbody>${output.fields.map((field) => `<tr><td><code>${escapeHtml(field.id)}</code></td><td>${escapeHtml(field.unit)}</td></tr>`).join("")}</tbody></table></div>
      <p class="muted">Produced by: ${escapeHtml(output.produced_by.map((id) => state.trace.steps.find((item) => item.id === id)?.label || id).join(", "))}</p>`;
  }
}

function renderTraceRunSelect() {
  const select = byId("trace-run-select");
  const validRuns = state.runs.filter((run) => run.valid);
  if (!validRuns.some((run) => run.scenario_id === state.selectedTraceRunId)) {
    state.selectedTraceRunId = validRuns[0]?.scenario_id || "";
  }
  select.innerHTML = validRuns.length
    ? validRuns.map((run) => `<option value="${escapeHtml(run.scenario_id)}" ${run.scenario_id === state.selectedTraceRunId ? "selected" : ""}>${escapeHtml(run.scenario_id)}</option>`).join("")
    : `<option value="">No valid saved runs</option>`;
}

function renderTraceRunSnapshot() {
  const container = byId("trace-run-snapshot");
  const run = state.runs.find((item) => item.scenario_id === state.selectedTraceRunId);
  if (!run) {
    container.innerHTML = `<p class="muted">No saved run is available. Run a PVT scenario to record its input snapshot and outputs.</p>`;
    return;
  }
  const summary = [
    ["Electrical energy", run.electrical_energy_kwh, "kWh"],
    ["Useful heat", run.useful_heat_kwh, "kWh"],
    ["Average electrical power", run.average_electrical_power_w, "W"],
    ["Average useful heat", run.average_useful_heat_w, "W"],
    ["Electrical metric (M-PV-01)", run.metrics?.["M-PV-01"], "J"],
    ["Thermal metric (M-TH-01)", run.metrics?.["M-TH-01"], "J"],
  ].filter(([, value]) => value !== undefined && value !== null);
  const summaryHtml = summary.length
    ? `<div class="trace-summary-grid">${summary.map(([label, value, unit]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(display(value))} ${escapeHtml(unit)}</strong></div>`).join("")}</div>`
    : `<p class="muted">This run has no summary output fields available.</p>`;
  const snapshot = run.input_parameters;
  const inputHtml = snapshot && typeof snapshot === "object"
    ? parameterSnapshotTable(Object.keys(snapshot), snapshot)
    : `<p class="muted">Input snapshot unavailable for this saved run (it may predate snapshot recording).</p>`;
  container.innerHTML = `<p class="muted"><strong>${escapeHtml(run.scenario_id)}</strong> · ${escapeHtml(run.weather_source || "weather source unavailable")} · ${escapeHtml(display(run.steps))} hourly records</p>
    <h3>Summary outputs</h3>${summaryHtml}<h3>Recorded input values and provenance</h3>${inputHtml}`;
}

function renderModuleList() {
  const container = byId("module-list");
  if (!state.modules.length) {
    container.innerHTML = `<p class="muted">No modules are registered.</p>`;
    return;
  }
  container.innerHTML = state.modules.map((module) => {
    const enabled = moduleEnabled(module);
    const operational = module.operational_status === "operational";
    const readinessLabel = module.readiness === "ready"
      ? "Ready"
      : operational ? "Requirements need attention" : "Not connected to current run";
    const issueList = (module.issues || []).length
      ? `<ul class="module-issues">${module.issues.map((issue) => `<li><span class="severity-pill ${escapeHtml(issue.severity)}">${escapeHtml(issue.severity)}</span><span>${escapeHtml(issue.message)} <small>${escapeHtml(issue.file || "")}${issue.location ? ` · ${escapeHtml(issue.location)}` : ""}</small></span></li>`).join("")}</ul>`
      : `<p class="muted">${operational ? "No current blocking requirements for this module." : "No parameter validation findings are currently associated with these files."}</p>`;
    const requirements = enabled
      ? `<div class="module-requirements">
          <strong>${operational ? readinessLabel : `${readinessLabel} · preparation only`}</strong>
          <ul>${(module.requirements || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          ${issueList}
          ${!operational ? `<p class="muted">Enabling this module does not execute it and does not block the current PVT-only run.</p>` : ""}
        </div>`
      : `<p class="muted module-off-note">Off · associated inputs are hidden from the parameter and data browsers. Saved values are unchanged.</p>`;
    const staged = Object.hasOwn(state.stagedModules, module.id);
    return `<article class="module-card panel${enabled ? " is-enabled" : ""}">
      <div class="module-card-heading">
        <div><p class="eyebrow">${escapeHtml(module.operational_status.replaceAll("_", " "))}</p><h3>${escapeHtml(module.name)}</h3><p>${escapeHtml(module.description)}</p></div>
        <label class="module-toggle"><input type="checkbox" data-module-toggle="${escapeHtml(module.id)}" ${enabled ? "checked" : ""}><span>${enabled ? "Enabled" : "Disabled"}${staged ? " · staged" : ""}</span></label>
      </div>
      ${requirements}
    </article>`;
  }).join("");
}

async function loadWeather(preferredPath = null) {
  state.weather = await request("/api/weather");
  const select = byId("weather-select");
  const currentPath = preferredPath || select.value;
  select.innerHTML = state.weather.map((item) => `<option value="${escapeHtml(item.file)}" ${item.valid ? "" : "disabled"}>${escapeHtml(item.file.split("/").at(-1))}${item.valid ? "" : " · not compatible"}</option>`).join("");
  const firstValid = state.weather.find((item) => item.valid);
  if (state.weather.some((item) => item.file === currentPath && item.valid)) {
    select.value = currentPath;
  } else if (firstValid) {
    select.value = firstValid.file;
  }
  const quality = byId("weather-quality");
  quality.textContent = firstValid
    ? `${firstValid.rows.toLocaleString()} rows · hourly intervals verified`
    : "No compatible hourly weather file. Inspect data validation.";
  updateWeatherOption();
}

async function refreshRunReadiness() {
  const weather = byId("weather-select").value;
  if (!weather) {
    byId("run-blocker").textContent = "No compatible weather file is available.";
    byId("start-run").dataset.ready = "";
    updateStagedState();
    return;
  }
  try {
    const readiness = await request(`/api/run-readiness?weather=${encodeURIComponent(weather)}`);
    const blocker = byId("run-blocker");
    if (readiness.ok) {
      blocker.textContent = "PVT parameters and selected hourly weather pass run preflight.";
      blocker.classList.add("is-ready");
      byId("start-run").dataset.ready = "true";
    } else {
      blocker.classList.remove("is-ready");
      blocker.innerHTML = `<strong>Run blocked.</strong> ${readiness.issues.map((item) => escapeHtml(item.message)).join("<br>")}`;
      byId("start-run").dataset.ready = "";
    }
  } catch (error) {
    byId("run-blocker").textContent = `Preflight failed: ${error.message}`;
    byId("start-run").dataset.ready = "";
  }
  updateStagedState();
}

function updateWeatherOption() {
  const item = state.weather.find((entry) => entry.file === byId("weather-select").value);
  byId("weather-quality").textContent = item?.valid
    ? `${item.rows.toLocaleString()} rows · hourly intervals verified`
    : item?.error || "Choose a compatible hourly weather file.";
  refreshRunReadiness();
}

async function refreshRuns() {
  state.runs = await request("/api/runs");
  renderTraceRunSelect();
  renderTraceRunSnapshot();
  const validIds = state.runs.filter((run) => run.valid).map((run) => run.scenario_id);
  state.selectedRuns = state.selectedRuns.filter((id) => validIds.includes(id));
  if (!state.selectedRuns.length) state.selectedRuns = validIds.slice(0, 3);
  renderRunPicker();
  await loadSelectedRuns();
}

function selectedRunRecords() {
  return state.selectedRuns
    .map((id) => state.runs.find((run) => run.scenario_id === id))
    .filter((run) => run?.valid && state.seriesByRun[run.scenario_id])
    .map((run) => ({
      run,
      rows: state.seriesByRun[run.scenario_id],
    }));
}

function renderRunPicker() {
  const picker = byId("run-picker");
  if (!state.runs.length) {
    picker.innerHTML = `<p class="muted">No saved scenarios yet. Run a PVT case to begin comparing.</p>`;
    return;
  }
  picker.innerHTML = state.runs.map((run) => {
    const id = run.scenario_id || "";
    const checked = state.selectedRuns.includes(id);
    const detail = run.valid
      ? `${Number(run.rows || 0).toLocaleString()} records · ${run.scope || "PVT-only"}`
      : `Output invalid · ${run.validation_error || "check the result files"}`;
    return `<label class="selection-option${run.valid ? "" : " is-disabled"}">
      <input type="checkbox" data-run-id="${escapeHtml(id)}" ${checked ? "checked" : ""} ${run.valid ? "" : "disabled"}>
      <span><strong>${escapeHtml(id || run.file)}</strong><small>${escapeHtml(detail)}</small></span>
    </label>`;
  }).join("");
}

async function loadSelectedRuns() {
  const loadId = ++state.selectionLoadId;
  const selected = state.selectedRuns.filter((id) =>
    state.runs.some((run) => run.scenario_id === id && run.valid)
  );
  state.selectedRuns = selected;
  byId("result-quality").textContent = selected.length ? "Loading selected run series…" : "Select at least one valid saved run.";
  if (!selected.length) {
    renderVariablePicker();
    renderAnalysis();
    return;
  }
  await Promise.all(selected.map(async (scenario) => {
    if (state.seriesByRun[scenario]) return;
    try {
      const result = await request(`/api/runs/${encodeURIComponent(scenario)}/series`);
      state.seriesByRun[scenario] = result.rows;
      delete state.seriesErrors[scenario];
    } catch (error) {
      state.seriesErrors[scenario] = error.message;
    }
  }));
  if (loadId !== state.selectionLoadId) return;
  if (!state.variablesInitialized) {
    const available = availableVariables();
    state.selectedVariables = DEFAULT_VARIABLES.filter((column) => available.includes(column));
    if (!state.selectedVariables.length) state.selectedVariables = available.slice(0, 1);
    state.variablesInitialized = true;
  } else {
    state.selectedVariables = state.selectedVariables.filter((column) =>
      availableVariables().includes(column)
    );
  }
  renderVariablePicker();
  renderAnalysis();
}

function availableVariables() {
  const columns = new Set();
  for (const { rows } of selectedRunRecords()) {
    for (const column of Object.keys(rows[0] || {})) {
      if (column !== "timestamp" && column !== "converged" && rows.some((row) => Number.isFinite(Number(row[column])))) {
        columns.add(column);
      }
    }
  }
  return Object.keys(ANALYSIS_VARIABLES).filter((column) => columns.has(column));
}

function renderVariablePicker() {
  const picker = byId("variable-picker");
  const available = availableVariables();
  if (!available.length) {
    picker.innerHTML = `<p class="muted">Select a valid run with numeric weather or PVT series.</p>`;
    return;
  }
  const groups = ["Weather drivers", "PVT outputs"];
  picker.innerHTML = groups.map((group) => {
    const options = available.filter((column) => ANALYSIS_VARIABLES[column].group === group);
    if (!options.length) return "";
    return `<div class="variable-group"><strong>${group}</strong>${options.map((column) => `
      <label class="selection-option variable-option">
        <input type="checkbox" data-variable="${column}" ${state.selectedVariables.includes(column) ? "checked" : ""}>
        <span>${escapeHtml(getVariableLabel(column))} <small>${escapeHtml(getVariableUnit(column))}</small></span>
      </label>`).join("")}</div>`;
  }).join("");
}

function getFullDomain(records = selectedRunRecords()) {
  let minimum = Infinity;
  let maximum = -Infinity;
  for (const { rows } of records) {
    for (const row of rows) {
      const time = Date.parse(row.timestamp);
      if (!Number.isFinite(time)) continue;
      minimum = Math.min(minimum, time);
      maximum = Math.max(maximum, time);
    }
  }
  return Number.isFinite(minimum) ? { start: minimum, end: maximum } : null;
}

function getCurrentDomain(records = selectedRunRecords()) {
  const full = getFullDomain(records);
  if (!full) return null;
  if (!state.zoomRange) return full;
  const start = Math.max(full.start, state.zoomRange.start);
  const end = Math.min(full.end, state.zoomRange.end);
  if (end <= start) {
    state.zoomRange = null;
    state.zoomHistory = [];
    return full;
  }
  return { start, end };
}

function formatTime(value) {
  return Number.isFinite(value) ? new Date(value).toLocaleString() : "—";
}

function formatTimeInput(value) {
  if (!Number.isFinite(value)) return "";
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function formatNumber(value, digits = 3) {
  return Number.isFinite(value)
    ? value.toLocaleString(undefined, { maximumFractionDigits: digits })
    : "—";
}

function visibleRows(rows, domain) {
  return rows.filter((row) => {
    const time = Date.parse(row.timestamp);
    return Number.isFinite(time) && time >= domain.start && time <= domain.end;
  });
}

function renderAnalysis() {
  const records = selectedRunRecords();
  const variables = state.selectedVariables.filter((column) => availableVariables().includes(column));
  state.selectedVariables = variables;
  const domain = getCurrentDomain(records);
  const chartRoot = byId("analysis-charts");
  const empty = byId("chart-empty");
  const hasData = records.length > 0 && Boolean(domain);
  empty.classList.toggle("is-hidden", hasData && variables.length > 0);
  empty.textContent = records.length
    ? "Choose one or more numeric variables to chart."
    : "Choose one or more valid saved runs to compare.";
  if (!hasData || !variables.length) {
    chartRoot.innerHTML = "";
    byId("analysis-statistics").innerHTML = `<p class="muted">Select runs and variables to calculate statistics.</p>`;
    byId("analysis-table").innerHTML = `<p class="muted">Select runs and variables to inspect hourly records.</p>`;
    byId("parameter-snapshot").innerHTML = `<p class="muted">Select saved runs to inspect their recorded inputs.</p>`;
    byId("export-table").disabled = true;
    byId("result-quality").textContent = records.length
      ? "Output check passed. Select one or more numeric variables."
      : (Object.keys(state.seriesErrors).length
        ? Object.entries(state.seriesErrors).map(([id, error]) => `${id}: ${error}`).join(" · ")
        : "Select at least one valid saved run.");
    syncRangeControls(null);
    return;
  }

  chartRoot.innerHTML = variables.map((column) => {
    const label = getVariableLabel(column);
    const unit = getVariableUnit(column);
    const legend = records.map(({ run }, index) => `
      <span class="chart-legend-item"><i style="--series-color:${SERIES_COLORS[index % SERIES_COLORS.length]}"></i>${escapeHtml(run.scenario_id)}</span>
    `).join("");
    return `<section class="analysis-chart-card" data-chart-card="${column}">
      <div class="analysis-chart-heading"><div><h3>${escapeHtml(label)}</h3><span>${escapeHtml(unit)}</span></div></div>
      <div class="chart-surface"><canvas class="analysis-chart" data-chart="${column}" tabindex="0" role="img" aria-label="${escapeHtml(label)} time-series comparison"></canvas></div>
      <div class="chart-legend">${legend}</div>
    </section>`;
  }).join("");

  syncRangeControls(domain);
  chartRoot.querySelectorAll("canvas[data-chart]").forEach((canvas) => {
    canvas.addEventListener("pointerdown", handleChartPointerDown);
    canvas.addEventListener("pointermove", handleChartPointerMove);
    canvas.addEventListener("pointerup", handleChartPointerUp);
    canvas.addEventListener("pointercancel", handleChartPointerUp);
    canvas.addEventListener("pointerleave", handleChartPointerLeave);
    drawChart(canvas);
  });
  renderStatistics(records, variables, domain);
  renderAnalysisTable(records, variables, domain);
  renderParameterSnapshot(records);
  const failures = Object.entries(state.seriesErrors)
    .filter(([id]) => state.selectedRuns.includes(id))
    .map(([id, error]) => `${id}: ${error}`);
  byId("result-quality").textContent = failures.length
    ? `Could not read: ${failures.join(" · ")}`
    : `${records.length} run${records.length === 1 ? "" : "s"} · ${variables.length} variable${variables.length === 1 ? "" : "s"} · output checks passed`;
}

function syncRangeControls(domain) {
  const start = byId("range-start");
  const end = byId("range-end");
  if (domain) {
    start.value = formatTimeInput(domain.start);
    end.value = formatTimeInput(domain.end);
    byId("time-range-copy").textContent = state.zoomRange
      ? `${formatTime(domain.start)} — ${formatTime(domain.end)}`
      : `Full range · ${formatTime(domain.start)} — ${formatTime(domain.end)}`;
  } else {
    start.value = "";
    end.value = "";
    byId("time-range-copy").textContent = "Full time range";
  }
  const full = getFullDomain();
  byId("zoom-out").disabled = !state.zoomHistory.length;
  byId("reset-zoom").disabled = !state.zoomRange;
  byId("apply-range").disabled = !full || !start.value || !end.value;
}

function drawAnalysisCanvases() {
  byId("analysis-charts").querySelectorAll("canvas[data-chart]").forEach(drawChart);
}

function drawChart(canvas) {
  const column = canvas.dataset.chart;
  const records = selectedRunRecords();
  const domain = getCurrentDomain(records);
  const rect = canvas.getBoundingClientRect();
  if (!domain || rect.width < 10) return;
  const ratio = window.devicePixelRatio || 1;
  const width = rect.width;
  const height = Math.max(180, rect.height);
  canvas.width = Math.floor(width * ratio);
  canvas.height = Math.floor(height * ratio);
  const context = canvas.getContext("2d");
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);
  const margin = { left: 58, right: 14, top: 16, bottom: 34 };
  const chartWidth = Math.max(1, width - margin.left - margin.right);
  const chartHeight = Math.max(1, height - margin.top - margin.bottom);
  const series = records.map(({ run, rows }, index) => ({
    run,
    color: SERIES_COLORS[index % SERIES_COLORS.length],
    rows: visibleRows(rows, domain).filter((row) => Number.isFinite(Number(row[column]))),
  }));
  const values = series.flatMap((item) => item.rows.map((row) => getVariableValue(column, Number(row[column]))));
  if (!values.length) return;
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    const padding = Math.abs(min) * 0.05 || 1;
    min -= padding;
    max += padding;
  } else {
    const padding = (max - min) * 0.05;
    min -= padding;
    max += padding;
  }
  const x = (time) => margin.left + ((time - domain.start) / (domain.end - domain.start || 1)) * chartWidth;
  const y = (value) => margin.top + ((max - value) / (max - min)) * chartHeight;
  context.font = "11px Segoe UI, sans-serif";
  context.strokeStyle = "#e4ece8";
  context.fillStyle = "#71878a";
  context.lineWidth = 1;
  for (let tick = 0; tick <= 4; tick += 1) {
    const lineY = margin.top + (chartHeight * tick) / 4;
    const value = max - ((max - min) * tick) / 4;
    context.beginPath();
    context.moveTo(margin.left, lineY);
    context.lineTo(width - margin.right, lineY);
    context.stroke();
    context.textAlign = "right";
    context.fillText(formatNumber(value, 2), margin.left - 8, lineY + 4);
  }
  for (const item of series) {
    context.beginPath();
    item.rows.forEach((row, index) => {
      const pointX = x(Date.parse(row.timestamp));
      const pointY = y(getVariableValue(column, Number(row[column])));
      if (index === 0) context.moveTo(pointX, pointY);
      else context.lineTo(pointX, pointY);
    });
    context.strokeStyle = item.color;
    context.lineWidth = 1.8;
    context.stroke();
  }
  context.fillStyle = "#526d71";
  context.textAlign = "center";
  [domain.start, domain.start + (domain.end - domain.start) / 2, domain.end].forEach((time) => {
    context.fillText(new Date(time).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit" }), x(time), height - 10);
  });

  if (Number.isFinite(state.hoverTime) && state.hoverTime >= domain.start && state.hoverTime <= domain.end) {
    const cursorX = x(state.hoverTime);
    context.beginPath();
    context.moveTo(cursorX, margin.top);
    context.lineTo(cursorX, height - margin.bottom);
    context.strokeStyle = "#425f64";
    context.setLineDash([3, 3]);
    context.stroke();
    context.setLineDash([]);
    series.forEach((item) => {
      const row = nearestRow(item.rows, state.hoverTime);
      if (!row) return;
      context.beginPath();
      context.arc(x(Date.parse(row.timestamp)), y(getVariableValue(column, Number(row[column]))), 3.5, 0, Math.PI * 2);
      context.fillStyle = item.color;
      context.fill();
    });
  }
  if (state.dragRange) {
    const left = Math.max(margin.left, Math.min(x(state.dragRange.start), x(state.dragRange.current)));
    const right = Math.min(width - margin.right, Math.max(x(state.dragRange.start), x(state.dragRange.current)));
    context.fillStyle = "#087c7826";
    context.fillRect(left, margin.top, Math.max(0, right - left), chartHeight);
  }
}

function nearestRow(rows, time) {
  if (!rows.length) return null;
  let low = 0;
  let high = rows.length - 1;
  while (low < high) {
    const middle = Math.floor((low + high) / 2);
    if (Date.parse(rows[middle].timestamp) < time) low = middle + 1;
    else high = middle;
  }
  const after = rows[low];
  const before = rows[Math.max(0, low - 1)];
  return Math.abs(Date.parse(before.timestamp) - time) <= Math.abs(Date.parse(after.timestamp) - time)
    ? before
    : after;
}

function chartTimeFromPointer(event, canvas) {
  const domain = getCurrentDomain();
  if (!domain) return null;
  const rect = canvas.getBoundingClientRect();
  const plotLeft = 58;
  const plotRight = 14;
  const plotWidth = Math.max(1, rect.width - plotLeft - plotRight);
  const position = Math.max(0, Math.min(plotWidth, event.clientX - rect.left - plotLeft));
  return domain.start + (position / plotWidth) * (domain.end - domain.start);
}

function handleChartPointerDown(event) {
  if (event.button !== 0) return;
  const time = chartTimeFromPointer(event, event.currentTarget);
  if (!Number.isFinite(time)) return;
  state.dragRange = { start: time, current: time };
  event.currentTarget.setPointerCapture(event.pointerId);
  event.preventDefault();
}

function handleChartPointerMove(event) {
  const time = chartTimeFromPointer(event, event.currentTarget);
  if (!Number.isFinite(time)) return;
  state.hoverTime = time;
  if (state.dragRange) {
    state.dragRange.current = time;
    drawChart(event.currentTarget);
  } else if (state.drawFrame === null) {
    state.drawFrame = window.requestAnimationFrame(() => {
      state.drawFrame = null;
      drawAnalysisCanvases();
    });
  }
  renderCursorReadout(event.currentTarget.dataset.chart, time);
}

function handleChartPointerUp(event) {
  if (!state.dragRange) return;
  const drag = state.dragRange;
  state.dragRange = null;
  if (Math.abs(drag.current - drag.start) >= 60 * 1000) {
    const previous = getCurrentDomain();
    if (previous) state.zoomHistory.push(previous);
    state.zoomRange = {
      start: Math.min(drag.start, drag.current),
      end: Math.max(drag.start, drag.current),
    };
    state.tablePage = 0;
    renderAnalysis();
  } else {
    drawChart(event.currentTarget);
  }
}

function handleChartPointerLeave() {
  if (state.dragRange) return;
  state.hoverTime = null;
  byId("cursor-readout").textContent = "Hover over a chart to inspect values across runs. Drag within a chart to zoom all panels to that time range.";
  drawAnalysisCanvases();
}

function renderCursorReadout(column, time) {
  const label = getVariableLabel(column);
  const unit = getVariableUnit(column);
  const parts = selectedRunRecords().map(({ run, rows }) => {
    const row = nearestRow(visibleRows(rows, getCurrentDomain()), time);
    const val = row ? getVariableValue(column, Number(row[column])) : null;
    return `${run.scenario_id}: ${val !== null && Number.isFinite(val) ? formatNumber(val) : "—"} ${unit}`;
  });
  byId("cursor-readout").textContent = `${formatTime(time)} · ${label} · ${parts.join(" · ")}`;
}

function renderStatistics(records, variables, domain) {
  const selected = records.map(({ run, rows }) => ({
    run,
    rows: visibleRows(rows, domain),
  }));
  const reference = selected[0];
  const headers = `<tr><th>Variable</th><th>Scenario</th><th>Count</th><th>Min</th><th>Max</th><th>Mean</th><th>Median</th><th>Std dev</th><th>Mean Δ vs ${escapeHtml(reference.run.scenario_id)}</th></tr>`;
  const body = variables.flatMap((column) => selected.map(({ run, rows }) => {
    const values = rows.map((row) => getVariableValue(column, Number(row[column]))).filter(Number.isFinite);
    const sorted = [...values].sort((a, b) => a - b);
    const mean = values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : NaN;
    const median = sorted.length
      ? sorted.length % 2
        ? sorted[Math.floor(sorted.length / 2)]
        : (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
      : NaN;
    const deviation = values.length
      ? Math.sqrt(values.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / values.length)
      : NaN;
    const referenceValues = new Map((reference.rows || []).map((row) => [
      Date.parse(row.timestamp),
      getVariableValue(column, Number(row[column])),
    ]));
    const deltas = run.scenario_id === reference.run.scenario_id
      ? []
      : rows.map((row) => {
        const base = referenceValues.get(Date.parse(row.timestamp));
        const current = getVariableValue(column, Number(row[column]));
        return Number.isFinite(base) && Number.isFinite(current)
          ? current - base
          : NaN;
      }).filter(Number.isFinite);
    const deltaMean = deltas.length ? deltas.reduce((sum, value) => sum + value, 0) / deltas.length : NaN;
    return `<tr><td>${escapeHtml(getVariableLabel(column))} <small>${escapeHtml(getVariableUnit(column))}</small></td>
      <td>${escapeHtml(run.scenario_id)}</td><td>${values.length.toLocaleString()}</td>
      <td>${formatNumber(Math.min(...values))}</td><td>${formatNumber(Math.max(...values))}</td>
      <td>${formatNumber(mean)}</td><td>${formatNumber(median)}</td><td>${formatNumber(deviation)}</td>
      <td>${run.scenario_id === reference.run.scenario_id ? "Reference" : formatNumber(deltaMean)}</td></tr>`;
  })).join("");
  byId("analysis-statistics").innerHTML = `<table class="analysis-table"><thead>${headers}</thead><tbody>${body}</tbody></table>`;
}

function alignedRows(records, variables, domain) {
  const indexed = new Map();
  for (const { run, rows } of records) {
    for (const row of visibleRows(rows, domain)) {
      const time = Date.parse(row.timestamp);
      if (!Number.isFinite(time)) continue;
      if (!indexed.has(time)) indexed.set(time, { time, timestamp: row.timestamp, values: {} });
      const target = indexed.get(time);
      for (const column of variables) {
        target.values[`${run.scenario_id}::${column}`] = Number.isFinite(Number(row[column]))
          ? getVariableValue(column, Number(row[column]))
          : "";
      }
    }
  }
  return [...indexed.values()].sort((a, b) => a.time - b.time);
}

function renderAnalysisTable(records, variables, domain) {
  const rows = alignedRows(records, variables, domain);
  const columns = [
    { key: "timestamp", label: "Timestamp" },
    ...records.flatMap(({ run }) => variables.map((column) => ({
      key: `${run.scenario_id}::${column}`,
      label: `${run.scenario_id} · ${getVariableLabel(column)} (${getVariableUnit(column)})`,
    }))),
  ];
  const { key, direction } = state.tableSort;
  const sorted = [...rows].sort((left, right) => {
    let a = key === "timestamp" ? left.time : left.values[key];
    let b = key === "timestamp" ? right.time : right.values[key];
    if (typeof a === "string" || typeof b === "string") {
      a = String(a ?? "");
      b = String(b ?? "");
      return direction === "ascending" ? a.localeCompare(b) : b.localeCompare(a);
    }
    return direction === "ascending" ? (a - b) : (b - a);
  });
  const pageSize = Number(byId("table-page-size").value) || MAX_TABLE_ROWS;
  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize));
  state.tablePage = Math.min(state.tablePage, pageCount - 1);
  const pageRows = sorted.slice(state.tablePage * pageSize, (state.tablePage + 1) * pageSize);
  if (!rows.length) {
    byId("analysis-table").innerHTML = `<p class="muted">No hourly records in the selected time range.</p>`;
  } else {
    const head = columns.map((column) => `<th><button type="button" class="table-sort-button" data-sort-key="${escapeHtml(column.key)}" aria-label="Sort by ${escapeHtml(column.label)}">${escapeHtml(column.label)}${key === column.key ? (direction === "ascending" ? " ↑" : " ↓") : ""}</button></th>`).join("");
    const body = pageRows.map((row) => `<tr>${columns.map((column) => {
      const value = column.key === "timestamp"
        ? row.timestamp
        : row.values[column.key];
      return `<td>${column.key === "timestamp" ? escapeHtml(value) : (value === "" || value === undefined ? "—" : formatNumber(value))}</td>`;
    }).join("")}</tr>`).join("");
    byId("analysis-table").innerHTML = `<table class="analysis-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
    byId("analysis-table").querySelectorAll("[data-sort-key]").forEach((button) => {
      button.addEventListener("click", () => {
        const nextKey = button.dataset.sortKey;
        state.tableSort = {
          key: nextKey,
          direction: state.tableSort.key === nextKey && state.tableSort.direction === "ascending"
            ? "descending"
            : "ascending",
        };
        renderAnalysisTable(records, variables, domain);
      });
    });
  }
  byId("table-page-status").textContent = rows.length
    ? `Rows ${state.tablePage * pageSize + 1}–${Math.min((state.tablePage + 1) * pageSize, rows.length)} of ${rows.length.toLocaleString()}`
    : "No rows";
  byId("table-prev").disabled = state.tablePage <= 0;
  byId("table-next").disabled = state.tablePage >= pageCount - 1;
  byId("export-table").disabled = rows.length === 0;
  byId("export-table").dataset.available = rows.length ? "true" : "";
}

function renderParameterSnapshot(records) {
  const available = records.filter(({ run }) => run.input_parameters);
  if (!available.length) {
    byId("parameter-snapshot").innerHTML = `<p class="muted">No historical input snapshot is available for these runs. Snapshots are recorded for runs created after this feature was added.</p>`;
    return;
  }
  const allIds = [...new Set(available.flatMap(({ run }) => Object.keys(run.input_parameters || {})))].sort();
  const header = `<tr><th>Parameter</th>${records.map(({ run }) => `<th>${escapeHtml(run.scenario_id)}</th>`).join("")}</tr>`;
  const body = allIds.map((id) => `<tr><th>${escapeHtml(id)}</th>${records.map(({ run }) => {
    const item = run.input_parameters?.[id];
    if (!item) return `<td>${run.input_parameters ? "—" : "Snapshot unavailable"}</td>`;
    const source = [item.source_type, item.source_ref].filter(Boolean).join(" · ");
    return `<td>${escapeHtml(display(item.value))} ${escapeHtml(item.unit || "")}<small>${escapeHtml(source || "No provenance recorded")}</small></td>`;
  }).join("")}</tr>`).join("");
  byId("parameter-snapshot").innerHTML = `<table class="analysis-table"><thead>${header}</thead><tbody>${body}</tbody></table>`;
}

function applyZoomRange(start, end) {
  const full = getFullDomain();
  if (!full || !Number.isFinite(start) || !Number.isFinite(end) || end <= start) return;
  const boundedStart = Math.max(full.start, start);
  const boundedEnd = Math.min(full.end, end);
  if (boundedEnd <= boundedStart) return;
  const current = getCurrentDomain();
  if (current) state.zoomHistory.push(current);
  state.zoomRange = { start: boundedStart, end: boundedEnd };
  state.tablePage = 0;
  renderAnalysis();
}

function exportAnalysisTable() {
  const records = selectedRunRecords();
  const variables = state.selectedVariables;
  const domain = getCurrentDomain(records);
  if (!records.length || !variables.length || !domain) return;
  const rows = alignedRows(records, variables, domain);
  const columns = [
    { key: "timestamp", label: "timestamp" },
    ...records.flatMap(({ run }) => variables.map((column) => ({
      key: `${run.scenario_id}::${column}`,
      label: `${run.scenario_id} ${isTemperatureVariable(column) ? `${column.replace(/_K$/, "")}_${state.tempUnit}` : column}`,
    }))),
  ];
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const content = [
    columns.map((column) => quote(column.label)).join(","),
    ...rows.map((row) => columns.map((column) => quote(
      column.key === "timestamp" ? row.timestamp : row.values[column.key]
    )).join(",")),
  ].join("\r\n");
  const url = URL.createObjectURL(new Blob([content], { type: "text/csv;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "aquasolar-run-comparison.csv";
  anchor.click();
  URL.revokeObjectURL(url);
}

async function startRun() {
  const button = byId("start-run");
  button.disabled = true;
  byId("run-job-status").textContent = "Starting preflight…";
  try {
    const job = await request("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        scenario_id: byId("scenario-id").value.trim(),
        weather: byId("weather-select").value,
      }),
    });
    state.activeJob = job.id;
    byId("run-job-status").textContent = `Running scenario ${job.scenario_id}…`;
    pollRun(job.id);
  } catch (error) {
    byId("run-job-status").textContent = error.message;
    await refreshRunReadiness();
  }
}

function pollRun(jobId) {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const job = await request(`/api/runs/jobs/${encodeURIComponent(jobId)}`);
      if (job.state === "running") return;
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      state.activeJob = null;
      byId("run-job-status").textContent = job.state === "completed"
        ? `Scenario complete. ${job.stdout || ""}`
        : `Scenario failed. ${job.stderr || job.stdout || "No error details returned."}`;
      if (job.state === "completed" && job.scenario_id) {
        state.selectedRuns = [job.scenario_id, ...state.selectedRuns.filter((id) => id !== job.scenario_id)];
      }
      await refreshRuns();
      await refreshValidation();
      updateStagedState();
    } catch (error) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
      byId("run-job-status").textContent = `Could not read run status: ${error.message}`;
    }
  }, 900);
}

async function stageUpload(input) {
  const file = input.files?.[0];
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) {
    input.value = "";
    window.alert("Select a file no larger than 8 MiB.");
    return;
  }
  try {
    state.stagedFiles[input.dataset.uploadFile] = await file.text();
    state.previewToken = null;
    updateStagedState();
    openDataFile(state.selectedDataFile);
    byId("save-state").textContent = `Staged ${file.name} · validate before applying`;
  } catch (error) {
    window.alert(`Could not read ${file.name}: ${error.message}`);
  }
}

async function stageWeatherUpload(input, kind) {
  const file = input.files?.[0];
  if (!file) return;
  const status = byId("weather-upload-status");
  if (state.newWeatherPath) {
    delete state.stagedFiles[state.newWeatherPath.csv];
    delete state.stagedFiles[state.newWeatherPath.metadata];
    state.newWeatherPath = null;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    input.value = "";
    status.textContent = "Each weather file must be no larger than 8 MiB.";
    status.classList.add("error-message");
    updateStagedState();
    return;
  }
  try {
    state.weatherUpload[kind] = { name: file.name, contents: await file.text(), size: file.size };
  } catch (error) {
    status.textContent = `Could not read ${file.name}: ${error.message}`;
    status.classList.add("error-message");
    return;
  }
  const { csv, metadata } = state.weatherUpload;
  if (!csv || !metadata) {
    status.textContent = "Choose both files with the same base filename.";
    status.classList.remove("error-message");
    return;
  }
  const csvMatch = csv.name.match(/^([A-Za-z0-9][A-Za-z0-9._-]{0,99})\.csv$/);
  const metadataMatch = metadata.name.match(/^([A-Za-z0-9][A-Za-z0-9._-]{0,99})\.meta\.yaml$/);
  if (!csvMatch || !metadataMatch || csvMatch[1] !== metadataMatch[1]) {
    status.textContent = "Use matching safe filenames: name.csv and name.meta.yaml (letters, digits, dot, underscore, or hyphen).";
    status.classList.add("error-message");
    updateStagedState();
    return;
  }
  if (csv.size + metadata.size > MAX_UPLOAD_BYTES) {
    status.textContent = "The CSV and metadata pair must total no more than 8 MiB.";
    status.classList.add("error-message");
    updateStagedState();
    return;
  }
  const csvPath = `inputs/timeseries/${csv.name}`;
  const metadataPath = `inputs/timeseries/${metadata.name}`;
  const knownFile = state.catalog.data_files.some((item) =>
    item.file === csvPath || item.metadata_file === metadataPath
  );
  const knownWeather = state.weather.some((item) => item.file === csvPath);
  if (knownFile || knownWeather) {
    status.textContent = "That weather filename already exists. Choose a unique dataset name to avoid replacing it.";
    status.classList.add("error-message");
    updateStagedState();
    return;
  }
  state.stagedFiles[csvPath] = csv.contents;
  state.stagedFiles[metadataPath] = metadata.contents;
  state.newWeatherPath = { file: csvPath, csv: csvPath, metadata: metadataPath };
  state.previewToken = null;
  status.textContent = `${csv.name} and ${metadata.name} staged. Use Preview & apply changes to validate and save the pair.`;
  status.classList.remove("error-message");
  byId("save-state").textContent = `Staged weather pair · validate before applying`;
  updateStagedState();
}

function showConfirmation() {
  if (!stagedCount()) return;
  const dialog = byId("confirm-dialog");
  byId("confirm-copy").textContent = `Checking ${Object.keys(state.stagedParameters).length} parameter, ${Object.keys(state.stagedFiles).length} file, and ${Object.keys(state.stagedModules).length} module change(s). Nothing is written until you confirm the preview.`;
  byId("confirm-apply").textContent = "Preview staged changes";
  dialog.dataset.stage = "preview";
  dialog.showModal();
}

async function handleApplyConfirmation(event) {
  event.preventDefault();
  const dialog = byId("confirm-dialog");
  const button = byId("confirm-apply");
  button.disabled = true;
  try {
    if (dialog.dataset.stage === "preview") {
      await previewStaged();
      const errors = state.report.error_count;
      const warnings = state.report.warning_count;
      byId("confirm-copy").textContent = `${errors} blocking error(s), ${warnings} warning(s) in the preview. Existing issues will remain visible and will block running. Review the report before saving these staged source files.`;
      button.textContent = "Apply staged files";
      dialog.dataset.stage = "apply";
    } else {
      await applyStaged();
      byId("confirm-copy").textContent = "Changes saved. The project validation report has been refreshed.";
      dialog.dataset.stage = "done";
      button.textContent = "Close";
    }
    if (dialog.dataset.stage === "done") dialog.close();
  } catch (error) {
    byId("confirm-copy").textContent = `Changes were not applied: ${error.message}`;
    button.textContent = "Retry";
    dialog.dataset.stage = "apply";
  } finally {
    button.disabled = false;
  }
}

function wireEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.view));
  });
  document.querySelectorAll("[data-go]").forEach((button) => {
    button.addEventListener("click", () => showView(button.dataset.go));
  });
  document.querySelectorAll("[data-model-tab]").forEach((button) => {
    button.addEventListener("click", () => setModelTab(button.dataset.modelTab));
  });
  byId("module-list").addEventListener("change", (event) => {
    if (event.target.matches("[data-module-toggle]")) stageModuleToggle(event.target);
  });
  byId("trace-graph").addEventListener("click", (event) => {
    const node = event.target.closest("[data-trace-node]");
    if (!node) return;
    state.selectedTraceNode = node.dataset.traceNode;
    renderTraceGraph();
  });
  byId("trace-run-select").addEventListener("change", (event) => {
    state.selectedTraceRunId = event.target.value;
    renderTraceRunSnapshot();
  });
  parameterList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-parameter-id]");
    if (button) openParameter(button.dataset.parameterId);
  });
  dataList.addEventListener("click", (event) => {
    const button = event.target.closest("[data-data-file]");
    if (button) openDataFile(button.dataset.dataFile);
  });
  byId("parameter-detail").addEventListener("input", (event) => {
    if (event.target.matches("[data-param-field]")) stageParameterInput(event.target);
  });
  byId("parameter-detail").addEventListener("change", (event) => {
    if (event.target.matches("[data-param-field]")) stageParameterInput(event.target);
  });
  byId("data-detail").addEventListener("change", (event) => {
    if (event.target.matches("[data-upload-file]")) stageUpload(event.target);
  });
  byId("weather-csv-upload").addEventListener("change", (event) => {
    stageWeatherUpload(event.target, "csv");
  });
  byId("weather-meta-upload").addEventListener("change", (event) => {
    stageWeatherUpload(event.target, "metadata");
  });
  byId("parameter-detail").addEventListener("click", async (event) => {
    const convertBtn = event.target.closest("#convert-param-temp");
    if (convertBtn) {
      const nextUnit = convertBtn.dataset.to;
      const nextVal = Number(convertBtn.dataset.val);
      const row = state.catalog.parameters.find((item) => item.id === state.selectedParameter);
      if (row) {
        const changes = state.stagedParameters[row.id] || {};
        changes["value"] = nextVal;
        changes["unit"] = nextUnit;
        state.stagedParameters[row.id] = changes;
        state.previewToken = null;
        renderParameterList();
        openParameter(row.id);
        updateStagedState();
      }
      return;
    }
    if (event.target.id === "revert-parameter") {
      delete state.stagedParameters[state.selectedParameter];
      state.previewToken = null;
      renderParameterList();
      openParameter(state.selectedParameter);
      updateStagedState();
    }
    if (event.target.id === "validate-parameter") {
      try {
        await previewStaged();
        showView("validation");
      } catch (error) {
        window.alert(`Validation failed: ${error.message}`);
      }
    }
  });
  byId("parameter-search").addEventListener("input", renderParameterList);
  byId("parameter-status-filter").addEventListener("change", renderParameterList);
  byId("parameter-group-filter").addEventListener("change", renderParameterList);
  byId("data-search").addEventListener("input", renderDataList);
  byId("data-kind-filter").addEventListener("change", renderDataList);
  byId("finding-search").addEventListener("input", renderValidation);
  byId("severity-filter").addEventListener("change", renderValidation);
  byId("finding-category-filter").addEventListener("change", renderValidation);
  byId("validate-now").addEventListener("click", refreshValidation);
  byId("refresh-validation").addEventListener("click", refreshValidation);
  byId("weather-select").addEventListener("change", updateWeatherOption);
  byId("start-run").addEventListener("click", startRun);
  byId("refresh-runs").addEventListener("click", refreshRuns);
  byId("run-picker").addEventListener("change", (event) => {
    if (!event.target.matches("[data-run-id]")) return;
    state.selectedRuns = [...byId("run-picker").querySelectorAll("[data-run-id]:checked")]
      .map((input) => input.dataset.runId);
    state.tablePage = 0;
    renderRunPicker();
    loadSelectedRuns();
  });
  byId("variable-picker").addEventListener("change", (event) => {
    if (!event.target.matches("[data-variable]")) return;
    state.selectedVariables = [...byId("variable-picker").querySelectorAll("[data-variable]:checked")]
      .map((input) => input.dataset.variable);
    state.tablePage = 0;
    renderAnalysis();
  });
  byId("range-start").addEventListener("input", updateRangeApplyButton);
  byId("range-end").addEventListener("input", updateRangeApplyButton);
  byId("apply-range").addEventListener("click", () => {
    const start = Date.parse(byId("range-start").value);
    const end = Date.parse(byId("range-end").value);
    if (Number.isFinite(start) && Number.isFinite(end)) applyZoomRange(start, end);
  });
  byId("zoom-out").addEventListener("click", () => {
    state.zoomRange = state.zoomHistory.pop() || null;
    state.tablePage = 0;
    renderAnalysis();
  });
  byId("reset-zoom").addEventListener("click", () => {
    state.zoomRange = null;
    state.zoomHistory = [];
    state.tablePage = 0;
    renderAnalysis();
  });
  byId("table-page-size").addEventListener("change", () => {
    state.tablePage = 0;
    renderAnalysis();
  });
  byId("table-prev").addEventListener("click", () => {
    state.tablePage = Math.max(0, state.tablePage - 1);
    renderAnalysis();
  });
  byId("table-next").addEventListener("click", () => {
    state.tablePage += 1;
    renderAnalysis();
  });
  byId("export-table").addEventListener("click", exportAnalysisTable);
  byId("apply-staged").addEventListener("click", showConfirmation);
  byId("confirm-apply").addEventListener("click", handleApplyConfirmation);
  byId("global-search").addEventListener("input", renderGlobalSearch);
  byId("global-search").addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      byId("global-results").hidden = true;
      byId("global-search").setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("click", (event) => {
    const unitBtn = event.target.closest(".temp-unit-btn");
    if (unitBtn && unitBtn.dataset.tempUnit) {
      setTemperatureUnit(unitBtn.dataset.tempUnit);
      return;
    }
    if (!event.target.closest(".search-shell")) {
      byId("global-results").hidden = true;
      byId("global-search").setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      byId("global-search").focus();
    }
  });
  window.addEventListener("popstate", () => {
    const name = window.location.hash.slice(1);
    showView(VIEW_NAMES.has(name) ? name : "overview", { updateHistory: false });
  });
  window.addEventListener("resize", drawAnalysisCanvases);
}

function updateRangeApplyButton() {
  const start = Date.parse(byId("range-start").value);
  const end = Date.parse(byId("range-end").value);
  const full = getFullDomain();
  byId("apply-range").disabled = !full
    || !Number.isFinite(start)
    || !Number.isFinite(end)
    || end <= start;
}

async function initialize() {
  wireEvents();
  updateTempUnitButtons();
  try {
    const config = await request("/api/config");
    state.readOnly = config.read_only === true;
    if (state.readOnly) {
      document.body.classList.add("read-only");
      byId("project-mode").textContent = "Public read-only showcase";
      byId("overview-title").textContent = "Project overview";
      byId("overview-intro").textContent = "Explore this project's registered inputs, validation findings, and PVT model scope.";
      byId("parameters-intro").textContent = "Search and review registered parameter values, requirements, and provenance.";
      byId("data-intro").textContent = "Inspect registered tables and time series, including metadata, sample rows, and validation findings.";
      byId("runs-intro").textContent = "Review saved PVT-only outputs. This public showcase does not run new scenarios.";
      byId("readonly-run-note").textContent = "Read-only public demo: input editing and new simulation runs are disabled. Only results already included with the project are available.";
      byId("readonly-run-note").hidden = false;
      byId("footer-mode").textContent = "AquaSolar · public read-only showcase";
      byId("save-state").textContent = "Edits and new runs are disabled";
      byId("parameter-detail").querySelector(".empty-state p").textContent = "Select a parameter to review its definition, requirement, and provenance.";
    }
    state.catalog = await request("/api/catalog");
    byId("nav-parameter-count").textContent = state.catalog.parameters.length;
    byId("nav-data-count").textContent = state.catalog.data_files.length;
    renderParameterGroups();
    renderParameterList();
    renderDataList();
    if (state.catalog.catalog_errors?.length) {
      byId("next-action-copy").textContent = state.catalog.catalog_errors.map((item) => `${item.file}: ${item.error}`).join("; ");
    }
    await Promise.all([refreshValidation(), loadWeather(), refreshRuns(), loadModel()]);
    byId("summary-inputs").textContent = state.catalog.parameters.length + state.catalog.data_files.length;
  } catch (error) {
    setGlobalError(error.message);
  } finally {
    const initialView = window.location.hash.slice(1);
    if (VIEW_NAMES.has(initialView)) {
      showView(initialView, { updateHistory: false, focusHeading: false });
    }
  }
}

initialize();
