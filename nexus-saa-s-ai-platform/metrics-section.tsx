"use client";

import { useEffect, useState, useRef } from "react";
import { Compass, Globe, Waves, Navigation2 } from "lucide-react";
import { Reveal } from "./reveal";

function AnimatedCounter({
  end,
  suffix = "",
  prefix = "",
}: {
  end: number;
  suffix?: string;
  prefix?: string;
}) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          setHasAnimated(true);
          const duration = 2000;
          const startTime = performance.now();

          const animate = (currentTime: number) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(eased * end));

            if (progress < 1) {
              requestAnimationFrame(animate);
            }
          };

          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.3 }
    );

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [end, hasAnimated]);

  return (
    <div ref={ref} className="font-mono text-3xl sm:text-5xl font-bold tracking-tight text-foreground">
      {prefix}
      {count.toLocaleString()}
      {suffix}
    </div>
  );
}

const metrics = [
  {
    value: 714,
    suffix: "",
    label: "Active ARGO Floats",
    sublabel: "Indexed in FAISS & BM25",
  },
  {
    value: 1240000,
    suffix: "+",
    label: "Ocean Measurements",
    sublabel: "Live in Neon PostgreSQL",
  },
  {
    value: 57,
    suffix: "%",
    label: "Token Window Savings",
    sublabel: "Dynamic Schema Pruning",
  },
  {
    value: 99,
    suffix: ".4%",
    label: "SQL Validation Rate",
    sublabel: "Zero SQL injection risk",
  },
];

const regions = [
  {
    name: "Arabian Sea",
    lat: "5°N to 30°N",
    lon: "40°E to 80°E",
    depth: "Up to 2,000 dbar",
    primary: "High Salinity Water Mass (ASW)",
  },
  {
    name: "Bay of Bengal",
    lat: "5°N to 25°N",
    lon: "80°E to 100°E",
    depth: "Up to 2,000 dbar",
    primary: "Low Salinity River Runoff Layer",
  },
  {
    name: "Equatorial Indian Ocean",
    lat: "10°S to 5°N",
    lon: "40°E to 100°E",
    depth: "Up to 2,000 dbar",
    primary: "Wyrtki Jets & Thermocline Dynamics",
  },
  {
    name: "Southern Indian Ocean",
    lat: "50°S to 10°S",
    lon: "20°E to 120°E",
    depth: "Up to 2,000 dbar",
    primary: "Antarctic Intermediate Water (AAIW)",
  },
];

export function MetricsSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

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
    <section id="metrics" ref={sectionRef} className="relative py-28 overflow-hidden bg-secondary/20">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <Reveal>
          <div className="max-w-3xl mb-16">
            <p className="text-xs font-mono text-cyan-400 mb-2 uppercase tracking-widest">// DATASET COVERAGE</p>
            <h2
              className={`text-3xl lg:text-5xl font-bold tracking-tight mb-4 transition-all duration-700 ${
                isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
              }`}
            >
              Indian Ocean Geographic Extent
            </h2>
            <p className="text-muted-foreground text-sm sm:text-base">
              Comprehensive spatial and temporal indexing calibrated for Indian Ocean basin oceanography.
            </p>
          </div>
        </Reveal>

        {/* Counter Grid */}
        <Reveal delay={100}>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
            {metrics.map((metric, idx) => (
              <div
                key={idx}
                className="p-6 rounded-2xl bg-card/80 border border-border/60 card-shadow backdrop-blur-md hover:border-primary/40 transition-colors duration-300"
              >
                <AnimatedCounter end={metric.value} suffix={metric.suffix} />
                <div className="text-sm font-semibold text-foreground mt-2">{metric.label}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{metric.sublabel}</div>
              </div>
            ))}
          </div>
        </Reveal>

        {/* Geographic Region Table */}
        <Reveal delay={200}>
        <div className="rounded-2xl border border-border/80 overflow-hidden bg-card/90 card-shadow backdrop-blur-xl">
          <div className="px-6 py-4 border-b border-border/60 bg-secondary/40 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-cyan-400" />
              <span className="font-mono text-xs font-semibold text-foreground uppercase tracking-wider">
                Automated Region Classification Boundaries
              </span>
            </div>
            <span className="font-mono text-xs text-muted-foreground">Spatial Lat/Lon Indices</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-xs">
              <thead className="bg-secondary/20 text-muted-foreground uppercase text-[10px]">
                <tr>
                  <th className="px-6 py-3 font-semibold">Ocean Region</th>
                  <th className="px-6 py-3 font-semibold">Latitude Range</th>
                  <th className="px-6 py-3 font-semibold">Longitude Range</th>
                  <th className="px-6 py-3 font-semibold">Max Depth</th>
                  <th className="px-6 py-3 font-semibold">Oceanographic Feature</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40">
                {regions.map((reg, idx) => (
                  <tr key={idx} className="hover:bg-secondary/30 transition-colors">
                    <td className="px-6 py-3.5 font-medium text-foreground">{reg.name}</td>
                    <td className="px-6 py-3.5 text-cyan-300">{reg.lat}</td>
                    <td className="px-6 py-3.5 text-cyan-300">{reg.lon}</td>
                    <td className="px-6 py-3.5 text-muted-foreground">{reg.depth}</td>
                    <td className="px-6 py-3.5 text-foreground/80">{reg.primary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        </Reveal>
      </div>
    </section>
  );
}
