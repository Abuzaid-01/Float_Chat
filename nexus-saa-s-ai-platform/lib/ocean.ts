/**
 * Oceanographic constants and formatting shared by the Observatory UI.
 */

export type GeoBounds = { lonMin: number; lonMax: number; latMin: number; latMax: number };

export type OceanRegion = GeoBounds & { name: string };

/**
 * The six Indian Ocean regions the backend classifies measurements into.
 * Mirrors REGION_BOUNDS in data_processing/regions.py — keep the two in sync.
 */
export const OCEAN_REGIONS: OceanRegion[] = [
  { name: "Red Sea", latMin: 12, latMax: 30, lonMin: 32, lonMax: 44 },
  { name: "Andaman Sea", latMin: 5, latMax: 20, lonMin: 92, lonMax: 100 },
  { name: "Arabian Sea", latMin: 5, latMax: 30, lonMin: 40, lonMax: 80 },
  { name: "Bay of Bengal", latMin: 5, latMax: 25, lonMin: 80, lonMax: 100 },
  { name: "Equatorial Indian Ocean", latMin: -10, latMax: 5, lonMin: 40, lonMax: 100 },
  { name: "Southern Indian Ocean", latMin: -50, latMax: -10, lonMin: 20, lonMax: 120 },
];

export const INDIAN_OCEAN_VIEW: GeoBounds = { lonMin: 16, lonMax: 126, latMin: -56, latMax: 36 };
export const WORLD_VIEW: GeoBounds = { lonMin: -180, lonMax: 180, latMin: -78, latMax: 84 };

export function insideBounds(lat: number, lon: number, bounds: GeoBounds) {
  return lat >= bounds.latMin && lat <= bounds.latMax && lon >= bounds.lonMin && lon <= bounds.lonMax;
}

/** ARGO floats profile the top 2,000 m; the page maps its scroll onto that dive. */
export const MAX_DEPTH_M = 2000;

export const DEPTH_ZONES = [
  { name: "Sunlight zone", science: "Epipelagic", from: 0, to: 200 },
  { name: "Twilight zone", science: "Mesopelagic", from: 200, to: 1000 },
  { name: "Midnight zone", science: "Bathypelagic", from: 1000, to: 2000 },
] as const;

export function zoneAtDepth(depth: number) {
  return DEPTH_ZONES.find((zone) => depth < zone.to) ?? DEPTH_ZONES[DEPTH_ZONES.length - 1];
}

/**
 * A representative tropical temperature profile (°C by depth in metres):
 * warm mixed layer, sharp thermocline, slow decline below. Used only for the
 * illustrative float-cycle animation — never presented as measured data.
 */
export function typicalTemperature(depth: number) {
  const mixedLayer = 28.6;
  const deep = 2.6;
  const thermocline = 1 / (1 + Math.exp((depth - 130) / 45));
  const slowDecay = Math.exp(-depth / 620);
  return deep + (mixedLayer - deep) * (0.62 * thermocline + 0.38 * slowDecay);
}

const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 2 });
const grouped = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });

export function formatCount(value: number | null | undefined, compactFrom = 100_000) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return Math.abs(value) >= compactFrom ? compact.format(value) : grouped.format(value);
}

export function formatCoordinate(lat: number, lon: number) {
  const ns = lat >= 0 ? "N" : "S";
  const ew = lon >= 0 ? "E" : "W";
  return `${Math.abs(lat).toFixed(2)}°${ns}, ${Math.abs(lon).toFixed(2)}°${ew}`;
}

const dayMonth = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const dayMonthYear = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

/** The API sends naive UTC timestamps ("2025-10-19T00:53:20"). */
export function parseTimestamp(value: unknown): Date | null {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(value)) return null;
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return new Date(`${value}T00:00:00Z`);
  const iso = value.includes("T") ? value : value.replace(" ", "T");
  const date = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatDate(value: unknown) {
  const date = parseTimestamp(value);
  return date ? dayMonthYear.format(date) : "—";
}

export function formatDateRange(from: unknown, to: unknown) {
  const start = parseTimestamp(from);
  const end = parseTimestamp(to);
  if (!start || !end) return null;
  const sameYear = start.getUTCFullYear() === end.getUTCFullYear();
  return `${(sameYear ? dayMonth : dayMonthYear).format(start)} – ${dayMonthYear.format(end)}`;
}
