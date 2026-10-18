"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ArrowRight, Compass, Sparkles } from "lucide-react";
import { AsciiWave } from "./ascii-wave";
import { useParallax } from "@/lib/animation";

export function HeroSection() {
  const [isVisible, setIsVisible] = useState(false);

  // Parallax layers — backgrounds drift at different speeds for depth.
  const gridRef = useParallax<HTMLDivElement>(0.06);
  const waveRef = useParallax<HTMLDivElement>(0.14);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  return (
    <section className="relative min-h-[90vh] flex flex-col justify-center overflow-hidden pt-24 pb-16">
      {/* Subtle grid - slow parallax */}
      <div ref={gridRef} className="absolute inset-0 grid-pattern opacity-40 will-change-transform" />

      {/* ASCII Ocean Wave Background - parallax (background depth) */}
      <div
        ref={waveRef}
        className="absolute inset-0 opacity-25 pointer-events-none overflow-hidden will-change-transform"
      >
        <AsciiWave className="w-full h-full text-cyan-400" />
      </div>

      {/* Floating bioluminescent glow orbs */}
      <div className="absolute -top-32 -left-32 w-[420px] h-[420px] rounded-full bg-cyan-500/10 blur-[120px] animate-float-slow pointer-events-none" />
      <div className="absolute top-1/3 -right-40 w-[380px] h-[380px] rounded-full bg-primary/15 blur-[110px] animate-float pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-[320px] h-[320px] rounded-full bg-blue-500/10 blur-[100px] animate-float-slow pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 py-8 lg:py-16">
        {/* Top Badge */}
        <div
          className={`flex justify-center mb-6 transition-all duration-700 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-primary/30 bg-primary/10 backdrop-blur-md text-xs font-mono text-cyan-300 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-primary animate-spin" style={{ animationDuration: "6s" }} />
            <span>Hybrid RAG Engine (BM25 + FAISS + Dynamic Schema)</span>
          </div>
        </div>

        {/* Main Headline */}
        <div className="text-center max-w-5xl mx-auto mb-8">
          <h1
            className={`text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight leading-[1.05] mb-6 transition-all duration-700 delay-100 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            <span className="text-balance">Conversational Oceanography with</span>{" "}
            <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-indigo-400 bg-clip-text text-transparent text-glow-cyan animate-gradient-x">
              FloatChat AI + RAG
            </span>
          </h1>

          <p
            className={`text-base sm:text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed transition-all duration-700 delay-200 ${
              isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
            }`}
          >
            Ask anything about Indian Ocean, Arabian Sea, and Bay of Bengal ARGO float data in plain English.
            Converts natural language into optimized SQL queries against 1.2M+ live ocean measurements.
          </p>
        </div>

        {/* Action CTAs */}
        <div
          className={`flex flex-col sm:flex-row items-center justify-center gap-3 mb-16 transition-all duration-700 delay-300 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          <a href="#chat">
            <Button
              size="lg"
              className="bg-primary hover:bg-primary/90 text-primary-foreground px-7 h-12 text-sm font-semibold group shadow-xl shadow-primary/25"
            >
              Start Live Query
              <ArrowRight className="w-4 h-4 ml-2 transition-transform group-hover:translate-x-1" />
            </Button>
          </a>
          <a href="#how-it-works">
            <Button
              size="lg"
              variant="outline"
              className="h-12 px-6 text-sm font-medium border-border/80 hover:bg-secondary/60 bg-background/50 backdrop-blur-sm"
            >
              <Compass className="w-4 h-4 mr-2 text-cyan-400" />
              View RAG Architecture
            </Button>
          </a>
        </div>

        {/* Live Metrics Grid */}
        <div
          className={`grid grid-cols-2 lg:grid-cols-4 gap-px bg-border/60 rounded-2xl overflow-hidden card-shadow backdrop-blur-lg border border-border/40 transition-all duration-700 delay-400 ${
            isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
          }`}
        >
          {[
            {
              value: "714",
              label: "Active ARGO Floats",
              detail: "Indian Ocean & Adjacent Seas",
              tag: "NEON DB",
            },
            {
              value: "1.2M+",
              label: "Ocean Profiles",
              detail: "Temp, Salinity, DO, Chlorophyll, pH",
              tag: "POSTGRESQL",
            },
            {
              value: "57%",
              label: "Token Savings",
              detail: "Dynamic Schema Prompt Pruner",
              tag: "OPTIMIZER",
            },
            {
              value: "< 2.5s",
              label: "Query Latency",
              detail: "Sub-second Semantic Cache & RRF",
              tag: "GROQ + FAISS",
            },
          ].map((stat) => (
            <div
              key={stat.label}
              className="p-6 lg:p-7 flex justify-between min-h-[140px] bg-card/80 hover:bg-card transition-colors duration-300 flex-col"
            >
              <div>
                <div className="flex items-baseline gap-2 mb-1">
                  <span className="text-2xl lg:text-3xl font-bold font-mono tracking-tight text-foreground">
                    {stat.value}
                  </span>
                </div>
                <div className="text-sm font-semibold text-foreground/90">{stat.label}</div>
                <div className="text-xs text-muted-foreground mt-1 leading-snug">{stat.detail}</div>
              </div>
              <div className="font-mono text-[10px] text-cyan-400/80 tracking-wider mt-4 uppercase flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                {stat.tag}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}