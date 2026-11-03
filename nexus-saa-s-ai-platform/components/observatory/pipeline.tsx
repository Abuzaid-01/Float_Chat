"use client";

import { useEffect, useRef, useState } from "react";
import { Code2, Database, Layers3, MessageSquareText, Radar, Split } from "lucide-react";
import type { DatabaseStats, PipelineStats } from "@/lib/api";
import { formatCount } from "@/lib/ocean";
import { Reveal } from "@/components/landing/reveal";
import type { CompletedQuery } from "./workspace";

type PipelineProps = {
  telemetry: PipelineStats | null;
  stats: DatabaseStats | null;
  lastQuery: CompletedQuery | null;
};

/** Shown until the visitor has run a query of their own. */
const EXAMPLE = {
  question: "Show temperature in Arabian Sea",
  sql: "SELECT float_id, cycle_number, latitude, longitude, timestamp, pressure, temperature FROM argo_profiles WHERE ocean_region IN ('Arabian Sea') AND temperature IS NOT NULL ORDER BY timestamp DESC, pressure ASC LIMIT 1000;",
  rows: 1000,
  answer: "Temperatures fall from about 28.8 °C near the surface to roughly 8.5 °C at depth across the returned measurements.",
};

function plainText(markdown: string) {
  return markdown
    .replace(/\|.*\|/g, " ")
    .replace(/[#*_`>|-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const clip = (text: string, length: number) => (text.length > length ? `${text.slice(0, length).trimEnd()}…` : text);

export function Pipeline({ telemetry, stats, lastQuery }: PipelineProps) {
  const track = useRef<HTMLOListElement>(null);
  const [active, setActive] = useState(0);

  // The trace line fills as the list scrolls past the middle of the viewport.
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    let raf = 0;

    const update = () => {
      raf = 0;
      const rect = el.getBoundingClientRect();
      // The line runs from the first step's node to the last one's.
      const centers = Array.from(el.querySelectorAll<HTMLElement>(".trace__node")).map((node) => {
        const box = node.getBoundingClientRect();
        return box.top + box.height / 2 - rect.top;
      });
      if (!centers.length) return;
      const start = centers[0];
      const length = Math.max(1, centers[centers.length - 1] - start);
      const progress = Math.min(1, Math.max(0, (window.innerHeight * 0.62 - rect.top - start) / length));
      el.style.setProperty("--trace-start", `${start.toFixed(1)}px`);
      el.style.setProperty("--trace-length", `${length.toFixed(1)}px`);
      el.style.setProperty("--trace", progress.toFixed(4));
      let reached = 0;
      centers.forEach((center, index) => {
        if (center <= start + progress * length + 1) reached = index;
      });
      setActive(reached);
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };

    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  const question = lastQuery?.question ?? EXAMPLE.question;
  const sql = lastQuery?.result.sql ?? (lastQuery ? null : EXAMPLE.sql);
  const rowCount = lastQuery ? (lastQuery.result.result_count ?? 0) : EXAMPLE.rows;
  const seconds = lastQuery?.result.execution_time;
  const answer = lastQuery ? plainText(lastQuery.result.response) : EXAMPLE.answer;
  const generator = telemetry?.stats?.sql_generator;
  const route = lastQuery?.result.route ?? (lastQuery ? null : "rules");
  const understood = lastQuery?.result.interpretation;
  const indexLoaded = telemetry?.stats?.vector_store_loaded;

  const steps = [
    {
      icon: Split,
      title: "Classify",
      body: "A greeting or a help request gets a direct reply. Anything about the data is routed into the retrieval pipeline.",
      label: "question",
      artifact: (
        <>
          <q>{clip(question, 90)}</q>
          <span>intent → {lastQuery?.result.intent ?? "data_query"}</span>
          {understood && <span>understood as → {clip(understood, 110)}</span>}
        </>
      ),
    },
    {
      icon: Radar,
      title: "Retrieve",
      body: "The question is embedded with all-MiniLM-L6-v2 and matched against profile summaries in a FAISS index. The three nearest are passed on as context for writing SQL.",
      label: "vector search",
      artifact: (
        <>
          <span>384-dimension embedding · top 3 neighbours</span>
          <span>
            index →{" "}
            {indexLoaded === undefined ? "status unknown" : indexLoaded ? "loaded" : "not loaded"}
          </span>
        </>
      ),
    },
    {
      icon: Code2,
      title: "Generate",
      body: "Questions the rules fully understand — regions, floats, depths, dates, counts, comparisons — become SQL without a model. Anything else goes to the language model. Either way only one SELECT on the ARGO table may run, inside a read-only transaction.",
      label: route === "llm" ? "sql · written by the language model" : route === "rules" ? "sql · built by rules" : "sql",
      artifact: sql ? <code>{clip(sql.replace(/\s+/g, " "), 230)}</code> : <span>No SQL was needed for this reply.</span>,
    },
    {
      icon: Database,
      title: "Execute",
      body: `The statement runs on the PostgreSQL table of ARGO measurements${
        stats ? ` — ${formatCount(stats.total_records)} rows from ${formatCount(stats.unique_floats)} floats` : ""
      }.`,
      label: "rows",
      artifact: (
        <>
          <span>
            {rowCount.toLocaleString("en-US")} {rowCount === 1 ? "row" : "rows"} returned
          </span>
          <span>table → argo_profiles</span>
        </>
      ),
    },
    {
      icon: MessageSquareText,
      title: "Answer",
      body: "The language model writes the reply from the returned rows and from totals over everything the filters matched. The rows and the SQL travel back with it so you can check the claim yourself.",
      label: "answer",
      artifact: (
        <>
          <q>{clip(answer, 190)}</q>
          {typeof seconds === "number" && <span>{seconds.toFixed(1)} s from question to answer</span>}
        </>
      ),
    },
  ];

  return (
    <section className="architecture-section" id="architecture">
      <Reveal>
        <div className="section-heading">
          <div>
            <span className="eyebrow">
              <Layers3 size={13} /> How an answer is made
            </span>
            <h2>
              Every answer has
              <br />a <i>provenance trail.</i>
            </h2>
          </div>
          <p>
            {lastQuery
              ? "This is the trail left by your last question, step by step."
              : "An example trail is shown below. Ask a question in the workspace and this section replays yours."}
          </p>
        </div>
      </Reveal>

      <ol className="trace" ref={track}>
        {steps.map(({ icon: Icon, title, body, label, artifact }, index) => (
          <li key={title} className={index <= active ? "is-reached" : ""}>
            <div className="trace__node">
              <Icon size={16} />
            </div>
            <div className="trace__copy">
              <span>0{index + 1}</span>
              <h3>{title}</h3>
              <p>{body}</p>
            </div>
            <div className="trace__artifact">
              <em>{label}</em>
              {artifact}
            </div>
          </li>
        ))}
      </ol>

      <Reveal>
        <div className="telemetry">
          <dl>
            <div>
              <dt>Built by rules</dt>
              <dd>{generator ? formatCount(generator.rule_built ?? 0) : "—"}</dd>
            </div>
            <div>
              <dt>Written by the model</dt>
              <dd>{generator ? formatCount(generator.llm_built ?? 0) : "—"}</dd>
            </div>
            <div>
              <dt>Failed to generate</dt>
              <dd>{generator ? formatCount(generator.failed_queries) : "—"}</dd>
            </div>
            <div>
              <dt>Vector index</dt>
              <dd>
                {indexLoaded === undefined
                  ? "—"
                  : indexLoaded
                    ? `${formatCount(telemetry?.stats?.vector_count ?? 0)} profiles`
                    : "Not loaded"}
              </dd>
            </div>
          </dl>
          <p>SQL statements by origin, counted since the API process last started.</p>
        </div>
      </Reveal>
    </section>
  );
}
