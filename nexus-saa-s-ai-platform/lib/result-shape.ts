/**
 * Works out what a `/api/v1/chat` result table contains so the UI can pick a
 * fitting view: a depth profile, a category comparison, a single row of
 * figures, a time series — or just the table.
 */

import type { DataRow } from "@/lib/api";
import { parseTimestamp } from "@/lib/ocean";

export type Measure = { key: string; label: string; unit: string };

/** Physical measurements in argo_profiles (database/models.py). */
const KNOWN_MEASURES: Measure[] = [
  { key: "temperature", label: "Temperature", unit: "°C" },
  { key: "salinity", label: "Salinity", unit: "PSU" },
  { key: "dissolved_oxygen", label: "Dissolved oxygen", unit: "µmol/kg" },
  { key: "chlorophyll", label: "Chlorophyll", unit: "mg/m³" },
  { key: "ph", label: "pH", unit: "" },
];

/** Numeric-looking columns that identify things rather than measure them. */
const IDENTIFIER_COLUMNS = new Set([
  "id",
  "float_id",
  "cycle_number",
  "temp_qc",
  "sal_qc",
  "data_mode",
  "platform_type",
]);

const POSITION_COLUMNS = new Set(["latitude", "longitude"]);

export type ResultKind = "profile" | "category" | "figures" | "series" | "table";

/** Columns that give depth: raw pressure, or the start of a depth bin. */
const DEPTH_COLUMNS = ["pressure", "depth_bin"];

export type ResultShape = {
  kind: ResultKind;
  columns: string[];
  /** The column plotted on the depth axis, when there is one. */
  depthColumn: string | null;
  /** Measurements that can be plotted against depth (profile kind). */
  profileMeasures: Measure[];
  /** Numeric columns worth comparing (category / series kinds). */
  valueColumns: string[];
  categoryColumn: string | null;
  timeColumn: string | null;
  hasPositions: boolean;
  hasRegions: boolean;
};

export function toNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function humanize(column: string) {
  const known = KNOWN_MEASURES.find((measure) => measure.key === column);
  if (known) return known.label;
  const text = column.replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function unitFor(column: string) {
  if (column === "pressure") return "dbar";
  const known = KNOWN_MEASURES.find((measure) => column === measure.key || column.endsWith(`_${measure.key}`));
  return known?.unit ?? "";
}

function isNumericColumn(rows: DataRow[], column: string) {
  let seen = 0;
  for (const row of rows) {
    const value = row[column];
    if (value === null || value === undefined || value === "") continue;
    if (toNumber(value) === null) return false;
    seen += 1;
  }
  return seen > 0;
}

export function analyzeRows(rows: DataRow[]): ResultShape {
  const columns = rows.length ? Object.keys(rows[0]) : [];
  const numeric = columns.filter((column) => isNumericColumn(rows, column));
  const valueColumns = numeric.filter(
    (column) => !IDENTIFIER_COLUMNS.has(column) && !POSITION_COLUMNS.has(column),
  );
  const depthColumn = DEPTH_COLUMNS.find((column) => numeric.includes(column)) ?? null;
  // Depth-binned results carry averages ("average_temperature") instead of raw values.
  const binned: Measure[] = valueColumns
    .filter((column) => column.startsWith("average_"))
    .map((column) => ({ key: column, label: humanize(column), unit: unitFor(column) }));
  const profileMeasures =
    depthColumn === "depth_bin" ? binned : KNOWN_MEASURES.filter((measure) => valueColumns.includes(measure.key));
  const hasPressure = depthColumn !== null;
  const hasPositions = numeric.includes("latitude") && numeric.includes("longitude");
  const hasRegions = columns.includes("ocean_region");
  const timeColumn =
    columns.find((column) => rows.some((row) => parseTimestamp(row[column]) !== null) && !numeric.includes(column)) ??
    null;

  // A category column labels each row uniquely (e.g. one row per ocean region).
  const categoryColumn =
    columns.find((column) => {
      if (numeric.includes(column) || column === timeColumn) return false;
      const labels = new Set(rows.map((row) => String(row[column] ?? "")));
      return labels.size === rows.length && rows.length >= 2 && rows.length <= 24;
    }) ?? null;

  let kind: ResultKind = "table";
  if (hasPressure && profileMeasures.length > 0 && rows.length >= 3) kind = "profile";
  else if (rows.length === 1 && columns.length > 0) kind = "figures";
  else if (categoryColumn && valueColumns.length > 0) kind = "category";
  // Rows that are positions (a trajectory, a list of floats) belong on the map, not a line chart.
  else if (timeColumn && !hasPositions && valueColumns.some((column) => column !== "pressure") && rows.length >= 3)
    kind = "series";

  return {
    kind,
    columns,
    depthColumn,
    profileMeasures,
    valueColumns: kind === "series" ? valueColumns.filter((column) => column !== "pressure") : valueColumns,
    categoryColumn,
    timeColumn,
    hasPositions,
    hasRegions,
  };
}

export type DepthProfile = {
  id: string;
  label: string;
  /** Sorted shallow → deep. */
  points: Array<{ depth: number; value: number }>;
};

/** Split rows into one profile per float cycle and keep the measure's valid points. */
export function buildProfiles(rows: DataRow[], measure: string, depthColumn = "pressure"): DepthProfile[] {
  const groups = new Map<string, DepthProfile>();
  for (const row of rows) {
    const depth = toNumber(row[depthColumn]);
    const value = toNumber(row[measure]);
    if (depth === null || value === null) continue;
    const float = row.float_id ?? null;
    const cycle = row.cycle_number ?? null;
    const fallback = `${row.latitude ?? ""},${row.longitude ?? ""},${row.timestamp ?? ""}`;
    const id = float !== null ? `${float}#${cycle ?? ""}` : fallback;
    let profile = groups.get(id);
    if (!profile) {
      const label =
        float !== null
          ? `Float ${float}${cycle !== null ? ` · cycle ${cycle}` : ""}`
          : depthColumn === "depth_bin"
            ? "Mean of all matching measurements"
            : `Profile ${groups.size + 1}`;
      profile = { id, label, points: [] };
      groups.set(id, profile);
    }
    profile.points.push({ depth, value });
  }
  return [...groups.values()]
    .filter((profile) => profile.points.length >= 2)
    .map((profile) => ({ ...profile, points: profile.points.sort((a, b) => a.depth - b.depth) }));
}

export type MapPoint = { lat: number; lon: number; label: string; count: number };

/** Collapse rows to their distinct positions (many depth samples share one). */
export function buildPositions(rows: DataRow[]): MapPoint[] {
  const positions = new Map<string, MapPoint>();
  for (const row of rows) {
    const lat = toNumber(row.latitude);
    const lon = toNumber(row.longitude);
    if (lat === null || lon === null) continue;
    const key = `${lat.toFixed(2)},${lon.toFixed(2)}`;
    const existing = positions.get(key);
    if (existing) existing.count += 1;
    else {
      positions.set(key, {
        lat,
        lon,
        label:
          row.float_id !== undefined && row.float_id !== null
            ? `Float ${row.float_id}${row.cycle_number !== undefined && row.cycle_number !== null ? ` · cycle ${row.cycle_number}` : ""}`
            : "Observation",
        count: 1,
      });
    }
  }
  return [...positions.values()];
}

/** Round an axis range outward to tidy tick values. */
export function niceTicks(min: number, max: number, target = 5): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [];
  if (min === max) {
    const pad = Math.abs(min) > 0 ? Math.abs(min) * 0.1 : 1;
    min -= pad;
    max += pad;
  }
  const rawStep = (max - min) / target;
  const magnitude = 10 ** Math.floor(Math.log10(rawStep));
  const residual = rawStep / magnitude;
  const step = (residual >= 5 ? 10 : residual >= 2 ? 5 : residual >= 1 ? 2 : 1) * magnitude;
  const start = Math.floor(min / step) * step;
  const end = Math.ceil(max / step) * step;
  const ticks: number[] = [];
  for (let tick = start; tick <= end + step / 2; tick += step) ticks.push(Number(tick.toPrecision(12)));
  return ticks;
}

export function formatValue(value: unknown, digits = 3): string {
  if (value === null || value === undefined || value === "") return "—";
  const numeric = typeof value === "number" ? value : null;
  if (numeric !== null) {
    if (Number.isInteger(numeric)) return numeric.toLocaleString("en-US");
    return numeric.toLocaleString("en-US", { maximumFractionDigits: digits });
  }
  return String(value);
}
