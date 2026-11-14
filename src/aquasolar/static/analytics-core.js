(function attachAnalyticsCore(root) {
  const DEFAULT_INTERVAL_MS = 60 * 60 * 1000;

  function groupVariablesByUnit(items) {
    const groups = new Map();
    for (const item of items) {
      if (!groups.has(item.unit)) groups.set(item.unit, []);
      groups.get(item.unit).push(item.column);
    }
    return [...groups].map(([unit, variables]) => ({ unit, variables }));
  }

  function intervalMilliseconds(record) {
    const declared = Number(record.run?.weather_interval_seconds);
    if (Number.isFinite(declared) && declared > 0) return declared * 1000;

    const rows = record.rows || [];
    for (let index = 1; index < rows.length; index += 1) {
      const previous = Date.parse(rows[index - 1].timestamp);
      const current = Date.parse(rows[index].timestamp);
      if (Number.isFinite(previous) && Number.isFinite(current) && current > previous) {
        return current - previous;
      }
    }
    return DEFAULT_INTERVAL_MS;
  }

  function fullDomain(records) {
    let start = Infinity;
    let end = -Infinity;
    for (const record of records) {
      let first = Infinity;
      let last = -Infinity;
      for (const row of record.rows || []) {
        const time = Date.parse(row.timestamp);
        if (!Number.isFinite(time)) continue;
        first = Math.min(first, time);
        last = Math.max(last, time);
      }
      if (!Number.isFinite(first)) continue;
      start = Math.min(start, first);
      end = Math.max(end, last + intervalMilliseconds(record));
    }
    return Number.isFinite(start) && Number.isFinite(end) && end > start
      ? { start, end }
      : null;
  }

  function rowsInWindow(rows, start, end) {
    return rows.filter((row) => {
      const time = Date.parse(row.timestamp);
      return Number.isFinite(time) && time >= start && time < end;
    });
  }

  function finiteValue(value) {
    if (value === null || value === undefined || value === "") return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  }

  function valueBounds(values) {
    let min = Infinity;
    let max = -Infinity;
    for (const value of values) {
      if (!Number.isFinite(value)) continue;
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
    return Number.isFinite(min) ? { min, max } : null;
  }

  function sumEnergyWindow(rows, start, end) {
    let electricWh = 0;
    let heatWh = 0;
    let electricSteps = 0;
    let heatSteps = 0;
    let intervalCount = 0;

    for (const row of rowsInWindow(rows, start, end)) {
      intervalCount += 1;
      const electric = finiteValue(row.E_el_Wh);
      const heat = finiteValue(row.E_heat_Wh);
      if (electric !== null) {
        electricWh += electric;
        electricSteps += 1;
      }
      if (heat !== null) {
        heatWh += heat;
        heatSteps += 1;
      }
    }
    return {
      electricKWh: electricSteps ? electricWh / 1000 : null,
      heatKWh: heatSteps ? heatWh / 1000 : null,
      electricSteps,
      heatSteps,
      intervalCount,
    };
  }

  function quantile(sorted, probability) {
    if (!sorted.length) return null;
    const position = (sorted.length - 1) * probability;
    const lower = Math.floor(position);
    const upper = Math.ceil(position);
    const fraction = position - lower;
    return sorted[lower] + (sorted[upper] - sorted[lower]) * fraction;
  }

  function summarizeValues(values) {
    const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
    if (!sorted.length) {
      return {
        count: 0,
        min: null,
        max: null,
        mean: null,
        median: null,
        standardDeviation: null,
        q1: null,
        q3: null,
        iqr: null,
        p5: null,
        p95: null,
        coefficientOfVariation: null,
      };
    }

    const mean = sorted.reduce((sum, value) => sum + value, 0) / sorted.length;
    const variance = sorted.reduce((sum, value) => sum + ((value - mean) ** 2), 0) / sorted.length;
    const standardDeviation = Math.sqrt(variance);
    const q1 = quantile(sorted, 0.25);
    const q3 = quantile(sorted, 0.75);
    const nearZeroMean = Math.abs(mean) <= 1e-12;

    return {
      count: sorted.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      mean,
      median: quantile(sorted, 0.5),
      standardDeviation,
      q1,
      q3,
      iqr: q3 - q1,
      p5: quantile(sorted, 0.05),
      p95: quantile(sorted, 0.95),
      coefficientOfVariation: nearZeroMean ? null : (standardDeviation / Math.abs(mean)) * 100,
    };
  }

  root.AquaSolarAnalytics = Object.freeze({
    fullDomain,
    groupVariablesByUnit,
    intervalMilliseconds,
    rowsInWindow,
    sumEnergyWindow,
    summarizeValues,
    valueBounds,
  });
})(globalThis);
