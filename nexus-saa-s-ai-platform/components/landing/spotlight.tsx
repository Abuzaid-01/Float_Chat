"use client";

import { useEffect, useRef } from "react";

/**
 * A soft radial glow that follows the cursor across the page.
 * rAF-throttled. Hidden on touch devices and for reduced-motion users.
 */
export function Spotlight() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof window === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (!window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;

    let raf = 0;

    const onMove = (e: MouseEvent) => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        el.style.background = `radial-gradient(560px circle at ${e.clientX}px ${e.clientY}px, oklch(0.65 0.15 190 / 0.08), transparent 65%)`;
      });
    };

    window.addEventListener("mousemove", onMove, { passive: true });

    return () => {
      window.removeEventListener("mousemove", onMove);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div
      ref={ref}
      className="fixed inset-0 z-[5] pointer-events-none hidden md:block"
      aria-hidden="true"
    />
  );
}