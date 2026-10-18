"use client";

/**
 * Infinite horizontal marquee strip. Content is doubled and the CSS animation
 * translates -50% for a seamless loop. Stops for reduced-motion users.
 */
export function Marquee({
  items,
  className = "",
}: {
  items: string[];
  className?: string;
}) {
  const doubled = [...items, ...items];

  return (
    <div
      className={`relative overflow-hidden border-y border-border/60 bg-secondary/20 py-4 select-none ${className}`}
      aria-hidden="true"
    >
      <div className="flex w-max whitespace-nowrap animate-marquee motion-reduce:animate-none">
        {doubled.map((item, i) => (
          <span
            key={i}
            className="mx-5 flex items-center gap-3 font-mono text-xs sm:text-sm tracking-[0.18em] text-muted-foreground uppercase"
          >
            <span className="text-cyan-400/70">▸</span>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}