"use client";

import { useScrollProgress } from "@/lib/animation";
import { DEPTH_ZONES, MAX_DEPTH_M, zoneAtDepth } from "@/lib/ocean";

const TICKS = [0, 500, 1000, 1500, 2000];

/**
 * Fixed dive gauge: maps page scroll onto the 0–2,000 m an ARGO float
 * profiles, and names the ocean zone the reader is currently "in".
 */
export function DepthGauge() {
  const progress = useScrollProgress();
  const depth = Math.round(progress * MAX_DEPTH_M);
  const zone = zoneAtDepth(depth);

  return (
    <>
      <div className="obs-progress" aria-hidden="true">
        <div style={{ transform: `scaleX(${progress})` }} />
      </div>
      <aside className="depth-gauge" aria-hidden="true">
        <span className="depth-gauge__title">DEPTH</span>
        <div className="depth-gauge__track">
          {DEPTH_ZONES.map((entry) => (
            <i
              key={entry.name}
              className={entry.name === zone.name ? "is-active" : ""}
              style={{
                top: `${(entry.from / MAX_DEPTH_M) * 100}%`,
                height: `${((entry.to - entry.from) / MAX_DEPTH_M) * 100}%`,
              }}
            />
          ))}
          {TICKS.map((tick) => (
            <span key={tick} className="depth-gauge__tick" style={{ top: `${(tick / MAX_DEPTH_M) * 100}%` }}>
              {tick}
            </span>
          ))}
          <div className="depth-gauge__marker" style={{ top: `${progress * 100}%` }}>
            <b>{depth.toLocaleString("en-US")} m</b>
            <em>{zone.name}</em>
          </div>
        </div>
      </aside>
    </>
  );
}
