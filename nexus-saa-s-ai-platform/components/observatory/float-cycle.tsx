"use client";

import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/animation";
import { MAX_DEPTH_M, typicalTemperature } from "@/lib/ocean";

const SURFACE_Y = 78;
const FLOOR_Y = 372;
const PLOT_LEFT = 64;
const PLOT_RIGHT = 484;
const LOOP_SECONDS = 18;

const depthToY = (depth: number) => SURFACE_Y + (depth / MAX_DEPTH_M) * (FLOOR_Y - SURFACE_Y);
const yToDepth = (y: number) => Math.max(0, ((y - SURFACE_Y) / (FLOOR_Y - SURFACE_Y)) * MAX_DEPTH_M);

/** One mission cycle: sink to 1,000 m, drift, dive to 2,000 m, profile upward, transmit. */
const CYCLE_PATH = `M84,${SURFACE_Y} C102,${SURFACE_Y} 120,${depthToY(1000)} 152,${depthToY(1000)} L290,${depthToY(1000)} C312,${depthToY(1000)} 318,${FLOOR_Y} 340,${FLOOR_Y} C368,${FLOOR_Y} 394,${SURFACE_Y} 430,${SURFACE_Y} L${PLOT_RIGHT},${SURFACE_Y}`;

const PHASES = [
  { until: 152, label: "Descent" },
  { until: 290, label: "Drift at 1,000 m" },
  { until: 340, label: "Deep dive" },
  { until: 430, label: "Profiling ascent" },
  { until: Infinity, label: "Transmitting" },
];

const DEPTH_TICKS = [0, 500, 1000, 1500, 2000];
const SAMPLE_COUNT = 22;

/**
 * Animated diagram of how an ARGO float gathers the data behind FloatChat.
 * Purely illustrative — the temperature readout follows a typical tropical
 * profile, not a live measurement.
 */
export function FloatCycle() {
  const svg = useRef<SVGSVGElement>(null);
  const track = useRef<SVGPathElement>(null);
  const trail = useRef<SVGPathElement>(null);
  const float = useRef<SVGGElement>(null);
  const samples = useRef<SVGGElement>(null);
  const uplink = useRef<SVGGElement>(null);
  const tempMarker = useRef<SVGGElement>(null);
  const phaseText = useRef<HTMLElement>(null);
  const depthText = useRef<HTMLElement>(null);
  const tempText = useRef<HTMLElement>(null);

  useEffect(() => {
    const path = track.current;
    const host = svg.current;
    if (!path || !host) return;

    const total = path.getTotalLength();
    if (trail.current) trail.current.style.strokeDasharray = `${total}`;

    // Lay the sample dots along the ascent leg once the path can be measured.
    const sampleLengths: number[] = [];
    let ascentStart = 0;
    let ascentEnd = total;
    for (let length = 0; length <= total; length += 2) {
      const x = path.getPointAtLength(length).x;
      if (x < 340) ascentStart = length;
      if (x <= 430) ascentEnd = length;
    }
    const dots = samples.current ? Array.from(samples.current.children) : [];
    dots.forEach((dot, index) => {
      const length = ascentStart + ((index + 0.5) / dots.length) * (ascentEnd - ascentStart);
      const point = path.getPointAtLength(length);
      dot.setAttribute("cx", point.x.toFixed(1));
      dot.setAttribute("cy", point.y.toFixed(1));
      sampleLengths.push(length);
    });

    const render = (progress: number) => {
      const length = total * progress;
      const point = path.getPointAtLength(length);
      const depth = yToDepth(point.y);
      float.current?.setAttribute("transform", `translate(${point.x.toFixed(1)} ${point.y.toFixed(1)})`);
      if (trail.current) trail.current.style.strokeDashoffset = `${total - length}`;
      dots.forEach((dot, index) => dot.classList.toggle("is-on", length >= sampleLengths[index]));
      const phase = PHASES.find((entry) => point.x < entry.until) ?? PHASES[PHASES.length - 1];
      uplink.current?.classList.toggle("is-on", phase.label === "Transmitting");
      tempMarker.current?.setAttribute("transform", `translate(0 ${point.y.toFixed(1)})`);
      if (phaseText.current) phaseText.current.textContent = phase.label;
      if (depthText.current) depthText.current.textContent = `${Math.round(depth / 10) * 10} m`;
      if (tempText.current) tempText.current.textContent = `${typicalTemperature(depth).toFixed(1)} °C`;
    };

    if (prefersReducedMotion()) {
      render(0.83);
      return;
    }

    let raf = 0;
    let visible = true;
    const origin = performance.now();
    const tick = (now: number) => {
      render((((now - origin) / 1000) % LOOP_SECONDS) / LOOP_SECONDS);
      raf = requestAnimationFrame(tick);
    };
    const sync = () => {
      const shouldRun = visible && !document.hidden;
      if (shouldRun && !raf) raf = requestAnimationFrame(tick);
      if (!shouldRun && raf) {
        cancelAnimationFrame(raf);
        raf = 0;
      }
    };

    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      sync();
    });
    observer.observe(host);
    document.addEventListener("visibilitychange", sync);
    sync();

    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", sync);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="float-cycle">
      <svg
        ref={svg}
        viewBox="0 0 520 400"
        role="img"
        aria-label="Diagram of an ARGO float cycle: it sinks to 1,000 metres, drifts for about nine days, dives to 2,000 metres, then measures temperature and salinity while rising and transmits the profile by satellite."
      >
        <defs>
          <linearGradient id="cycle-water" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#2f9fb5" stopOpacity=".26" />
            <stop offset="45%" stopColor="#12456a" stopOpacity=".16" />
            <stop offset="100%" stopColor="#040d1c" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="cycle-temp" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#ffc45c" />
            <stop offset="14%" stopColor="#e8a25a" />
            <stop offset="34%" stopColor="#6fa2c8" />
            <stop offset="100%" stopColor="#2c4f9e" />
          </linearGradient>
        </defs>

        <rect x={PLOT_LEFT} y={SURFACE_Y} width={PLOT_RIGHT - PLOT_LEFT} height={FLOOR_Y - SURFACE_Y} fill="url(#cycle-water)" />

        {DEPTH_TICKS.map((tick) => (
          <g key={tick} className="float-cycle__grid">
            <line x1={PLOT_LEFT} x2={PLOT_RIGHT} y1={depthToY(tick)} y2={depthToY(tick)} />
            <text x={PLOT_LEFT - 10} y={depthToY(tick) + 3.5} textAnchor="end">
              {tick === 0 ? "0 m" : tick.toLocaleString("en-US")}
            </text>
          </g>
        ))}

        <path
          className="float-cycle__surface"
          d={`M${PLOT_LEFT},${SURFACE_Y} q13,-7 26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t26,0 t4,0`}
        />

        <path ref={track} className="float-cycle__track" d={CYCLE_PATH} />
        <path ref={trail} className="float-cycle__trail" d={CYCLE_PATH} />

        <g ref={samples} className="float-cycle__samples">
          {Array.from({ length: SAMPLE_COUNT }, (_, index) => (
            <circle key={index} r="1.9" />
          ))}
        </g>

        <g className="float-cycle__notes">
          <text x="221" y={depthToY(1000) - 12} textAnchor="middle">
            DRIFT · ~9 DAYS
          </text>
          <text x="340" y={FLOOR_Y + 18} textAnchor="middle">
            2,000 m
          </text>
          <text x="403" y={depthToY(1150)} textAnchor="start">
            SAMPLING
          </text>
          <text x="403" y={depthToY(1150) + 13} textAnchor="start">
            T · S · P
          </text>
        </g>

        <g ref={uplink} className="float-cycle__uplink">
          <path d="M457,70 L470,40" />
          <path d="M448,60 a14,14 0 0 1 18,-6" />
          <path d="M441,54 a24,24 0 0 1 30,-10" />
          <g transform="translate(474 30)">
            <rect x="-4" y="-4" width="8" height="8" rx="1.5" />
            <rect x="-15" y="-2.5" width="9" height="5" rx="1" />
            <rect x="6" y="-2.5" width="9" height="5" rx="1" />
          </g>
        </g>

        <g className="float-cycle__temp">
          <rect x="498" y={SURFACE_Y} width="5" height={FLOOR_Y - SURFACE_Y} rx="2.5" fill="url(#cycle-temp)" />
          <g ref={tempMarker}>
            <path d="M494,0 l-6,-4 v8 z" />
          </g>
        </g>

        <g ref={float} className="float-cycle__float">
          <circle r="15" />
          <line x1="0" y1="-10" x2="0" y2="-19" />
          <rect x="-3.6" y="-10" width="7.2" height="20" rx="3.6" />
        </g>
      </svg>

      <dl className="float-cycle__readout">
        <div>
          <dt>Phase</dt>
          <dd ref={phaseText}>Descent</dd>
        </div>
        <div>
          <dt>Depth</dt>
          <dd ref={depthText}>0 m</dd>
        </div>
        <div>
          <dt>Typical temp.</dt>
          <dd ref={tempText}>28.6 °C</dd>
        </div>
      </dl>
    </div>
  );
}
