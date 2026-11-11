import { cn } from "../../lib/cn";
import { useCountUp } from "../../lib/useCountUp";
import type { Band } from "../../types";

const RADIUS = 80;
const ARC_LENGTH = Math.PI * RADIUS;

// the arc colour, by band: the dark "ink" shades on cream, the lighter tints on dark
const ARC_CLASS = {
  cream: { green: "stroke-risk-green-ink", amber: "stroke-risk-amber-ink", red: "stroke-gauge-red" },
  navy: { green: "stroke-risk-green-tint", amber: "stroke-risk-amber-tint", red: "stroke-risk-red-tint" },
} as const;

/** A point on the half circle for a score from 0 (left end) to 100 (right end). */
function pointAt(value: number, radius: number) {
  const angle = (Math.PI * value) / 100;
  return { x: 100 - radius * Math.cos(angle), y: 100 - radius * Math.sin(angle) };
}

interface ScoreGaugeProps {
  score: number;
  band: Band;
  /** which surface it sits on */
  on?: "cream" | "navy";
  className?: string;
}

/** A semicircle gauge. The arc sweeps with a CSS animation and the number counts up (about 900 ms); reduced motion shows the end state. */
export function ScoreGauge({ score, band, on = "cream", className }: ScoreGaugeProps) {
  const shown = useCountUp(score);
  const cream = on === "cream";
  const ticks = [25, 60].map((value) => ({ value, from: pointAt(value, RADIUS - 11), to: pointAt(value, RADIUS + 11), label: pointAt(value, RADIUS + 22) }));
  const description = `Risk score ${score} out of 100, ${band} band`;

  return (
    <div className={cn("relative mx-auto w-full max-w-72", className)}>
      <svg viewBox="0 -14 200 126" className="block w-full" role="img" aria-label={description}>
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" strokeWidth={12} strokeLinecap="round" className={cream ? "stroke-line-on-cream" : "stroke-line-on-navy"} />
        <path
          key={score}
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          strokeWidth={12}
          strokeLinecap="round"
          strokeDasharray={ARC_LENGTH}
          strokeDashoffset={ARC_LENGTH * (1 - score / 100)}
          style={{ ["--arc-length" as string]: ARC_LENGTH }}
          className={cn("gauge-sweep", ARC_CLASS[on][band])}
        />
        {ticks.map((tick) => (
          <g key={tick.value}>
            <line x1={tick.from.x} y1={tick.from.y} x2={tick.to.x} y2={tick.to.y} strokeWidth={1.5} className={cream ? "stroke-faint-on-cream" : "stroke-faint-on-navy"} />
            <text x={tick.label.x} y={tick.label.y} textAnchor="middle" dominantBaseline="middle" className={cn("font-mono text-11", cream ? "fill-faint-on-cream" : "fill-faint-on-navy")}>
              {tick.value}
            </text>
          </g>
        ))}
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
        <span aria-hidden="true" className={cn("font-serif text-58", cream ? "text-ink" : "text-cream")}>
          {shown}
        </span>
        <span aria-hidden="true" className={cn("font-mono text-12", cream ? "text-muted-on-cream" : "text-muted-on-navy")}>
          / 100
        </span>
        <span className="sr-only">{description}</span>
      </div>
    </div>
  );
}
