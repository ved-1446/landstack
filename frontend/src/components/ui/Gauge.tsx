import { useReducedMotion } from "framer-motion";
import { gsap } from "gsap";
import { useEffect, useRef } from "react";
import { cn } from "../../lib/cn";
import type { Band } from "../../types";

const RADIUS = 80;
const ARC_LENGTH = Math.PI * RADIUS;

// the gauge arc, by band, drawn in the "ink" shades so it reads on the cream sheet
const ARC_CLASS: Record<Band, string> = {
  green: "stroke-risk-green-ink",
  amber: "stroke-risk-amber-ink",
  red: "stroke-gauge-red",
};

/** A point on the half circle for a score from 0 (left end) to 100 (right end). */
function pointAt(value: number, radius: number) {
  const angle = (Math.PI * value) / 100;
  return { x: 100 - radius * Math.cos(angle), y: 100 - radius * Math.sin(angle) };
}

interface GaugeProps {
  score: number;
  band: Band;
  className?: string;
}

/** A semicircle gauge on the cream sheet. GSAP fills the arc and counts the score up (about 900 ms). */
export function Gauge({ score, band, className }: GaugeProps) {
  const arc = useRef<SVGPathElement>(null);
  const number = useRef<HTMLSpanElement>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const path = arc.current;
    const text = number.current;
    if (!path || !text) return;
    const draw = (value: number) => {
      path.style.strokeDashoffset = String(ARC_LENGTH * (1 - value / 100));
      text.textContent = String(Math.round(value));
    };
    if (reduceMotion) {
      draw(score);
      return;
    }
    const state = { value: 0 };
    draw(0);
    const tween = gsap.to(state, { value: score, duration: 0.9, ease: "power2.out", onUpdate: () => draw(state.value) });
    return () => {
      tween.kill();
    };
  }, [score, reduceMotion]);

  const ticks = [25, 60].map((value) => ({
    value,
    from: pointAt(value, RADIUS - 11),
    to: pointAt(value, RADIUS + 11),
    label: pointAt(value, RADIUS + 22),
  }));
  const description = `Risk score ${score} out of 100, ${band} band`;

  return (
    <div className={cn("relative mx-auto w-full max-w-72", className)}>
      <svg viewBox="0 -14 200 126" className="block w-full" role="img" aria-label={description}>
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" strokeWidth={12} strokeLinecap="round" className="stroke-line-on-cream" />
        <path
          ref={arc}
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          strokeWidth={12}
          strokeLinecap="round"
          strokeDasharray={ARC_LENGTH}
          strokeDashoffset={ARC_LENGTH}
          className={ARC_CLASS[band]}
        />
        {ticks.map((tick) => (
          <g key={tick.value}>
            <line x1={tick.from.x} y1={tick.from.y} x2={tick.to.x} y2={tick.to.y} strokeWidth={1.5} className="stroke-faint-on-cream" />
            <text x={tick.label.x} y={tick.label.y} textAnchor="middle" dominantBaseline="middle" className="fill-faint-on-cream font-mono text-11">
              {tick.value}
            </text>
          </g>
        ))}
      </svg>
      <div className="absolute inset-x-0 bottom-0 flex flex-col items-center">
        <span ref={number} aria-hidden="true" className="font-serif text-58 text-ink">
          {score}
        </span>
        <span aria-hidden="true" className="font-mono text-12 text-muted-on-cream">
          / 100
        </span>
        <span className="sr-only">{description}</span>
      </div>
    </div>
  );
}
