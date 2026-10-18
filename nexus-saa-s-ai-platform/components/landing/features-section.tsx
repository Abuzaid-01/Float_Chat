"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Sparkles, Database, Search, Cpu } from "lucide-react";
import { Reveal } from "./reveal";

// Animated ASCII generators for oceanographic features
const asciiAnimations = {
  hybrid: (frame: number) => {
    const states = ["◉", "◎", "○", "◎"];
    const getChar = (offset: number) => states[(frame + offset) % states.length];
    return `  ┌──FAISS──┐
  │ ${getChar(0)}  ${getChar(1)}  ${getChar(2)} │
  └───┬───┬─┘
      ▼RRF▼
  ┌──BM25───┐
  │ ${getChar(3)}  ${getChar(4)}  ${getChar(5)} │
  └─────────┘`;
  },
  pruning: (frame: number) => {
    const bars = ["██████", "███░░░", "██░░░░", "█░░░░░"];
    const b = bars[frame % bars.length];
    return `  [FULL SCHEMA: 49L]
  ${b} 100%
      │ PRUNER (-57%)
      ▼
  [RELEVANT: 21L]
  ████ 43%`;
  },
  ocean: (frame: number) => {
    const waves = [
      "~ ≈ ~ ≈ ~ ≈ ~",
      "≈ ~ ≈ ~ ≈ ~ ≈",
      "~ ≈ ~ ≈ ~ ≈ ~",
      "≈ ~ ≈ ~ ≈ ~ ≈",
    ];
    const w = waves[frame % waves.length];
    return `  ┌─INDIAN OCEAN─┐
  │ ${w} │
  │ 714 FLOATS   │
  │ 1.2M+ PROFS  │
  └──────────────┘`;
  },
  sensors: (frame: number) => {
    const heights = [
      [1, 2, 3, 2],
      [2, 3, 2, 3],
      [3, 2, 3, 1],
      [2, 1, 2, 2],
    ];
    const h = heights[frame % heights.length];
    const bar = (height: number) => {
      if (height === 3) return "█";
      if (height === 2) return "▄";
      return "▁";
    };
    return `  TEMP SAL  DO  CHL
  │${bar(h[0])}   ${bar(h[1])}   ${bar(h[2])}  ${bar(h[3])}
  │█   █   █   █
  └────────────────`;
  },
};

const features = [
  {
    id: "hybrid",
    title: "Hybrid Search (BM25 + FAISS)",
    description:
      "Fuses 384-d dense vector embeddings with BM25 Okapi exact keyword retrieval via Reciprocal Rank Fusion (RRF). Eliminates misses on exact float IDs.",
    stat: "1,306 Profiles Indexed",
    asciiType: "hybrid" as const,
    icon: Search,
  },
  {
    id: "pruning",
    title: "Dynamic Schema Prompt Pruner",
    description:
      "Smart context-window optimizer that inspects intent to strip out unused sensors and regions, cutting prompt tokens by 57% and eliminating SQL hallucinations.",
    stat: "57% Token Reduction",
    asciiType: "pruning" as const,
    icon: Cpu,
  },
  {
    id: "ocean",
    title: "1.2M+ Real ARGO Float Dataset",
    description:
      "Direct PostgreSQL access to 714 active ocean floats across the Arabian Sea, Bay of Bengal, Equatorial Indian Ocean, and Southern Indian Ocean.",
    stat: "714 Active Floats",
    asciiType: "ocean" as const,
    icon: Database,
  },
  {
    id: "sensors",
    title: "Core & BGC Sensor Analytics",
    description:
      "Comprehensive multi-parameter analytics for in-situ Temperature, Practical Salinity, Pressure, Dissolved Oxygen, Chlorophyll-a, and pH.",
    stat: "6 Sensor Parameters",
    asciiType: "sensors" as const,
    icon: Sparkles,
  },
];

export function FeaturesSection() {
  const [frame, setFrame] = useState(0);
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
  const sectionRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setFrame((prev) => prev + 1);
    }, 450);
    return () => clearInterval(interval);
  }, []);

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

  return (
    <section id="features" ref={sectionRef} className="relative py-28 overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <div className="max-w-3xl mb-16">
          <p className="text-xs font-mono text-cyan-400 mb-2 uppercase tracking-widest">// CAPABILITIES</p>
          <h2
            className={`text-3xl lg:text-5xl font-bold tracking-tight mb-4 transition-all duration-700 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            Built for Precision Ocean Intelligence
          </h2>
          <p className="text-muted-foreground text-sm sm:text-base">
            Engineered from the ground up for high-precision oceanographic retrieval with zero hallucinations.
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-8">
          {features.map((feature, idx) => {
            const Icon = feature.icon;
            const isHovered = hoveredCard === feature.id;
            const asciiArt = asciiAnimations[feature.asciiType](frame);

            return (
              <Reveal key={feature.id} delay={idx * 90}>
              <div
                onMouseEnter={() => setHoveredCard(feature.id)}
                onMouseLeave={() => setHoveredCard(null)}
                className={`relative rounded-2xl border p-7 sm:p-8 transition-all duration-500 bg-card/60 backdrop-blur-xl card-shadow overflow-hidden flex flex-col justify-between ${
                  isHovered ? "border-primary/60 bg-card/90" : "border-border/60 hover:border-border"
                }`}
              >
                <div>
                  {/* Top Bar */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="font-mono text-xs px-3 py-1 rounded-full bg-secondary/80 border border-border/60 text-cyan-300">
                      {feature.stat}
                    </span>
                  </div>

                  {/* Title & Description */}
                  <h3 className="text-xl font-bold text-foreground mb-2.5">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-6">
                    {feature.description}
                  </p>
                </div>

                {/* ASCII Visual Box */}
                <div className="rounded-xl bg-black/70 border border-border/70 p-4 font-mono text-xs text-cyan-400 overflow-hidden flex items-center justify-center min-h-[105px]">
                  <pre className="select-none leading-tight">{asciiArt}</pre>
                </div>
              </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
