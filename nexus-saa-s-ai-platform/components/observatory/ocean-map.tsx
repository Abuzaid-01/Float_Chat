"use client";

import { useEffect, useRef, useState } from "react";
import { prefersReducedMotion } from "@/lib/animation";
import { GeoBounds, OceanRegion, formatCoordinate } from "@/lib/ocean";
import type { MapPoint } from "@/lib/result-shape";

export type MapRegion = OceanRegion & {
  /** 0–1 share of the busiest region; drives the fill strength. */
  intensity: number;
  hasData: boolean;
};

export type MapPin = { lat: number; lon: number; label: string };

type OceanMapProps = {
  view: GeoBounds;
  label: string;
  regions?: MapRegion[];
  selectedRegion?: string | null;
  onSelectRegion?: (name: string) => void;
  points?: MapPoint[];
  pin?: MapPin | null;
};

// Map space is plain degrees: x = longitude + 180, y = 90 − latitude.
const toX = (lon: number) => lon + 180;
const toY = (lat: number) => 90 - lat;

let landRequest: Promise<string> | null = null;

/** The coastline outline (Natural Earth 1:50m, simplified) is fetched once and shared. */
function loadLandPath() {
  if (!landRequest) {
    landRequest = fetch("/ocean/land-path.txt")
      .then((response) => (response.ok ? response.text() : ""))
      .catch(() => "");
  }
  return landRequest;
}

function useLandPath() {
  const [path, setPath] = useState("");
  useEffect(() => {
    let alive = true;
    loadLandPath().then((value) => {
      if (alive) setPath(value);
    });
    return () => {
      alive = false;
    };
  }, []);
  return path;
}

/** Eases the visible window toward `target` whenever it changes. */
function useTweenedView(target: GeoBounds) {
  const [view, setView] = useState(target);
  const current = useRef(target);

  useEffect(() => {
    const from = current.current;
    if (prefersReducedMotion()) {
      current.current = target;
      setView(target);
      return;
    }

    let raf = 0;
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 750);
      const eased = 1 - Math.pow(1 - t, 3);
      const mix = (a: number, b: number) => a + (b - a) * eased;
      const next = {
        lonMin: mix(from.lonMin, target.lonMin),
        lonMax: mix(from.lonMax, target.lonMax),
        latMin: mix(from.latMin, target.latMin),
        latMax: mix(from.latMax, target.latMax),
      };
      current.current = next;
      setView(next);
      if (t < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target.lonMin, target.lonMax, target.latMin, target.latMax]); // eslint-disable-line react-hooks/exhaustive-deps

  return view;
}

function graticule(view: GeoBounds) {
  const span = view.lonMax - view.lonMin;
  const step = span > 200 ? 30 : span > 70 ? 20 : span > 28 ? 10 : span > 14 ? 5 : 2;
  const lons: number[] = [];
  const lats: number[] = [];
  for (let lon = Math.ceil(view.lonMin / step) * step; lon <= view.lonMax; lon += step) lons.push(lon);
  for (let lat = Math.ceil(view.latMin / step) * step; lat <= view.latMax; lat += step) lats.push(lat);
  return { lons, lats };
}

const lonLabel = (lon: number) => (lon === 0 ? "0°" : `${Math.abs(lon)}°${lon > 0 ? "E" : "W"}`);
const latLabel = (lat: number) => (lat === 0 ? "EQ" : `${Math.abs(lat)}°${lat > 0 ? "N" : "S"}`);

type Tip = { x: number; y: number; title: string; detail: string };

export function OceanMap({ view: target, label, regions, selectedRegion, onSelectRegion, points, pin }: OceanMapProps) {
  const land = useLandPath();
  const view = useTweenedView(target);
  const frame = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  const width = view.lonMax - view.lonMin;
  const height = view.latMax - view.latMin;
  // One "unit" is 1% of the visible width, so marks keep their size when the view changes.
  const unit = width / 100;
  const lines = graticule(view);
  const ordered = regions
    ? [...regions].sort(
        (a, b) => (b.lonMax - b.lonMin) * (b.latMax - b.latMin) - (a.lonMax - a.lonMin) * (a.latMax - a.latMin),
      )
    : [];

  function showTip(event: React.PointerEvent | React.FocusEvent, title: string, detail: string) {
    const host = frame.current?.getBoundingClientRect();
    const mark = (event.currentTarget as Element).getBoundingClientRect();
    if (!host) return;
    const pointer = "clientX" in event && event.clientX !== 0;
    const x = (pointer ? (event as React.PointerEvent).clientX : mark.left + mark.width / 2) - host.left;
    const y = (pointer ? (event as React.PointerEvent).clientY : mark.top) - host.top;
    setTip({ x: Math.min(Math.max(x, 90), host.width - 90), y, title, detail });
  }

  return (
    <div
      ref={frame}
      className="ocean-map"
      style={{ aspectRatio: `${target.lonMax - target.lonMin} / ${target.latMax - target.latMin}` }}
    >
      <svg
        viewBox={`${toX(view.lonMin)} ${toY(view.latMax)} ${width} ${height}`}
        preserveAspectRatio="xMidYMid slice"
        role="img"
        aria-label={label}
      >
        <g className="ocean-map__graticule">
          {lines.lons.map((lon) => (
            <line key={`lon${lon}`} x1={toX(lon)} x2={toX(lon)} y1={toY(view.latMax)} y2={toY(view.latMin)} />
          ))}
          {lines.lats.map((lat) => (
            <line
              key={`lat${lat}`}
              className={lat === 0 ? "is-equator" : undefined}
              x1={toX(view.lonMin)}
              x2={toX(view.lonMax)}
              y1={toY(lat)}
              y2={toY(lat)}
            />
          ))}
        </g>

        {land && <path className="ocean-map__land" d={land} />}

        <g className="ocean-map__ticks" style={{ fontSize: unit * 1.75 }}>
          {lines.lons
            .slice(1)
            .filter((lon) => lon < view.lonMax - unit * 7)
            .map((lon) => (
              <text key={`lon${lon}`} x={toX(lon) + unit * 0.6} y={toY(view.latMin) - unit * 1.2}>
                {lonLabel(lon)}
              </text>
            ))}
          {lines.lats.slice(1).map((lat) => (
            <text key={`lat${lat}`} x={toX(view.lonMin) + unit * 1.2} y={toY(lat) - unit * 0.7}>
              {latLabel(lat)}
            </text>
          ))}
        </g>

        {ordered.map((region) => {
          const selected = region.name === selectedRegion;
          const describe = region.hasData ? "Profiles recorded here" : "No profiles in this dataset";
          return (
            <g
              key={region.name}
              className={`ocean-map__region${selected ? " is-selected" : ""}${region.hasData ? "" : " is-empty"}`}
              role={onSelectRegion ? "button" : undefined}
              tabIndex={onSelectRegion ? 0 : undefined}
              aria-label={`${region.name}. ${describe}`}
              aria-pressed={onSelectRegion ? selected : undefined}
              onClick={() => onSelectRegion?.(region.name)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectRegion?.(region.name);
                }
              }}
            >
              <rect
                x={toX(region.lonMin)}
                y={toY(region.latMax)}
                width={region.lonMax - region.lonMin}
                height={region.latMax - region.latMin}
                rx={unit * 0.6}
                style={{ fillOpacity: region.hasData ? 0.07 + region.intensity * 0.2 : 0.02 }}
              />
              {/* Small or empty boxes sit inside bigger ones; name them only when picked. */}
              {(selected || (region.hasData && region.lonMax - region.lonMin > region.name.length * unit * 1.25)) && (
                <text x={toX(region.lonMin) + unit * 1.3} y={toY(region.latMin) - unit * 1.5} style={{ fontSize: unit * 1.7 }}>
                  {region.name.toUpperCase()}
                </text>
              )}
            </g>
          );
        })}

        {points && (
          <g className="ocean-map__points">
            {points.map((point) => {
              const detail = `${formatCoordinate(point.lat, point.lon)} · ${point.count.toLocaleString("en-US")} ${
                point.count === 1 ? "row" : "rows"
              }`;
              return (
                <g
                  key={`${point.lat},${point.lon}`}
                  tabIndex={0}
                  aria-label={`${point.label}, ${detail}`}
                  onPointerMove={(event) => showTip(event, point.label, detail)}
                  onPointerLeave={() => setTip(null)}
                  onFocus={(event) => showTip(event, point.label, detail)}
                  onBlur={() => setTip(null)}
                >
                  <circle className="ocean-map__hit" cx={toX(point.lon)} cy={toY(point.lat)} r={unit * 2.4} />
                  <circle className="ocean-map__dot" cx={toX(point.lon)} cy={toY(point.lat)} r={unit * 0.85} />
                </g>
              );
            })}
          </g>
        )}

        {pin && (
          <g className="ocean-map__pin" transform={`translate(${toX(pin.lon)} ${toY(pin.lat)})`}>
            <circle className="ocean-map__pin-pulse" r={unit * 3.4} />
            <circle className="ocean-map__pin-core" r={unit * 1.1} />
            <text x={unit * 2.2} y={unit * 0.7} style={{ fontSize: unit * 2.1 }}>
              {pin.label}
            </text>
          </g>
        )}
      </svg>

      {tip && (
        <div className="viz-tip" style={{ left: tip.x, top: tip.y }} role="status">
          <b>{tip.title}</b>
          <span>{tip.detail}</span>
        </div>
      )}
    </div>
  );
}
