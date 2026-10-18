"use client";

import { useScrollProgress } from "@/lib/animation";

export function ScrollProgress() {
  const progress = useScrollProgress();

  return (
    <div className="fixed top-0 left-0 right-0 z-[70] h-[3px] pointer-events-none" aria-hidden="true">
      <div
        className="h-full bg-gradient-to-r from-cyan-400 via-primary to-blue-400 shadow-[0_0_12px_oklch(0.7_0.18_170/0.6)] transition-[width] duration-150 ease-out"
        style={{ width: `${progress * 100}%` }}
      />
    </div>
  );
}