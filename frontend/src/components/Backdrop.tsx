import type { ReactNode } from "react";
import { cn } from "../lib/cn";

export type Identity = "visitor" | "citizen" | "officer" | "admin";

/**
 * The light static background used on every page except the landing hero and the login (those run the live Flow Field):
 * a gradient, a dot grid and a soft glow in the role's tint. No WebGL and no animation, so it costs almost nothing.
 */
export function StaticLayer({ identity, children, className }: { identity: Identity; children: ReactNode; className?: string }) {
  return (
    <div className={cn("static-layer relative min-h-dvh", `static-layer--${identity}`, className)}>
      <div aria-hidden="true" className="pattern-dots pointer-events-none absolute inset-0 opacity-60" />
      {children}
    </div>
  );
}

/** Topographic contour lines (SVG): rings that look like the height lines on a hiking map. Decoration only. */
export function ContourLines({ className }: { className?: string }) {
  const rings = [18, 34, 52, 72, 94, 118];
  return (
    <svg aria-hidden="true" viewBox="0 0 400 300" preserveAspectRatio="xMidYMid slice" className={cn("pointer-events-none absolute inset-0 size-full stroke-forest-line", className)} fill="none" strokeWidth={1}>
      {rings.map((r, i) => (
        <ellipse key={r} cx={150 + i * 4} cy={150 - i * 2} rx={r * 1.5} ry={r} transform={`rotate(${-12 + i * 3} 200 150)`} opacity={0.9 - i * 0.1} />
      ))}
      {rings.map((r, i) => (
        <ellipse key={`b${r}`} cx={310} cy={90} rx={r * 0.7} ry={r * 0.45} transform={`rotate(${20 - i * 4} 310 90)`} opacity={0.7 - i * 0.1} />
      ))}
    </svg>
  );
}

/** A soft vertical stripe glow: thin vertical lines that fade at the top and bottom. Decoration only. */
export function StripeGlow({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("pattern-stripes pointer-events-none absolute inset-0", className)} />;
}
