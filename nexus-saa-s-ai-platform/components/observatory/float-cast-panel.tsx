"use client";

import { useEffect, useMemo, useState } from "react";
import { Download, X } from "lucide-react";
import { floatchatApi, type ArchiveCast, type CastRef } from "@/lib/api";
import { formatCoordinate, formatDate, formatCount } from "@/lib/ocean";
import { downloadRows } from "@/lib/result-download";
import { analyzeRows, formatValue, toNumber } from "@/lib/result-shape";
import { ResultChart, Segmented, TemperatureSalinityChart } from "./result-charts";

const tabs = [
  { value: "profile", label: "Pressure profile" },
  { value: "ts", label: "T–S diagram" },
  { value: "readings", label: "Readings" },
] as const;

export function FloatCastPanel({ cast, onClose }: { cast: CastRef; onClose: () => void }) {
  const [data, setData] = useState<ArchiveCast | null>(null);
  const [error, setError] = useState<string>();
  const [attempt, setAttempt] = useState(0);
  const [view, setView] = useState<typeof tabs[number]["value"]>("profile");
  const { floatId, cycle, timestamp } = cast;
  useEffect(() => {
    const controller = new AbortController();
    void floatchatApi.cast({ floatId, cycle, timestamp }, controller.signal).then((profile) => {
      if (!controller.signal.aborted) setData(profile);
    }).catch((reason: unknown) => {
      if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Could not load the recorded cast.");
    });
    return () => controller.abort();
  }, [floatId, cycle, timestamp, attempt]);

  const shape = useMemo(() => analyzeRows(data?.readings ?? []), [data]);
  const pressures = data?.readings.flatMap((row) => {
    const pressure = toNumber(row.pressure);
    return pressure === null ? [] : [pressure];
  }) ?? [];
  const coordinates = data?.latitude != null && data.longitude != null
    ? formatCoordinate(data.latitude, data.longitude) : null;

  return (
    <section className="cast-panel" aria-label="Selected float profile">
      <div className="cast-panel__head">
        <div>
          <h3>Float {floatId} <span>· Cycle {cycle}</span></h3>
          <p>{[formatDate(timestamp), timestamp.slice(11, 16) + " UTC", data?.region, coordinates].filter(Boolean).join(" · ")}</p>
        </div>
        <button className="message-action" type="button" aria-label="Close float profile" onClick={onClose}><X size={14} /></button>
      </div>

      {!data && !error && <p role="status" className="viz-empty">Loading the recorded cast…</p>}
      {error && (
        <div className="cast-panel__error" role="status">
          <p>{error}</p>
          <button className="message-action" type="button" onClick={() => { setError(undefined); setAttempt(attempt + 1); }}>Retry profile</button>
        </div>
      )}
      {data && (
        <>
          <dl className="cast-panel__metrics">
            <div><dt>Pressure levels</dt><dd>{formatCount(data.total_levels)}</dd></div>
            <div><dt>Observed pressure</dt><dd>{pressures.length ? `${formatValue(Math.min(...pressures), 1)} to ${formatValue(Math.max(...pressures), 1)} dbar` : "—"}</dd></div>
            <div><dt>Temperature readings with QC 1–2</dt><dd>{formatCount(data.readings.filter((row) => toNumber(row.temperature) !== null).length)}</dd></div>
            <div><dt>Salinity readings with QC 1–2</dt><dd>{formatCount(data.readings.filter((row) => toNumber(row.salinity) !== null).length)}</dd></div>
          </dl>
          <div className="cast-panel__actions">
            <Segmented label="Cast display" options={[...tabs]} value={view} onChange={setView} />
            <button
              className="message-action" type="button"
              onClick={() => downloadRows(data.readings, `floatchat-${floatId}-cycle-${cycle}.csv`)}
            >
              <Download size={13} /> Cast CSV
            </button>
          </div>
          {view === "profile" && (shape.kind === "profile"
            ? <ResultChart rows={data.readings} shape={shape} />
            : <p className="viz-empty">There are too few quality-screened measurements to draw a pressure profile. Open Readings for the archived levels and flags.</p>)}
          {view === "ts" && <TemperatureSalinityChart rows={data.readings} />}
          {view === "readings" && (
            <>
              <div className="table-shell cast-panel__table" tabIndex={0}>
                <table aria-label="Cast readings with quality flags">
                  <thead><tr><th>Pressure (dbar)</th><th>Temperature (°C)</th><th>Salinity (PSU)</th><th>Temp QC</th><th>Salinity QC</th></tr></thead>
                  <tbody>
                    {data.readings.slice(0, 80).map((row, index) => (
                      <tr key={index}><td>{formatValue(row.pressure)}</td><td>{formatValue(row.temperature)}</td><td>{formatValue(row.salinity)}</td><td>{formatValue(row.temp_qc)}</td><td>{formatValue(row.sal_qc)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {data.readings.length > 80 && <p className="result-lens__caption">Showing the first 80 levels. Cast CSV includes all {formatCount(data.readings.length)} returned levels.</p>}
            </>
          )}
          <p className="result-lens__caption">Only temperature and salinity values with QC flags 1–2 appear in the charts and CSV. The original flags are included for each pressure level.{data.total_levels > data.readings.length && ` Showing the shallowest ${formatCount(data.readings.length)} levels; this cast contains ${formatCount(data.total_levels)} levels.`}</p>
        </>
      )}
    </section>
  );
}
