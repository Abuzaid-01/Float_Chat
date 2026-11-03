"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, ArrowUp, Database, Droplets, LocateFixed, Menu, Orbit, Thermometer, Waves, X } from "lucide-react";
import {
  ApiError, DatabaseStats, PipelineStats, RegionCount, Suggestion, floatchatApi,
} from "@/lib/api";
import { useCountUp, useInView, useScrollSpy } from "@/lib/animation";
import { OCEAN_REGIONS, formatCount, formatDateRange } from "@/lib/ocean";
import { Coverage } from "./coverage";
import { DepthGauge } from "./depth-gauge";
import { Hero } from "./hero";
import { OceanBackdrop } from "./ocean-backdrop";
import { Pipeline } from "./pipeline";
import { ApiStatus, CompletedQuery, Workspace, WorkspaceHandle } from "./workspace";

const fallbackSuggestions: Suggestion[] = [
  { text: "Show temperature in Arabian Sea", category: "geographic" },
  { text: "Compare Arabian Sea and Bay of Bengal", category: "comparison" },
  { text: "How many floats are there?", category: "statistics" },
  { text: "Show profiles deeper than 1000 meters", category: "depth" },
];

const NAV_LINKS = [
  ["Workspace", "workspace"],
  ["Coverage", "coverage"],
  ["How it works", "architecture"],
] as const;

const HEALTH_POLL_MS = 30_000;

type MetricProps = {
  icon: typeof Orbit;
  label: string;
  value: number | null;
  format: (value: number) => string;
};

function Metric({ icon: Icon, label, value, format }: MetricProps) {
  const { ref, inView } = useInView<HTMLDivElement>({ threshold: 0.4 });
  const shown = useCountUp(value, inView);
  return (
    <div ref={ref}>
      <Icon size={16} />
      <strong>{shown === null ? "—" : format(shown)}</strong>
      <span>{label}</span>
    </div>
  );
}

export function Observatory() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [status, setStatus] = useState<ApiStatus>("checking");
  const [stats, setStats] = useState<DatabaseStats | null>(null);
  const [regions, setRegions] = useState<RegionCount[] | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[]>(fallbackSuggestions);
  const [telemetry, setTelemetry] = useState<PipelineStats | null>(null);
  const [lastQuery, setLastQuery] = useState<CompletedQuery | null>(null);
  const workspace = useRef<WorkspaceHandle>(null);
  const loaded = useRef(false);
  // The backend handles one request at a time, so a health check sent during a
  // chat would just time out and wrongly report the API as offline.
  const chatting = useRef(false);
  const activeSection = useScrollSpy(NAV_LINKS.map(([, id]) => id), 220);

  const loadTelemetry = useCallback(() => {
    floatchatApi
      .pipelineStats()
      .then((value) => setTelemetry(value.success ? value : null))
      .catch(() => undefined);
  }, []);

  /** Everything the page shows that is not a chat reply. Safe to call again after an outage. */
  const loadDataset = useCallback(async () => {
    const [database, regionList, suggestionList] = await Promise.allSettled([
      floatchatApi.stats(),
      floatchatApi.regions(),
      floatchatApi.suggestions(),
    ]);
    if (database.status === "fulfilled") setStats(database.value);
    if (regionList.status === "fulfilled") setRegions(regionList.value.regions);
    if (suggestionList.status === "fulfilled" && suggestionList.value.suggestions.length) {
      setSuggestions(suggestionList.value.suggestions);
    }
    loaded.current = database.status === "fulfilled" && regionList.status === "fulfilled";
    loadTelemetry();
  }, [loadTelemetry]);

  // Watch the API: load the dataset once it answers, and recover by itself if it was down.
  useEffect(() => {
    let alive = true;
    const check = async () => {
      if (chatting.current) return;
      try {
        const health = await floatchatApi.health();
        if (!alive) return;
        const healthy = health.status === "healthy";
        setStatus(healthy ? "online" : "offline");
        if (healthy && !loaded.current) await loadDataset();
      } catch (error) {
        if (alive && !chatting.current && !(error instanceof ApiError && error.kind === "aborted")) setStatus("offline");
      }
    };
    check();
    const timer = setInterval(check, HEALTH_POLL_MS);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [loadDataset]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const openWorkspace = useCallback(() => {
    document.getElementById("workspace")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const ask = useCallback(
    (question: string) => {
      openWorkspace();
      workspace.current?.ask(question);
    },
    [openWorkspace],
  );

  const onBusy = useCallback((busy: boolean) => {
    chatting.current = busy;
  }, []);

  const onCompleted = useCallback(
    (query: CompletedQuery) => {
      setLastQuery(query);
      loadTelemetry();
    },
    [loadTelemetry],
  );

  const namedRegions = regions
    ? OCEAN_REGIONS.filter((region) => regions.some((entry) => entry.name === region.name && entry.measurements > 0)).length
    : (stats?.regions_covered ?? null);
  const window_ = formatDateRange(stats?.date_range?.earliest, stats?.date_range?.latest);

  return (
    <main className="obs-page">
      <OceanBackdrop />
      <DepthGauge />

      <header className={`obs-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="obs-nav__inner">
          <a href="#top" className="obs-brand">
            <span>
              <Waves size={19} />
            </span>
            <b>FloatChat</b>
            <em>OBSERVATORY</em>
          </a>
          <nav className={menuOpen ? "is-open" : ""} aria-label="Sections">
            {NAV_LINKS.map(([name, id]) => (
              <a
                key={id}
                href={`#${id}`}
                className={activeSection === id ? "is-active" : ""}
                aria-current={activeSection === id ? "true" : undefined}
                onClick={() => setMenuOpen(false)}
              >
                {name}
              </a>
            ))}
            <span className={`nav-status nav-status--${status}`}>
              <span className={`status-dot ${status}`} />
              {status === "online" ? "API online" : status === "offline" ? "API offline" : "Connecting"}
            </span>
            <button
              type="button"
              className="nav-cta"
              onClick={() => {
                setMenuOpen(false);
                openWorkspace();
              }}
            >
              Ask a question <ArrowRight size={14} />
            </button>
          </nav>
          <button
            type="button"
            className="menu-button"
            aria-label="Toggle navigation"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </header>

      <Hero status={status} stats={stats} suggestions={suggestions} onAsk={ask} onOpenWorkspace={openWorkspace} />

      <section className="metrics-ribbon" aria-label="Dataset at a glance">
        <Metric icon={Orbit} label="ARGO floats" value={stats?.unique_floats ?? null} format={(value) => formatCount(Math.round(value))} />
        <Metric
          icon={Database}
          label="measurements"
          value={stats?.total_records ?? null}
          format={(value) => formatCount(Math.round(value))}
        />
        <Metric icon={LocateFixed} label="Indian Ocean regions" value={namedRegions} format={(value) => String(Math.round(value))} />
        <Metric
          icon={Thermometer}
          label="mean temperature"
          value={stats?.average_temperature ?? null}
          format={(value) => `${value.toFixed(1)} °C`}
        />
        <Metric
          icon={Droplets}
          label="mean salinity"
          value={stats?.average_salinity ?? null}
          format={(value) => `${value.toFixed(2)} PSU`}
        />
        {(window_ || status === "offline") && (
          <p>
            {window_
              ? `Observations recorded ${window_} · read live from the database`
              : "Dataset figures appear here once the API is reachable."}
          </p>
        )}
      </section>

      <Workspace ref={workspace} status={status} suggestions={suggestions} onStatus={setStatus} onCompleted={onCompleted} onBusy={onBusy} />
      <Coverage regions={regions} stats={stats} unavailable={status === "offline" && !regions} onAsk={ask} />
      <Pipeline telemetry={telemetry} stats={stats} lastQuery={lastQuery} />

      <footer className="obs-footer">
        <div className="obs-footer__floor" aria-hidden="true">
          <span>2,000 m</span>
          <i />
          <span>profiling depth reached</span>
        </div>
        <div className="obs-footer__row">
          <div className="obs-brand">
            <span>
              <Waves size={18} />
            </span>
            <b>FloatChat</b>
            <em>OBSERVATORY</em>
          </div>
          <p>Plain-English answers from ARGO float data, with the evidence attached.</p>
          <a href="#top">
            Back to the surface <ArrowUp size={14} />
          </a>
        </div>
      </footer>
    </main>
  );
}
