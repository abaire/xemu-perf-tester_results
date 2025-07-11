import { XemuVersion } from "./xemu_version.js";

function expandTrendEnum(val) {
  // Keep in sync with renderer.py
  switch (val) {
    case "W":
      return "Worsening";
    case "N":
      // Insufficient data to detect trending.
      return "";
    case "S":
      return "Stable";
    case "I":
      return "Improving";
  }
}

export function expandData(rawData) {
  return rawData.map((d) => {
    const version_obj = new XemuVersion(d.xemu_version_obj);
    return {
      ...d,
      xemu_version_obj: version_obj,
      xemu_short_version: version_obj.toString(),
      trend: expandTrendEnum(d.trend),
    };
  });
}

export function processData(rawData, excludeMaxOutlier) {
  return rawData.map((d) => {
    let average_us = d.average_us;
    let max_us = d.max_us;
    const min_us = d.min_us;

    if (excludeMaxOutlier) {
      average_us = d.average_us_exmax;
      max_us = d.inner_max_us;
    }

    let error_plus_us;
    let error_minus_us;
    let adjusted_max_ms;
    let adjusted_min_ms;
    if (Number.isNaN(max_us) || Number.isNaN(min_us)) {
      error_plus_us = 0;
      error_minus_us = 0;
      adjusted_max_ms = NaN;
      adjusted_min_ms = NaN;
    } else {
      error_plus_us = max_us - average_us;
      error_minus_us = average_us - min_us;
      adjusted_max_ms = max_us / 1000.0;
      adjusted_min_ms = min_us / 1000.0;
    }

    return {
      ...d,
      average_us: average_us,
      average_ms: average_us / 1000.0,
      error_plus_us: error_plus_us,
      error_minus_us: error_minus_us,
      error_plus_ms: error_plus_us / 1000.0,
      error_minus_ms: error_minus_us / 1000.0,
      adjusted_max_ms: adjusted_max_ms,
      adjusted_min_ms: adjusted_min_ms,
    };
  });
}

export function augmentMinMax(data) {
  const machines = data.reduce((acc, d) => {
    const arr = acc[d.machine_id] || [];
    arr.push(d);
    acc[d.machine_id] = arr;
    return acc;
  }, {});

  for (const machineId in machines) {
    const machineData = machines[machineId];
    if (machineData.length < 2) continue;

    const minPoint = machineData.reduce((min, p) =>
      p.average_ms < min.average_ms ? p : min,
    );
    const maxPoint = machineData.reduce((max, p) =>
      p.average_ms > max.average_ms ? p : max,
    );

    minPoint.isMin = true;
    maxPoint.isMax = true;
  }
}
