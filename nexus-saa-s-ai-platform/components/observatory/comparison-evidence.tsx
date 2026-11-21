"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import type { DataRow } from "@/lib/api";
import { formatDateRange } from "@/lib/ocean";
import { downloadRows } from "@/lib/result-download";
import { analyzeRows, formatValue, toNumber } from "@/lib/result-shape";
import { ResultChart, Segmented } from "./result-charts";

const metrics = [
  { value: "temperature", label: "Temperature", unit: "°C" },
  { value: "salinity", label: "Salinity", unit: "PSU" },
] as const;

function pressureRange(min: unknown, max: unknown) {
  return min != null && max != null ? `${formatValue(min, 1)} to ${formatValue(max, 1)} dbar` : "—";
}

export function ComparisonCoverage({ rows }: { rows: DataRow[] }) {
  const available = metrics.filter(({ value }) => rows.some((row) => row[`${value}_readings`] !== undefined));
  return (
    <>
      <div className="viz-head"><div><b>Sampling coverage by region</b><span>Dates in UTC · QC counts are per variable</span></div></div>
      <div className="table-shell" tabIndex={0}>
        <table aria-label="Regional sampling coverage">
          <thead><tr>
            <th>Region</th><th>Observation dates</th><th>Pressure range</th><th>Floats</th><th>Profiles</th><th>Total readings</th>
            {available.map(({ value, label }) => <th key={value}>{label} QC 1–2</th>)}
          </tr></thead>
          <tbody>
            {rows.map((row) => (
              <tr key={String(row.ocean_region)}>
                <th scope="row">{formatValue(row.ocean_region)}</th>
                <td>{formatDateRange(row.earliest, row.latest) ?? "—"}</td>
                <td>{pressureRange(row.min_pressure, row.max_pressure)}</td>
                <td>{formatValue(row.float_count)}</td><td>{formatValue(row.profile_count)}</td><td>{formatValue(row.measurement_count)}</td>
                {available.map(({ value }) => <td key={value}>{formatValue(row[`${value}_readings`])}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="result-lens__caption">The regional overview weights every qualifying reading equally. For a comparison at the same pressure, use By depth and check how many casts support each band.</p>
    </>
  );
}

export function ComparisonDepth({ rows, regions, bandSize }: { rows: DataRow[]; regions: string[]; bandSize: number }) {
  const options = metrics.filter(({ value }) => rows.some((row) => Number(row[`${value}_casts`]) > 0));
  const [selected, setSelected] = useState<typeof metrics[number]["value"]>(options[0]?.value ?? "temperature");
  const [shared, setShared] = useState(true);
  const [requestedBand, setRequestedBand] = useState<number>();
  const metric = options.find((option) => option.value === selected) ?? options[0];
  if (!metric) return <p className="viz-empty">The matched casts contain no usable temperature or salinity depth bands.</p>;

  const readings = rows.filter((row) => Number(row[`${metric.value}_casts`]) > 0);
  const matchingRegions = new Map<number, Set<string>>();
  for (const row of readings) {
    const band = Number(row.depth_bin);
    const names = matchingRegions.get(band) ?? new Set<string>();
    names.add(String(row.ocean_region));
    matchingRegions.set(band, names);
  }
  const shown = shared
    ? readings.filter((row) => matchingRegions.get(Number(row.depth_bin))?.size === regions.length)
    : readings;
  const bands = [...new Set(shown.map((row) => Number(row.depth_bin)))].sort((a, b) => a - b);
  const band = requestedBand !== undefined && bands.includes(requestedBand) ? requestedBand : bands[0];
  const series = shown.map((row) => ({
    ocean_region: row.ocean_region,
    depth_bin: row.depth_bin,
    [`average_${metric.value}`]: row[`average_${metric.value}`],
  }));
  const shape = analyzeRows(series);
  const bandRows = new Map(shown.filter((row) => Number(row.depth_bin) === band).map((row) => [String(row.ocean_region), row]));
  const firstMean = toNumber(bandRows.get(regions[0])?.[`average_${metric.value}`]);
  const secondMean = toNumber(bandRows.get(regions[1])?.[`average_${metric.value}`]);
  const difference = regions.length === 2 && firstMean !== null && secondMean !== null ? firstMean - secondMean : null;

  return (
    <>
      <div className="viz-head comparison-depth__head">
        <div><b>Compare at the same pressure</b><span>{bandSize} dbar bands · one mean per cast in each band</span></div>
        <div className="cast-panel__actions">
          {options.length > 1 && <Segmented label="Comparison measurement" options={options} value={metric.value} onChange={setSelected} />}
          <button type="button" className="message-action" onClick={() => downloadRows(rows, "floatchat-depth-bands.csv")}><Download size={13} /> Depth bands CSV</button>
        </div>
      </div>
      <label className="comparison-depth__filter">
        <input type="checkbox" checked={shared} onChange={(event) => setShared(event.target.checked)} />
        Only bands with data in every matched region
      </label>
      {shape.kind === "profile"
        ? <ResultChart key={metric.value} rows={series} shape={shape} />
        : <p className="viz-empty">{bands.length ? "At least two bands are needed to draw a curve. The sampled band is listed below." : "No shared bands for this variable. Turn off the filter to inspect each region’s coverage."}</p>}
      {bands.length > 0 && (
        <div className="comparison-depth__samples">
          <label>Inspect pressure band
            <select className="viz-select" value={band} onChange={(event) => setRequestedBand(Number(event.target.value))}>
              {bands.map((start) => <option key={start} value={start}>{start} to {start + bandSize} dbar</option>)}
            </select>
          </label>
          <div className="table-shell" tabIndex={0}>
            <table aria-label="Sample sizes by pressure band">
              <thead><tr><th>Region</th><th>Mean {metric.label.toLowerCase()} ({metric.unit})</th><th>Contributing casts</th><th>QC 1–2 readings</th><th>Cast SD ({metric.unit})</th></tr></thead>
              <tbody>
                {regions.map((region) => {
                  const row = bandRows.get(region);
                  return (
                    <tr key={region}>
                      <th scope="row">{region}</th>
                      <td>{formatValue(toNumber(row?.[`average_${metric.value}`]), 3)}</td>
                      <td>{formatValue(row?.[`${metric.value}_casts`] ?? 0)}</td>
                      <td>{formatValue(row?.[`${metric.value}_readings`] ?? 0)}</td>
                      <td>{formatValue(toNumber(row?.[`${metric.value}_cast_sd`]), 3)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {difference !== null && (
            <p className="result-lens__caption"><b>{regions[0]} minus {regions[1]}</b> {difference >= 0 ? "+" : ""}{formatValue(difference, 3)} {metric.unit} at {band} to {band + bandSize} dbar.</p>
          )}
        </div>
      )}
      <p className="result-lens__caption">Cast SD is the spread of individual cast means within the band. Each cast gets equal weight within a band, even when instruments sample at different intervals. Use the contributing-cast counts and observation dates to judge how broadly a difference applies.</p>
    </>
  );
}
