"use client";

import { FormEvent, useMemo, useState } from "react";
import { Activity, ArrowDown, ArrowRight, Search } from "lucide-react";
import type { DatabaseStats, Suggestion } from "@/lib/api";
import { useParallax, useTilt, useTypewriter } from "@/lib/animation";
import { formatCount } from "@/lib/ocean";
import { FloatCycle } from "./float-cycle";
import type { ApiStatus } from "./workspace";

type HeroProps = {
  status: ApiStatus;
  stats: DatabaseStats | null;
  suggestions: Suggestion[];
  onAsk: (question: string) => void;
  onOpenWorkspace: () => void;
};

const STATUS_COPY: Record<ApiStatus, string> = {
  checking: "Connecting to the API",
  online: "Live ARGO database connected",
  offline: "API offline — start the backend",
};

/** Three drifting swells along the top edge: the page begins just under the surface. */
function SurfaceWaves() {
  const wave = "M0,40 C120,10 240,70 360,40 S600,10 720,40 S960,70 1080,40 S1320,10 1440,40 S1680,70 1800,40 S2040,10 2160,40 S2400,70 2520,40 S2760,10 2880,40 V0 H0 Z";
  return (
    <div className="surface-waves" aria-hidden="true">
      {[1, 2, 3].map((layer) => (
        <svg key={layer} className={`surface-waves__layer surface-waves__layer--${layer}`} viewBox="0 0 2880 80" preserveAspectRatio="none">
          <path d={wave} />
        </svg>
      ))}
    </div>
  );
}

export function Hero({ status, stats, suggestions, onAsk, onOpenWorkspace }: HeroProps) {
  const [question, setQuestion] = useState("");
  const examples = useMemo(() => suggestions.map((suggestion) => suggestion.text), [suggestions]);
  const typed = useTypewriter(examples, { typeSpeed: 42, deleteSpeed: 18, pause: 2200 });

  const waves = useParallax<HTMLDivElement>(0.28);
  const instrument = useParallax<HTMLDivElement>(0.07);
  const echoes = useParallax<HTMLDivElement>(-0.12);
  const tilt = useTilt<HTMLDivElement>(4);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (value) {
      onAsk(value);
      setQuestion("");
    } else onOpenWorkspace();
  }

  return (
    <section id="top" className="obs-hero">
      <div ref={waves} className="obs-hero__waves">
        <SurfaceWaves />
      </div>
      <div ref={echoes} className="hero-echoes" aria-hidden="true">
        <span className="hero-echo hero-echo--left">
          12° 43′ N<br />
          69° 18′ E
        </span>
        <span className="hero-echo hero-echo--right">
          INDIAN OCEAN
          <br />
          OBSERVATION GRID
        </span>
      </div>

      <div className="hero-copy">
        <div className="system-line">
          <span className={`status-dot ${status}`} />
          {STATUS_COPY[status]}
          <i />
        </div>
        <p className="hero-kicker">Conversational oceanography</p>
        <h1>
          <span className="rise">Read the</span>
          <span className="rise rise--late">
            <i>ocean&apos;s memory.</i>
          </span>
        </h1>
        <p className="hero-description">
          Ask questions of {stats ? formatCount(stats.total_records) : "over a million"} ARGO float measurements in plain
          English — and get the answer together with the rows, the chart and the SQL behind it.
        </p>

        <form className="hero-ask" onSubmit={submit}>
          <Search size={17} aria-hidden="true" />
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            aria-label="Ask a question about ARGO ocean data"
            placeholder={typed || "Ask about the ocean…"}
          />
          <button type="submit">
            Ask <ArrowRight size={15} />
          </button>
        </form>

        <button type="button" className="hero-dive" onClick={onOpenWorkspace}>
          <ArrowDown size={14} /> Or dive to the workspace
        </button>
      </div>

      <div ref={instrument} className="hero-instrument-wrap">
        <div ref={tilt} className="hero-instrument">
          <div className="instrument-top">
            <span>ARGO float · one 10-day cycle</span>
            <span>
              <Activity size={12} /> {status === "online" ? "Synced" : "Standby"}
            </span>
          </div>
          <FloatCycle />
          <div className="instrument-bottom">
            <span>
              <b>{stats ? formatCount(stats.unique_floats) : "—"}</b> floats in this dataset
            </span>
            <span>Illustrative cycle</span>
          </div>
        </div>
      </div>
    </section>
  );
}
