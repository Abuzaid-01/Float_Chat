"use client";

import { useEffect, useRef } from "react";
import { prefersReducedMotion } from "@/lib/animation";

type Particle = {
  x: number;
  y: number;
  /** 0.2 (far) → 1 (near). Near particles are larger and move more on scroll. */
  z: number;
  phase: number;
  sink: number;
};

function makeParticles(count: number): Particle[] {
  return Array.from({ length: count }, () => ({
    x: Math.random(),
    y: Math.random(),
    z: 0.2 + Math.random() * 0.8,
    phase: Math.random() * Math.PI * 2,
    sink: 4 + Math.random() * 9,
  }));
}

/**
 * The water column behind the page. Scrolling is treated as a dive: the
 * sunlit surface layers fade out, light shafts thin, and the drifting marine
 * snow starts to glow as the page gets deeper.
 */
export function OceanBackdrop() {
  const root = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const el = root.current;
    const cv = canvas.current;
    const ctx = cv?.getContext("2d");
    if (!el || !cv || !ctx) return;

    const still = prefersReducedMotion();
    const particles = makeParticles(window.innerWidth < 700 ? 42 : 90);
    let width = 0;
    let height = 0;
    let depth = 0;
    let scrollY = 0;
    let raf = 0;

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      cv.width = width * dpr;
      cv.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const readScroll = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      scrollY = window.scrollY;
      depth = max > 0 ? Math.min(1, Math.max(0, scrollY / max)) : 0;
      el.style.setProperty("--depth", depth.toFixed(4));
    };

    const draw = (time: number) => {
      const seconds = time / 1000;
      ctx.clearRect(0, 0, width, height);
      for (const particle of particles) {
        const sway = Math.sin(seconds * 0.35 + particle.phase) * 14 * particle.z;
        const travel = particle.y * height + seconds * particle.sink * particle.z - scrollY * particle.z * 0.32;
        const y = ((travel % height) + height) % height;
        const x = particle.x * width + sway;
        const radius = 0.5 + particle.z * 1.5;
        // Deeper water: brighter, with a slow bioluminescent pulse.
        const pulse = 0.65 + 0.35 * Math.sin(seconds * 0.9 + particle.phase * 3);
        const alpha = (0.1 + depth * 0.34 * pulse) * (0.35 + particle.z * 0.65);
        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${Math.round(190 - depth * 60)}, 240, 236, ${alpha.toFixed(3)})`;
        ctx.fill();
        if (particle.z > 0.82 && depth > 0.3) {
          ctx.beginPath();
          ctx.arc(x, y, radius * 4, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(120, 240, 228, ${(alpha * 0.12).toFixed(3)})`;
          ctx.fill();
        }
      }
    };

    const loop = (time: number) => {
      draw(time);
      raf = requestAnimationFrame(loop);
    };

    const start = () => {
      if (!raf && !still && !document.hidden) raf = requestAnimationFrame(loop);
    };
    const stop = () => {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
    };

    const onScroll = () => {
      readScroll();
      if (still) draw(0);
    };
    const onResize = () => {
      resize();
      onScroll();
    };
    const onVisibility = () => (document.hidden ? stop() : start());

    resize();
    readScroll();
    if (still) draw(0);
    else start();

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return (
    <div ref={root} className="obs-backdrop" aria-hidden="true">
      <div className="obs-backdrop__layer obs-backdrop__layer--twilight" />
      <div className="obs-backdrop__layer obs-backdrop__layer--sunlight" />
      <div className="obs-rays">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <canvas ref={canvas} className="obs-backdrop__snow" />
      <div className="obs-backdrop__grain" />
    </div>
  );
}
