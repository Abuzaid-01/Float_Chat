"use client";

import { FormEvent, useMemo, useRef, useState } from "react";
import { ArrowUpRight, Crosshair, LoaderCircle, LocateFixed, Search } from "lucide-react";
import { ApiError, DatabaseStats, FloatInfo, RegionCount, floatchatApi } from "@/lib/api";
import {
  GeoBounds, INDIAN_OCEAN_VIEW, OCEAN_REGIONS, formatCoordinate, formatCount, formatDateRange, insideBounds,
} from "@/lib/ocean";
import { Reveal } from "@/components/landing/reveal";
import { MapRegion, OceanMap } from "./ocean-map";

type CoverageProps = {
  regions: RegionCount[] | null;
  stats: DatabaseStats | null;
  unavailable: boolean;
  onAsk: (question: string) => void;
};

/** Keep the Indian Ocean framing but slide it so `lat, lon` sits in the middle. */
function viewAround(lat: number, lon: number): GeoBounds {
  const lonSpan = INDIAN_OCEAN_VIEW.lonMax - INDIAN_OCEAN_VIEW.lonMin;
  const latSpan = INDIAN_OCEAN_VIEW.latMax - INDIAN_OCEAN_VIEW.latMin;
  const lonMin = Math.min(Math.max(lon - lonSpan / 2, -180), 180 - lonSpan);
  const latMin = Math.min(Math.max(lat - latSpan / 2, -90), 90 - latSpan);
  return { lonMin, lonMax: lonMin + lonSpan, latMin, latMax: latMin + latSpan };
}

const rangeLabel = (low: number | null, high: number | null, digits: number, unit: string) =>
  low === null || high === null ? "no good-quality values" : `${low.toFixed(digits)}–${high.toFixed(digits)} ${unit}`;

const boundsLabel = (region: GeoBounds) => {
  const lat = (value: number) => `${Math.abs(value)}°${value >= 0 ? "N" : "S"}`;
  const lon = (value: number) => `${Math.abs(value)}°${value >= 0 ? "E" : "W"}`;
  return `${lat(region.latMin)}–${lat(region.latMax)}, ${lon(region.lonMin)}–${lon(region.lonMax)}`;
};

export function Coverage({ regions, stats, unavailable, onAsk }: CoverageProps) {
  const [selected, setSelected] = useState("Arabian Sea");
  const [floatId, setFloatId] = useState("");
  const [float, setFloat] = useState<FloatInfo | null>(null);
  const [lookup, setLookup] = useState<{ state: "idle" | "loading" | "error"; message?: string }>({ state: "idle" });
  const request = useRef<AbortController | null>(null);

  const counts = useMemo(() => new Map((regions ?? []).map((region) => [region.name, region.measurements])), [regions]);
  const busiest = Math.max(1, ...OCEAN_REGIONS.map((region) => counts.get(region.name) ?? 0));
  const total = stats?.total_records ?? (regions ? regions.reduce((sum, region) => sum + region.measurements, 0) : 0);

  const mapRegions: MapRegion[] = OCEAN_REGIONS.map((region) => {
    const measurements = counts.get(region.name) ?? 0;
    return { ...region, intensity: measurements / busiest, hasData: measurements > 0 };
  });
  const rows = [...OCEAN_REGIONS]
    .map((region) => ({ ...region, measurements: counts.get(region.name) ?? 0 }))
    .sort((a, b) => b.measurements - a.measurements);
  const elsewhere = (regions ?? [])
    .filter((region) => !OCEAN_REGIONS.some((known) => known.name === region.name))
    .reduce((sum, region) => sum + region.measurements, 0);

  const active = rows.find((region) => region.name === selected) ?? rows[0];
  const floatOutside = float && !insideBounds(float.avg_location.lat, float.avg_location.lon, INDIAN_OCEAN_VIEW);
  const view = float && floatOutside ? viewAround(float.avg_location.lat, float.avg_location.lon) : INDIAN_OCEAN_VIEW;

  async function locateFloat(event: FormEvent) {
    event.preventDefault();
    const id = floatId.trim();
    if (!/^\d{4,9}$/.test(id)) {
      setLookup({ state: "error", message: "Float IDs are numbers, such as 2903956." });
      return;
    }
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLookup({ state: "loading" });
    try {
      const info = await floatchatApi.float(id, controller.signal);
      setFloat(info);
      setLookup({ state: "idle" });
    } catch (error) {
      if (error instanceof ApiError && error.kind === "aborted") return;
      setFloat(null);
      const missing = error instanceof ApiError && /not found/i.test(error.message);
      setLookup({
        state: "error",
        message: missing
          ? `No float ${id} in this dataset. Check the ID and try again.`
          : error instanceof ApiError
            ? error.message
            : "The float lookup failed.",
      });
    }
  }

  return (
    <section className="coverage-section" id="coverage">
      <Reveal>
        <div className="section-heading">
          <div>
            <span className="eyebrow">
              <LocateFixed size={13} /> Coverage
            </span>
            <h2>
              Where the floats
              <br />
              <i>have been listening.</i>
            </h2>
          </div>
          <p>
            Every profile is sorted into an Indian Ocean region by where it surfaced. Pick a region to see how much of
            the dataset it holds, or look up a single float by its ID.
          </p>
        </div>
      </Reveal>

      <div className="coverage-grid">
        <Reveal direction="left" className="coverage-map">
          <div className="coverage-map__frame">
            <div className="coverage-map__head">
              <span>Indian Ocean · region grid</span>
              <span>{float ? `Float ${float.float_id}` : (formatDateRange(stats?.date_range?.earliest, stats?.date_range?.latest) ?? "")}</span>
            </div>
            <OceanMap
              view={view}
              regions={mapRegions}
              selectedRegion={selected}
              onSelectRegion={setSelected}
              pin={float ? { ...float.avg_location, label: float.float_id } : null}
              label="Map of the Indian Ocean showing the six regions used to classify ARGO profiles. The same figures are listed beside the map."
            />
          </div>
        </Reveal>

        <Reveal direction="right" delay={100} className="coverage-panel">
          <div className="region-list" role="group" aria-label="Regions by number of measurements">
            {rows.map((region) => (
              <button
                key={region.name}
                type="button"
                className={`region-row${region.name === selected ? " is-selected" : ""}`}
                aria-pressed={region.name === selected}
                onClick={() => setSelected(region.name)}
              >
                <span>{region.name}</span>
                <b>{regions ? (region.measurements ? formatCount(region.measurements) : "none") : "—"}</b>
                <span className="region-row__meter">
                  <i style={{ transform: `scaleX(${region.measurements / busiest})` }} />
                </span>
              </button>
            ))}
            {elsewhere > 0 && (
              <p className="region-list__note">
                {formatCount(elsewhere)} more measurements sit outside these six regions.
              </p>
            )}
            {unavailable && <p className="region-list__note">Region counts need the API — they will appear once it is reachable.</p>}
          </div>

          <div className="region-detail">
            <span className="eyebrow">
              <Crosshair size={12} /> {active.name}
            </span>
            <p>
              {boundsLabel(active)}
              {regions && active.measurements > 0 && total > 0 && (
                <>
                  {" · "}
                  {formatCount(active.measurements, 10_000_000)} measurements,{" "}
                  {((active.measurements / total) * 100).toFixed(1)}% of the dataset
                </>
              )}
              {regions && active.measurements === 0 && " · no profiles in this dataset yet"}
            </p>
            <div className="region-detail__actions">
              {[
                ["Temperature", `Show temperature in ${active.name}`],
                ["Salinity", `Show salinity in ${active.name}`],
                ["Deep profiles", `Show profiles deeper than 1000 meters in ${active.name}`],
              ].map(([label, question]) => (
                <button key={label} type="button" onClick={() => onAsk(question)}>
                  {label} <ArrowUpRight size={12} />
                </button>
              ))}
            </div>
          </div>

          <form className="float-lookup" onSubmit={locateFloat}>
            <label htmlFor="float-id">Find a float</label>
            <div>
              <input
                id="float-id"
                inputMode="numeric"
                autoComplete="off"
                placeholder="Float ID, e.g. 2903956"
                value={floatId}
                onChange={(event) => setFloatId(event.target.value)}
              />
              <button type="submit" disabled={lookup.state === "loading"} aria-label="Locate float">
                {lookup.state === "loading" ? <LoaderCircle size={15} className="spin" /> : <Search size={15} />}
              </button>
            </div>
            {lookup.state === "error" && <p className="float-lookup__error">{lookup.message}</p>}
            {float && (
              <div className="float-card">
                <dl>
                  <div>
                    <dt>Cycles</dt>
                    <dd>{formatCount(float.total_cycles)}</dd>
                  </div>
                  <div>
                    <dt>Measurements</dt>
                    <dd>{formatCount(float.total_measurements)}</dd>
                  </div>
                  <div>
                    <dt>Temperature</dt>
                    <dd>{rangeLabel(float.temperature.min, float.temperature.max, 1, "°C")}</dd>
                  </div>
                  <div>
                    <dt>Salinity</dt>
                    <dd>{rangeLabel(float.salinity.min, float.salinity.max, 2, "PSU")}</dd>
                  </div>
                </dl>
                <p>
                  {float.ocean_region && float.ocean_region !== "Other" ? `${float.ocean_region} · ` : ""}
                  mean position {formatCoordinate(float.avg_location.lat, float.avg_location.lon)}
                  {formatDateRange(float.first_measurement, float.last_measurement) &&
                    ` · ${formatDateRange(float.first_measurement, float.last_measurement)}`}
                </p>
                <button type="button" onClick={() => onAsk(`Show temperature profile for float ${float.float_id}`)}>
                  Ask about float {float.float_id} <ArrowUpRight size={12} />
                </button>
              </div>
            )}
          </form>
        </Reveal>
      </div>
    </section>
  );
}
