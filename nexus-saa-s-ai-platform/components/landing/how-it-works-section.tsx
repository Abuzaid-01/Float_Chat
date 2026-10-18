"use client";

import { useEffect, useRef, useState } from "react";
import { GitBranch, Cpu, Database, Search } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "Domain Query Expansion",
    icon: Search,
    description:
      "Normalizes oceanographic acronyms (SST, SSS, DO, Chl-a, BoB, AS) and enriches domain context before vectorization.",
    filename: "domain_utils.py",
    code: `def expand_query(query: str) -> str:
    # "SST in AS" -> "sea surface temperature in Arabian Sea"
    for pattern, term in OCEAN_SYNONYMS.items():
        query = re.sub(pattern, term, query, flags=re.IGNORECASE)
    return query.strip()`,
  },
  {
    number: "02",
    title: "Hybrid Search (BM25 + FAISS)",
    icon: GitBranch,
    description:
      "Fuses 384-dimensional dense semantic vectors with BM25 Okapi exact keyword retrieval via Reciprocal Rank Fusion (RRF).",
    filename: "hybrid_retriever.py",
    code: `def search(self, query_text, query_emb, k=5):
    faiss_res = self.vector_store.search(query_emb, k=15)
    bm25_res = self._bm25_search(query_text, k=15)
    
    # Reciprocal Rank Fusion
    return self._rrf_merge(faiss_res, bm25_res, k=k)`,
  },
  {
    number: "03",
    title: "Dynamic Schema Prompt Pruning",
    icon: Cpu,
    description:
      "Inspects query intent to strip out unused sensors and regions, reducing prompt size by 57% and eliminating hallucinations.",
    filename: "sql_generator.py",
    code: `def _build_relevant_schema(self, analysis):
    # Only include queried parameters (Temp/Salinity vs BGC)
    # Reduces schema prompt from 49+ lines to ~21 lines
    schema = [PRIMARY_COLUMNS]
    if 'temperature' in analysis['parameters']:
        schema.append(TEMP_COLUMNS)
    return "\\n".join(schema)`,
  },
  {
    number: "04",
    title: "Neon DB Execution & LLM Analysis",
    icon: Database,
    description:
      "Executes SQL directly on Neon Cloud PostgreSQL (1.2M+ rows) and feeds structured data to Llama 3.3 for scientific reporting.",
    filename: "response_generator.py",
    code: `ai_response = llm.generate_response(
    question=user_query,
    query_results=results_df,
    context=similar_profiles
) # Returns scientific markdown + formatted tables`,
  },
];

export function HowItWorksSection() {
  const [activeStep, setActiveStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);
  const sectionRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setIsVisible(true);
      },
      { threshold: 0.1 }
    );

    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  // Auto-cycle through steps
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % steps.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section
      id="how-it-works"
      ref={sectionRef}
      className="relative py-28 overflow-hidden bg-secondary/30 border-y border-border/50"
    >
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <div className="mb-16">
          <p className="text-xs font-mono text-cyan-400 mb-2 uppercase tracking-widest">// RAG ARCHITECTURE</p>
          <h2
            className={`text-3xl lg:text-5xl font-bold tracking-tight mb-4 transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            <span className="text-balance">Four-Stage Pipeline for</span>
            <br />
            <span className="bg-gradient-to-r from-cyan-300 via-primary to-blue-400 bg-clip-text text-transparent">
              Zero-Hallucination Ocean SQL.
            </span>
          </h2>
          <p className="text-muted-foreground text-sm sm:text-base max-w-2xl">
            From raw natural language to validated PostgreSQL queries and domain-accurate oceanographic summaries.
          </p>
        </div>

        {/* Main content grid */}
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          {/* Steps list */}
          <div className="space-y-3">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <button
                  key={step.number}
                  type="button"
                  onClick={() => setActiveStep(index)}
                  className={`w-full text-left p-5 sm:p-6 rounded-2xl border transition-all duration-300 ${
                    activeStep === index
                      ? "bg-card/95 border-primary/50 card-shadow"
                      : "bg-card/30 border-transparent hover:bg-card/60"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono text-xs font-bold shrink-0 transition-colors ${
                        activeStep === index
                          ? "bg-primary text-primary-foreground"
                          : "bg-secondary text-muted-foreground"
                      }`}
                    >
                      {step.number}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-base sm:text-lg font-semibold text-foreground">{step.title}</h3>
                      </div>
                      <p
                        className={`text-xs sm:text-sm leading-relaxed transition-colors ${
                          activeStep === index ? "text-muted-foreground" : "text-muted-foreground/70"
                        }`}
                      >
                        {step.description}
                      </p>
                    </div>
                  </div>

                  {/* Progress bar */}
                  {activeStep === index && (
                    <div className="mt-4 ml-13">
                      <div className="h-0.5 bg-border rounded-full overflow-hidden">
                        <div
                          className="h-full bg-cyan-400 rounded-full animate-[progress_5s_linear]"
                          style={{ width: "100%" }}
                        />
                      </div>
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Code display */}
          <div className="lg:sticky lg:top-28">
            <div className="rounded-2xl overflow-hidden bg-card/95 border border-border/80 card-shadow backdrop-blur-xl">
              {/* Window chrome */}
              <div className="px-4 py-3 border-b border-border/60 flex items-center justify-between bg-secondary/40">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/30" />
                  <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/30" />
                  <span className="w-2.5 h-2.5 rounded-full bg-muted-foreground/30" />
                  <span className="text-xs font-mono text-cyan-300 ml-2">
                    {steps[activeStep].filename}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-muted-foreground uppercase">
                  Stage {steps[activeStep].number} / 04
                </span>
              </div>

              {/* Code content */}
              <div className="p-6 font-mono text-xs sm:text-sm min-h-[220px] bg-black/60 overflow-x-auto">
                <pre className="text-muted-foreground leading-relaxed">
                  {steps[activeStep].code.split("\n").map((line, i) => (
                    <div key={`${activeStep}-${i}`} className="flex gap-4">
                      <span className="text-muted-foreground/30 select-none w-4 text-right inline-block">
                        {i + 1}
                      </span>
                      <span
                        dangerouslySetInnerHTML={{
                          __html: highlightCode(line),
                        }}
                      />
                    </div>
                  ))}
                </pre>
              </div>

              {/* Output status */}
              <div className="border-t border-border/60 p-3.5 bg-secondary/30 font-mono text-xs flex items-center justify-between">
                <div className="flex items-center gap-2 text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Pipeline Stage Active</span>
                </div>
                <span className="text-[10px] text-muted-foreground">Deterministic Execution</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes progress {
          from {
            width: 0%;
          }
          to {
            width: 100%;
          }
        }
      `}</style>
    </section>
  );
}

function highlightCode(line: string): string {
  return line
    .replace(/(def|return|for|in|if)\b/g, '<span class="text-indigo-400 font-semibold">$1</span>')
    .replace(/(self|re|query|analysis|schema|llm)/g, '<span class="text-foreground">$1</span>')
    .replace(/(\.\w+)/g, '<span class="text-cyan-400">$1</span>')
    .replace(/('.*?'|".*?")/g, '<span class="text-emerald-300">$1</span>')
    .replace(/(#.*$)/g, '<span class="text-muted-foreground/60 italic">$1</span>');
}
