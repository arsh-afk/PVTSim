const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const sourcePath = path.join(__dirname, "../../src/aquasolar/static/analytics-core.js");
vm.runInThisContext(readFileSync(sourcePath, "utf8"), { filename: sourcePath });

const analytics = globalThis.AquaSolarAnalytics;

test("groups graph variables by displayed unit", () => {
  const groups = analytics.groupVariablesByUnit([
    { column: "GHI_W_m2", unit: "W/m²" },
    { column: "POA_W_m2", unit: "W/m²" },
    { column: "P_el_W", unit: "W" },
  ]);
  assert.deepEqual(groups, [
    { unit: "W/m²", variables: ["GHI_W_m2", "POA_W_m2"] },
    { unit: "W", variables: ["P_el_W"] },
  ]);
  assert.deepEqual(analytics.valueBounds([120, 250, 300, 600]), { min: 120, max: 600 });
});

test("uses a half-open energy window and includes the final full-run interval", () => {
  const rows = [
    { timestamp: "2025-01-01T10:00:00Z", E_el_Wh: 1000, E_heat_Wh: 2000 },
    { timestamp: "2025-01-01T11:00:00Z", E_el_Wh: 1500, E_heat_Wh: 2500 },
    { timestamp: "2025-01-01T12:00:00Z", E_el_Wh: 2000, E_heat_Wh: 3000 },
  ];
  const record = { run: { weather_interval_seconds: 3600 }, rows };
  const domain = analytics.fullDomain([record]);

  assert.deepEqual(domain, {
    start: Date.parse("2025-01-01T10:00:00Z"),
    end: Date.parse("2025-01-01T13:00:00Z"),
  });
  assert.deepEqual(
    analytics.sumEnergyWindow(rows, Date.parse("2025-01-01T10:00:00Z"), Date.parse("2025-01-01T11:00:00Z")),
    { electricKWh: 1, heatKWh: 2, electricSteps: 1, heatSteps: 1, intervalCount: 1 },
  );
  assert.deepEqual(
    analytics.sumEnergyWindow(rows, domain.start, domain.end),
    { electricKWh: 4.5, heatKWh: 7.5, electricSteps: 3, heatSteps: 3, intervalCount: 3 },
  );
});

test("calculates descriptive distribution statistics and leaves zero-mean CV undefined", () => {
  const summary = analytics.summarizeValues([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  assert.equal(summary.count, 10);
  assert.equal(summary.mean, 5.5);
  assert.equal(summary.median, 5.5);
  assert.equal(summary.q1, 3.25);
  assert.equal(summary.q3, 7.75);
  assert.equal(summary.iqr, 4.5);
  assert.ok(Math.abs(summary.p5 - 1.45) < 1e-12);
  assert.ok(Math.abs(summary.p95 - 9.55) < 1e-12);
  assert.ok(summary.coefficientOfVariation > 52 && summary.coefficientOfVariation < 53);
  assert.equal(analytics.summarizeValues([0, 0]).coefficientOfVariation, null);
  assert.equal(analytics.summarizeValues([]).count, 0);
});
