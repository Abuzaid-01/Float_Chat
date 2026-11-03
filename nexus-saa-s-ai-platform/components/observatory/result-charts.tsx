"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { DataRow } from "@/lib/api";
import { parseTimestamp } from "@/lib/ocean";
import { buildProfiles, formatValue, humanize, niceTicks, toNumber, unitFor } from "@/lib/result-shape";
import type { Measure, ResultShape } from "@/lib/result-shape";

/**
 * Series colours, assigned in this fixed order. Checked for colour-blind
 * separation and contrast against the chart surface (#071a2b).
 */
export const SERIES_COLORS = ["#2a9db0", "#c98500", "#807cec", "#d75a8b"];
const MAX_SERIES = SERIES_COLORS.length;

type Series = { id: string; label: string; points: Array<{ x: number; y: number }> };

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return { ref, width };
}

export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Array<{ value: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={option.value === value ? "is-active" : ""}
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function Legend({ series }: { series: Series[] }) {
  if (series.length < 2) return null;
  return (
    <ul className="viz-legend">
      {series.map((entry, index) => (
        <li key={entry.id}>
          <i style={{ background: SERIES_COLORS[index] }} />
          {entry.label}
        </li>
      ))}
    </ul>
  );
}

/** A labelled depth drawn across a profile chart (thermocline, mixed layer). */
export type DepthMarker = { depth: number; label: string };

type XYChartProps = {
  series: Series[];
  markers?: DepthMarker[];
  xTitle: string;
  yTitle: string;
  formatX: (value: number) => string;
  formatY: (value: number) => string;
  /** Depth profiles read top-down: zero at the top, hover picks a depth. */
  depthAxis?: boolean;
  xTicks?: number[];
  label: string;
};

const MARGIN = { top: 12, right: 18, bottom: 40, left: 56 };

/** Markers too close to label separately share one label, so text never overlaps. */
function labelledMarkers(markers: DepthMarker[], sy: (depth: number) => number) {
  const sorted = [...markers].sort((a, b) => a.depth - b.depth);
  return sorted.map((marker, index) => {
    const name = (entry: DepthMarker) => `${entry.label} ${formatValue(entry.depth, 0)} dbar`;
    const next = sorted[index + 1];
    const previous = sorted[index - 1];
    if (next && Math.abs(sy(next.depth) - sy(marker.depth)) < 16) return { ...marker, text: "" };
    if (previous && Math.abs(sy(marker.depth) - sy(previous.depth)) < 16) {
      return { ...marker, text: `${name(previous)} · ${name(marker)}` };
    }
    return { ...marker, text: name(marker) };
  });
}
const CHART_HEIGHT = 300;

/** Line chart with a snapping crosshair; one readout lists every series. */
function XYChart({ series, markers = [], xTitle, yTitle, formatX, formatY, depthAxis = false, xTicks: givenXTicks, label }: XYChartProps) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const all = series.flatMap((entry) => entry.points);
  const xs = all.map((point) => point.x);
  const ys = all.map((point) => point.y);
  const xTicks = givenXTicks ?? niceTicks(Math.min(...xs), Math.max(...xs), width < 480 ? 4 : 6);
  const yTicks = niceTicks(depthAxis ? 0 : Math.min(...ys), Math.max(...ys), 5);
  const xMin = givenXTicks ? Math.min(...xs) : xTicks[0];
  const xMax = givenXTicks ? Math.max(...xs) : xTicks[xTicks.length - 1];
  const yMin = yTicks[0];
  const yMax = yTicks[yTicks.length - 1];

  const innerWidth = Math.max(10, width - MARGIN.left - MARGIN.right);
  const innerHeight = CHART_HEIGHT - MARGIN.top - MARGIN.bottom;
  const sx = (value: number) => MARGIN.left + ((value - xMin) / (xMax - xMin || 1)) * innerWidth;
  const sy = (value: number) => {
    const t = (value - yMin) / (yMax - yMin || 1);
    return MARGIN.top + (depthAxis ? t : 1 - t) * innerHeight;
  };

  // The crosshair follows the independent variable: depth for profiles, x otherwise.
  const hoverKey = depthAxis ? ("y" as const) : ("x" as const);
  // A series only reports a value where it actually has a sample near the crosshair.
  const reach = (depthAxis ? yMax - yMin : xMax - xMin) * 0.04;
  const readout =
    hover === null
      ? []
      : series.map((entry, index) => {
          let nearest = entry.points[0];
          for (const point of entry.points) {
            if (Math.abs(point[hoverKey] - hover) < Math.abs(nearest[hoverKey] - hover)) nearest = point;
          }
          const distance = Math.abs(nearest[hoverKey] - hover);
          return { entry, index, point: nearest, distance, sampled: distance <= reach };
        });
  const sampled = readout.filter((item) => item.sampled);
  const anchor = sampled.length
    ? sampled.reduce((best, item) => (item.distance < best.distance ? item : best)).point
    : undefined;

  function onMove(event: React.PointerEvent<SVGRectElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    if (depthAxis) {
      const t = (event.clientY - box.top) / box.height;
      setHover(yMin + t * (yMax - yMin));
    } else {
      const t = (event.clientX - box.left) / box.width;
      setHover(xMin + t * (xMax - xMin));
    }
  }

  return (
    <div className="viz-chart" ref={ref}>
      <Legend series={series} />
      {width > 0 && (
        <div className="viz-chart__plot">
          <svg width={width} height={CHART_HEIGHT} role="img" aria-label={label}>
            {yTicks.map((tick) => (
              <g key={`y${tick}`} className="viz-grid">
                <line x1={MARGIN.left} x2={MARGIN.left + innerWidth} y1={sy(tick)} y2={sy(tick)} />
                <text x={MARGIN.left - 9} y={sy(tick) + 3.5} textAnchor="end">
                  {formatY(tick)}
                </text>
              </g>
            ))}
            {xTicks.map((tick) => (
              <g key={`x${tick}`} className="viz-grid viz-grid--x">
                <line x1={sx(tick)} x2={sx(tick)} y1={MARGIN.top} y2={MARGIN.top + innerHeight} />
                <text x={sx(tick)} y={MARGIN.top + innerHeight + 17} textAnchor="middle">
                  {formatX(tick)}
                </text>
              </g>
            ))}
            <text className="viz-axis-title" x={MARGIN.left + innerWidth / 2} y={CHART_HEIGHT - 4} textAnchor="middle">
              {xTitle}
            </text>
            <text
              className="viz-axis-title"
              transform={`translate(12 ${MARGIN.top + innerHeight / 2}) rotate(-90)`}
              textAnchor="middle"
            >
              {yTitle}
            </text>

            {depthAxis &&
              labelledMarkers(
                markers.filter((marker) => marker.depth >= yMin && marker.depth <= yMax),
                sy,
              ).map((marker) => (
                <g key={marker.label} className="viz-depth-marker">
                  <line x1={MARGIN.left} x2={MARGIN.left + innerWidth} y1={sy(marker.depth)} y2={sy(marker.depth)} />
                  {marker.text && (
                    <text x={MARGIN.left + innerWidth - 6} y={sy(marker.depth) + 14} textAnchor="end">
                      {marker.text}
                    </text>
                  )}
                </g>
              ))}

            {series.map((entry, index) => (
              <path
                key={entry.id}
                className="viz-line"
                stroke={SERIES_COLORS[index]}
                d={entry.points
                  .map((point, i) => `${i ? "L" : "M"}${sx(point.x).toFixed(1)},${sy(point.y).toFixed(1)}`)
                  .join("")}
              />
            ))}

            {anchor &&
              (depthAxis ? (
                <line className="viz-crosshair" x1={MARGIN.left} x2={MARGIN.left + innerWidth} y1={sy(anchor.y)} y2={sy(anchor.y)} />
              ) : (
                <line className="viz-crosshair" x1={sx(anchor.x)} x2={sx(anchor.x)} y1={MARGIN.top} y2={MARGIN.top + innerHeight} />
              ))}
            {sampled.map(({ entry, index, point }) => (
              <circle key={entry.id} className="viz-marker" cx={sx(point.x)} cy={sy(point.y)} r="4.5" fill={SERIES_COLORS[index]} />
            ))}

            <rect
              x={MARGIN.left}
              y={MARGIN.top}
              width={innerWidth}
              height={innerHeight}
              fill="transparent"
              onPointerMove={onMove}
              onPointerLeave={() => setHover(null)}
            />
          </svg>

          {anchor && (
            <div
              className="viz-tip"
              style={{
                left: Math.min(Math.max(sx(anchor.x), 100), width - 100),
                top: sy(anchor.y),
              }}
            >
              <span>{depthAxis ? `${formatY(anchor.y)} dbar` : formatX(anchor.x)}</span>
              {readout.map(({ entry, index, point, sampled: hasSample }) => (
                <div key={entry.id} className="viz-tip__row">
                  <i style={{ background: SERIES_COLORS[index] }} />
                  <b>{hasSample ? (depthAxis ? formatX(point.x) : formatY(point.y)) : "—"}</b>
                  {series.length > 1 && <em>{hasSample ? entry.label : `${entry.label} · no sample here`}</em>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ProfileChart({
  rows,
  measures,
  depthColumn,
  markers,
}: {
  rows: DataRow[];
  measures: Measure[];
  depthColumn: string;
  markers?: DepthMarker[];
}) {
  const [measureKey, setMeasureKey] = useState(measures[0].key);
  const measure = measures.find((entry) => entry.key === measureKey) ?? measures[0];
  const profiles = useMemo(() => buildProfiles(rows, measure.key, depthColumn), [rows, measure.key, depthColumn]);
  const binned = depthColumn === "depth_bin";
  const shown = profiles.slice(0, MAX_SERIES);
  const hidden = profiles.length - shown.length;

  if (!shown.length) return <div className="viz-empty">No plottable depth samples in the returned rows.</div>;

  const series: Series[] = shown.map((profile) => ({
    id: profile.id,
    label: profile.label,
    points: profile.points.map((point) => ({ x: point.value, y: point.depth })),
  }));
  const unit = measure.unit ? ` (${measure.unit})` : "";

  return (
    <div>
      <div className="viz-head">
        <div>
          <b>{measure.label} against depth</b>
          <span>
            {shown.length === 1 ? shown[0].label : `${shown.length} profiles`}
            {hidden > 0 && ` · ${hidden} more in the table`}
          </span>
        </div>
        {measures.length > 1 && (
          <Segmented
            label="Measurement"
            value={measure.key}
            onChange={setMeasureKey}
            options={measures.map((entry) => ({ value: entry.key, label: entry.label }))}
          />
        )}
      </div>
      <XYChart
        series={series}
        markers={markers}
        depthAxis
        xTitle={`${measure.label}${unit}`}
        yTitle={binned ? "Depth bin (dbar ≈ m)" : "Pressure (dbar ≈ m)"}
        formatX={(value) => formatValue(value, 2)}
        formatY={(value) => formatValue(value, 0)}
        label={`${measure.label} against pressure for ${shown.map((profile) => profile.label).join(", ")}. Values are in the table view.`}
      />
    </div>
  );
}

const shortDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const longDate = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "UTC",
});

function SeriesChart({ rows, shape }: { rows: DataRow[]; shape: ResultShape }) {
  const [column, setColumn] = useState(shape.valueColumns[0]);
  const points = useMemo(() => {
    const list: Array<{ x: number; y: number }> = [];
    for (const row of rows) {
      const time = parseTimestamp(row[shape.timeColumn ?? ""]);
      const value = toNumber(row[column]);
      if (time && value !== null) list.push({ x: time.getTime(), y: value });
    }
    return list.sort((a, b) => a.x - b.x);
  }, [rows, column, shape.timeColumn]);

  if (points.length < 2) return <div className="viz-empty">Not enough dated values to draw a series.</div>;

  const first = points[0].x;
  const last = points[points.length - 1].x;
  const ticks = first === last ? [first] : [0, 0.25, 0.5, 0.75, 1].map((t) => first + (last - first) * t);
  const unit = unitFor(column);

  return (
    <div>
      <div className="viz-head">
        <div>
          <b>{humanize(column)} over time</b>
          <span>{points.length.toLocaleString("en-US")} dated values, in UTC</span>
        </div>
        {shape.valueColumns.length > 1 && (
          <Segmented
            label="Value"
            value={column}
            onChange={setColumn}
            options={shape.valueColumns.slice(0, 4).map((entry) => ({ value: entry, label: humanize(entry) }))}
          />
        )}
      </div>
      <XYChart
        series={[{ id: column, label: humanize(column), points }]}
        xTicks={ticks}
        xTitle="Observation time (UTC)"
        yTitle={`${humanize(column)}${unit ? ` (${unit})` : ""}`}
        formatX={(value) => (ticks.includes(value) ? shortDate : longDate).format(new Date(value))}
        formatY={(value) => formatValue(value, 2)}
        label={`${humanize(column)} over time. Values are in the table view.`}
      />
    </div>
  );
}

function CategoryBars({ rows, shape }: { rows: DataRow[]; shape: ResultShape }) {
  const [column, setColumn] = useState(shape.valueColumns[0]);
  const category = shape.categoryColumn ?? "";
  const values = rows.map((row) => ({ label: String(row[category] ?? "—"), value: toNumber(row[column]) }));
  const numbers = values.map((entry) => entry.value ?? 0);
  const low = Math.min(0, ...numbers);
  const high = Math.max(0, ...numbers);
  const span = high - low || 1;
  const zero = ((0 - low) / span) * 100;
  const unit = unitFor(column);

  return (
    <div>
      <div className="viz-head">
        <div>
          <b>
            {humanize(column)} by {humanize(category).toLowerCase()}
          </b>
          <span>{unit ? `Values in ${unit}` : `${rows.length} groups`}</span>
        </div>
        {shape.valueColumns.length > 1 && (
          <select className="viz-select" aria-label="Value to compare" value={column} onChange={(event) => setColumn(event.target.value)}>
            {shape.valueColumns.map((entry) => (
              <option key={entry} value={entry}>
                {humanize(entry)}
              </option>
            ))}
          </select>
        )}
      </div>
      <ul className="viz-bars">
        {values.map((entry) => {
          const value = entry.value ?? 0;
          const size = (Math.abs(value) / span) * 100;
          return (
            <li key={entry.label}>
              <span className="viz-bars__label">{entry.label}</span>
              <div className="viz-bars__track">
                <i
                  className={value < 0 ? "is-negative" : ""}
                  style={{ left: `${value < 0 ? zero - size : zero}%`, width: `${size}%` }}
                />
              </div>
              <b>{entry.value === null ? "—" : formatValue(entry.value, 2)}</b>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Figures({ row }: { row: DataRow }) {
  return (
    <dl className="viz-figures">
      {Object.entries(row).map(([key, value]) => {
        const numeric = toNumber(value);
        const unit = unitFor(key);
        return (
          <div key={key}>
            <dt>{humanize(key)}</dt>
            <dd>
              {numeric !== null && !/(_id|^id)$/.test(key) ? formatValue(numeric, 2) : formatValue(value)}
              {unit && numeric !== null && <small>{unit}</small>}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}

export function ResultChart({ rows, shape, markers }: { rows: DataRow[]; shape: ResultShape; markers?: DepthMarker[] }) {
  if (shape.kind === "profile") {
    return (
      <ProfileChart
        rows={rows}
        measures={shape.profileMeasures}
        depthColumn={shape.depthColumn ?? "pressure"}
        markers={markers}
      />
    );
  }
  if (shape.kind === "category") return <CategoryBars rows={rows} shape={shape} />;
  if (shape.kind === "series") return <SeriesChart rows={rows} shape={shape} />;
  if (shape.kind === "figures") return <Figures row={rows[0]} />;
  return null;
}
