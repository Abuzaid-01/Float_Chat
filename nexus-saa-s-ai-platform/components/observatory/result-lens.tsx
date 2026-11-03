"use client";

import { useMemo, useState } from "react";
import { BarChart3, Check, Clipboard, Code2, Download, MapPinned, ScanSearch, Table2 } from "lucide-react";
import type { ChatResponse, DataRow, ProfileAnalysis } from "@/lib/api";
import { GeoBounds, OCEAN_REGIONS, formatCount } from "@/lib/ocean";
import { MapPoint, analyzeRows, buildPositions, formatValue, humanize } from "@/lib/result-shape";
import { MapRegion, OceanMap } from "./ocean-map";
import { DepthMarker, ResultChart } from "./result-charts";

type View = "chart" | "map" | "table" | "sql";

const MAP_ASPECT = 2;
const MAX_MAP_POINTS = 400;
const TABLE_PAGE = 50;

/** Frame an area with some sea room around it, at the map panel's aspect ratio. */
function fitView(area: GeoBounds): GeoBounds {
  const latMid = (area.latMin + area.latMax) / 2;
  const lonMid = (area.lonMin + area.lonMax) / 2;
  let lonSpan = Math.max(10, (area.lonMax - area.lonMin) * 1.8);
  let latSpan = Math.max(lonSpan / MAP_ASPECT, (area.latMax - area.latMin) * 1.5);
  lonSpan = Math.min(360, Math.max(lonSpan, latSpan * MAP_ASPECT));
  latSpan = lonSpan / MAP_ASPECT;

  const lonMin = Math.min(Math.max(lonMid - lonSpan / 2, -180), 180 - lonSpan);
  const latMin = Math.min(Math.max(latMid - latSpan / 2, -90), 90 - latSpan);
  return { lonMin, lonMax: lonMin + lonSpan, latMin, latMax: latMin + latSpan };
}

function extent(items: Array<{ latMin: number; latMax: number; lonMin: number; lonMax: number }>): GeoBounds {
  return {
    latMin: Math.min(...items.map((item) => item.latMin)),
    latMax: Math.max(...items.map((item) => item.latMax)),
    lonMin: Math.min(...items.map((item) => item.lonMin)),
    lonMax: Math.max(...items.map((item) => item.lonMax)),
  };
}

const pointBounds = (point: MapPoint) => ({ latMin: point.lat, latMax: point.lat, lonMin: point.lon, lonMax: point.lon });

const SQL_KEYWORDS =
  /\b(SELECT|DISTINCT|FROM|WHERE|GROUP BY|ORDER BY|HAVING|LIMIT|AND|OR|NOT|IN|IS|NULL|AS|BETWEEN|LIKE|ILIKE|ASC|DESC|COUNT|AVG|MIN|MAX|SUM|ROUND|CASE|WHEN|THEN|ELSE|END)\b/gi;

function formatSql(sql: string) {
  return sql
    .replace(/\s+/g, " ")
    .replace(/\s(FROM|WHERE|GROUP BY|HAVING|ORDER BY|LIMIT)\b/gi, "\n$1")
    .replace(/\s(AND|OR)\s(?![^()]*\))/gi, "\n  $1 ")
    .trim();
}

/** Split SQL into keyword / string / number / plain tokens for colouring. */
function tokenizeSql(sql: string) {
  const parts = sql.split(/('(?:[^']|'')*')/g);
  return parts.flatMap((part, index) => {
    if (index % 2 === 1) return [{ kind: "string", text: part }];
    const tokens: Array<{ kind: string; text: string }> = [];
    let cursor = 0;
    for (const match of part.matchAll(SQL_KEYWORDS)) {
      const start = match.index ?? 0;
      if (start > cursor) tokens.push({ kind: "plain", text: part.slice(cursor, start) });
      tokens.push({ kind: "keyword", text: match[0].toUpperCase() });
      cursor = start + match[0].length;
    }
    if (cursor < part.length) tokens.push({ kind: "plain", text: part.slice(cursor) });
    return tokens;
  });
}

function toCsv(rows: DataRow[], columns: string[]) {
  const cell = (value: unknown) => {
    const text = value === null || value === undefined ? "" : String(value);
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return [columns.join(","), ...rows.map((row) => columns.map((column) => cell(row[column])).join(","))].join("\n");
}

const CHART_LABEL = { profile: "Profile", category: "Compare", series: "Trend", figures: "Figures", table: "" } as const;

const fixed = (value: number | undefined, digits: number) => (typeof value === "number" ? value.toFixed(digits) : "—");

/** Depths worth drawing across the profile chart. */
function depthMarkers(analysis?: ProfileAnalysis | null): DepthMarker[] {
  if (!analysis || analysis.type !== "thermocline" || analysis.success === false) return [];
  const markers: DepthMarker[] = [];
  if (typeof analysis.mixed_layer_depth_dbar === "number") {
    markers.push({ depth: analysis.mixed_layer_depth_dbar, label: "Mixed layer" });
  }
  if (typeof analysis.thermocline_depth_dbar === "number") {
    markers.push({ depth: analysis.thermocline_depth_dbar, label: "Thermocline" });
  }
  return markers;
}

/** Values computed by the backend's profile analysis, shown as figures. */
function AnalysisPanel({ analysis }: { analysis: ProfileAnalysis }) {
  if (analysis.success === false) {
    return <p className="result-lens__note">The analysis could not be completed: {analysis.error ?? "not enough data in this profile"}.</p>;
  }
  const profile = analysis.profile;
  const subject = profile?.float_id
    ? `Float ${profile.float_id}${profile.cycle_number !== undefined ? ` · cycle ${profile.cycle_number}` : ""}`
    : "Selected profile";

  if (analysis.type === "water_masses") {
    const masses = analysis.water_masses ?? [];
    return (
      <div className="analysis-panel">
        <span className="eyebrow">
          <ScanSearch size={12} /> Water masses · {subject}
        </span>
        {masses.length === 0 ? (
          <p>None of the reference Indian Ocean water-mass definitions matched this profile.</p>
        ) : (
          <ul>
            {masses.map((mass) => (
              <li key={mass.name}>
                <b>{mass.name}</b>
                <span>
                  {mass.depth_range_m ? `${fixed(mass.depth_range_m[0], 0)}–${fixed(mass.depth_range_m[1], 0)} dbar` : ""}
                  {typeof mass.core_temperature_C === "number" && ` · core ${fixed(mass.core_temperature_C, 1)} °C`}
                  {typeof mass.core_salinity_PSU === "number" && `, ${fixed(mass.core_salinity_PSU, 2)} PSU`}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <div className="analysis-panel">
      <span className="eyebrow">
        <ScanSearch size={12} /> Thermocline analysis · {subject}
      </span>
      <dl>
        <div>
          <dt>Thermocline depth</dt>
          <dd>
            {fixed(analysis.thermocline_depth_dbar, 0)} <small>dbar</small>
          </dd>
        </div>
        <div>
          <dt>Mixed layer depth</dt>
          <dd>
            {fixed(analysis.mixed_layer_depth_dbar, 0)} <small>dbar</small>
          </dd>
        </div>
        <div>
          <dt>Strength</dt>
          <dd>
            {fixed(analysis.thermocline_strength_deg_per_m, 2)} <small>°C/m</small>
          </dd>
        </div>
        <div>
          <dt>Surface to deep</dt>
          <dd>
            {fixed(analysis.surface_temp_celsius, 1)} → {fixed(analysis.deep_temp_celsius, 1)} <small>°C</small>
          </dd>
        </div>
      </dl>
      {analysis.thermocline_type && (
        <p>
          A {analysis.thermocline_strength_classification?.replaceAll("_", " ")} {analysis.thermocline_type} thermocline,
          computed from this one profile.
        </p>
      )}
    </div>
  );
}

export function ResultLens({ result }: { result: ChatResponse }) {
  const rows = useMemo(() => result.data ?? [], [result.data]);
  const shape = useMemo(() => analyzeRows(rows), [rows]);
  const positions = useMemo(() => (shape.hasPositions ? buildPositions(rows) : []), [rows, shape.hasPositions]);

  // Results grouped by region have no coordinates, but the regions themselves can be mapped.
  const namedRegions = useMemo<MapRegion[]>(() => {
    if (!shape.hasRegions) return [];
    const names = new Set(rows.map((row) => String(row.ocean_region)));
    return OCEAN_REGIONS.filter((region) => names.has(region.name)).map((region) => ({
      ...region,
      intensity: 0.8,
      hasData: true,
    }));
  }, [rows, shape.hasRegions]);

  const hasChart = shape.kind !== "table";
  const hasMap = positions.length > 0 || namedRegions.length > 0;
  // Trajectories and float lists have nothing to chart: open them on the map.
  const [view, setView] = useState<View>(hasChart ? "chart" : positions.length > 1 ? "map" : rows.length ? "table" : "sql");
  const markers = useMemo(() => depthMarkers(result.analysis), [result.analysis]);
  const matching = result.summary?.total_matching;
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const total = result.result_count ?? rows.length;
  const tabs = [
    hasChart && { key: "chart" as const, label: CHART_LABEL[shape.kind], icon: BarChart3 },
    hasMap && { key: "map" as const, label: "Map", icon: MapPinned },
    rows.length > 0 && { key: "table" as const, label: "Table", icon: Table2 },
    result.sql && { key: "sql" as const, label: "SQL", icon: Code2 },
  ].filter(Boolean) as Array<{ key: View; label: string; icon: typeof Code2 }>;

  if (!tabs.length) return null;

  function exportRows() {
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([toCsv(rows, shape.columns)], { type: "text/csv" }));
    link.download = "floatchat-query.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function copySql() {
    try {
      await navigator.clipboard.writeText(result.sql ?? "");
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access can be denied; the SQL stays selectable on screen.
    }
  }

  const visibleRows = expanded ? rows : rows.slice(0, TABLE_PAGE);
  const mapPoints = positions.slice(0, MAX_MAP_POINTS);

  return (
    <section className="result-lens" aria-label="Evidence for this answer">
      <div className="result-lens__bar">
        <div className="result-lens__tabs" role="tablist" aria-label="Result views">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={view === key}
              className={view === key ? "is-active" : ""}
              onClick={() => setView(key)}
            >
              <Icon size={13} /> {label}
            </button>
          ))}
        </div>
        <div className="result-lens__meta">
          <span>
            {formatCount(total, 1_000_000)} {total === 1 ? "row" : "rows"}
          </span>
          {typeof result.execution_time === "number" && (
            <span>{result.cached ? "cached" : `${result.execution_time.toFixed(1)} s`}</span>
          )}
          {rows.length > 0 && (
            <button type="button" className="icon-text-button" onClick={exportRows}>
              <Download size={13} /> CSV
            </button>
          )}
        </div>
      </div>

      {result.interpretation && (
        <p className="result-lens__note result-lens__note--understood">
          <b>Understood as</b> {result.interpretation}
        </p>
      )}
      {typeof matching === "number" && matching > rows.length ? (
        <p className="result-lens__note">
          {matching.toLocaleString("en-US")} measurements match these filters. The newest {total.toLocaleString("en-US")}{" "}
          were fetched{rows.length < total && `, and ${rows.length.toLocaleString("en-US")} of them are loaded here`}.
        </p>
      ) : (
        rows.length > 0 &&
        rows.length < total && (
          <p className="result-lens__note">
            Showing the first {rows.length.toLocaleString("en-US")} of {total.toLocaleString("en-US")} rows the query returned.
          </p>
        )
      )}

      {result.analysis && <AnalysisPanel analysis={result.analysis} />}

      {view === "chart" && hasChart && (
        <div className="result-lens__panel">
          <ResultChart rows={rows} shape={shape} markers={markers} />
        </div>
      )}

      {view === "map" && hasMap && (
        <div className="result-lens__panel result-lens__panel--map">
          {positions.length > 0 ? (
            <>
              <OceanMap
                view={fitView(extent(mapPoints.map(pointBounds)))}
                points={mapPoints}
                label={`Map of ${mapPoints.length} observation positions returned by the query. Coordinates are in the table view.`}
              />
              <p className="result-lens__caption">
                {positions.length.toLocaleString("en-US")} distinct {positions.length === 1 ? "position" : "positions"}
                {positions.length > MAX_MAP_POINTS && `, first ${MAX_MAP_POINTS} drawn`} · hover a point for details
              </p>
            </>
          ) : (
            <>
              <OceanMap
                view={fitView(extent(namedRegions))}
                regions={namedRegions}
                label={`Map highlighting ${namedRegions.map((region) => region.name).join(" and ")}.`}
              />
              <p className="result-lens__caption">Region boxes used by the database to classify each profile.</p>
            </>
          )}
        </div>
      )}

      {view === "table" && (
        <div className="result-lens__panel result-lens__panel--flush">
          <div className="table-shell" tabIndex={0}>
            <table>
              <thead>
                <tr>
                  {shape.columns.map((column) => (
                    <th key={column}>{humanize(column)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => (
                  <tr key={index}>
                    {shape.columns.map((column) => (
                      <td key={column}>
                        {column === "float_id" || column === "cycle_number" ? String(row[column] ?? "—") : formatValue(row[column])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > TABLE_PAGE && (
            <button type="button" className="table-more" onClick={() => setExpanded(!expanded)}>
              {expanded ? `Show first ${TABLE_PAGE} rows` : `Show all ${rows.length.toLocaleString("en-US")} loaded rows`}
            </button>
          )}
        </div>
      )}

      {view === "sql" && result.sql && (
        <div className="result-lens__panel sql-shell">
          <button type="button" onClick={copySql}>
            {copied ? <Check size={13} /> : <Clipboard size={13} />}
            {copied ? "Copied" : "Copy"}
          </button>
          <pre>
            <code>
              {tokenizeSql(formatSql(result.sql)).map((token, index) => (
                <span key={index} className={`sql-${token.kind}`}>
                  {token.text}
                </span>
              ))}
            </code>
          </pre>
        </div>
      )}
    </section>
  );
}
