"use client";

import { useMemo, useState } from "react";
import { Minus, Plus, Scan } from "lucide-react";
import { USE_NETLIFY_API, type CastRef } from "@/lib/api";
import { formatCount, formatDate, type GeoBounds } from "@/lib/ocean";
import { castKey, type MapPoint } from "@/lib/result-shape";
import { OceanMap } from "./ocean-map";
import { FloatCastPanel } from "./float-cast-panel";
import { SERIES_COLORS } from "./result-charts";

const MAX_POINTS = 400;

function frameAround(lon: number, lat: number, span: number): GeoBounds {
  const width = Math.max(2, Math.min(360, span));
  const height = width / 2;
  const lonMin = Math.max(-180, Math.min(180 - width, lon - width / 2));
  const latMin = Math.max(-90, Math.min(90 - height, lat - height / 2));
  return { lonMin, lonMax: lonMin + width, latMin, latMax: latMin + height };
}

function fitPoints(points: MapPoint[]) {
  const lons = points.map(({ lon }) => lon);
  const lats = points.map(({ lat }) => lat);
  const minLon = Math.min(...lons), maxLon = Math.max(...lons);
  const minLat = Math.min(...lats), maxLat = Math.max(...lats);
  return frameAround((minLon + maxLon) / 2, (minLat + maxLat) / 2, Math.max(8, (maxLon - minLon) * 1.3, (maxLat - minLat) * 2.6));
}

export function ObservationExplorer({
  points, track, comparisonLimit,
}: {
  points: MapPoint[];
  track?: { lat: number; lon: number }[];
  comparisonLimit?: number;
}) {
  const [region, setRegion] = useState("");
  const [frame, setFrame] = useState<GeoBounds | null>(null);
  const [selection, setSelection] = useState<{ pointId: string; cast: CastRef } | null>(null);
  const regions = useMemo(() => [...new Set(points.flatMap((point) => point.region ? [point.region] : []))].sort(), [points]);
  const colors = useMemo(() => Object.fromEntries(regions.map((name, index) => [name, SERIES_COLORS[index % SERIES_COLORS.length]])), [regions]);
  const filtered = points.filter((point) => !region || point.region === region);
  const shown = filtered.slice(0, MAX_POINTS);
  const casts = shown.flatMap((point) => point.casts.map((cast) => ({
    cast, point, value: `${point.id}|${castKey(cast)}`,
  })));
  const canInspect = USE_NETLIFY_API && casts.length > 0;
  const bounds = frame ?? fitPoints(shown);
  const selectedKey = selection ? `${selection.pointId}|${castKey(selection.cast)}` : "";

  function reframe(scale: number, lon = 0, lat = 0) {
    setFrame((current) => {
      const source = current ?? bounds;
      return frameAround((source.lonMin + source.lonMax) / 2 + lon, (source.latMin + source.latMax) / 2 + lat, (source.lonMax - source.lonMin) * scale);
    });
  }

  function choosePoint(point: MapPoint) {
    if (point.casts.length) setSelection({ pointId: point.id, cast: point.casts[0] });
  }

  return (
    <>
      <div className="observation-toolbar">
        {regions.length > 1 && (
          <label>Region
            <select className="viz-select" value={region} onChange={(event) => { setRegion(event.target.value); setFrame(null); setSelection(null); }}>
              <option value="">All regions</option>
              {regions.map((name) => <option key={name}>{name}</option>)}
            </select>
          </label>
        )}
        {canInspect && (
          <label>Inspect a cast
            <select
              className="viz-select" value={selectedKey}
              onChange={(event) => {
                const entry = casts.find((item) => item.value === event.target.value);
                setSelection(entry ? { pointId: entry.point.id, cast: entry.cast } : null);
              }}
            >
              <option value="">Pick a marker or a float cycle</option>
              {casts.map(({ cast, point, value }) => (
                <option key={value} value={value}>{cast.floatId} · Cycle {cast.cycle} · {formatDate(cast.timestamp)}{point.region ? ` · ${point.region}` : ""}</option>
              ))}
            </select>
          </label>
        )}
        <div className="observation-toolbar__buttons" role="group" aria-label="Map zoom">
          <button className="message-action" type="button" aria-label="Zoom in" onClick={() => reframe(0.65)}><Plus size={15} /></button>
          <button className="message-action" type="button" aria-label="Zoom out" onClick={() => reframe(1.5)}><Minus size={15} /></button>
          <button className="message-action" type="button" onClick={() => setFrame(null)}><Scan size={14} /> Reset view</button>
        </div>
      </div>
      <OceanMap
        view={bounds} points={shown} track={region ? undefined : track}
        colors={colors} selectedPoint={selection?.pointId}
        label={`Map of ${shown.length} recorded observation positions`}
        onSelectPoint={canInspect ? choosePoint : undefined}
        onPan={(lon, lat) => reframe(1, lon, lat)}
      />
      {regions.length > 0 && (
        <ul className="viz-legend observation-legend">
          {regions.filter((name) => !region || region === name).map((name) => <li key={name}><i style={{ background: colors[name] }} />{name}</li>)}
        </ul>
      )}
      <p className="result-lens__caption">
        {formatCount(shown.length)} plotted positions{casts.length > shown.length ? ` covering ${formatCount(casts.length)} casts` : ""}.
        {comparisonLimit !== undefined && ` The map shows up to ${comparisonLimit} casts per region, sampled across the matched dates for larger results.`}
        {filtered.length > shown.length && ` Only the first ${MAX_POINTS} positions are drawn.`}
        {canInspect && " Select a point to open the full archived cast. If casts share a position, use the selector to choose one."}
      </p>
      {selection && <FloatCastPanel key={selectedKey} cast={selection.cast} onClose={() => setSelection(null)} />}
    </>
  );
}
