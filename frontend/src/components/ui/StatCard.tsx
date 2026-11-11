import type { LucideIcon } from "lucide-react";
import type { CSSProperties } from "react";
import { cn } from "../../lib/cn";
import { useCountUp } from "../../lib/useCountUp";
import { GlassCard } from "./GlassCard";

interface StatCardProps {
  label: string;
  /** a number counts up when it appears; a string is shown as it is */
  value: number | string;
  hint?: string;
  icon?: LucideIcon;
  className?: string;
  style?: CSSProperties;
}

function Counting({ value }: { value: number }) {
  return <>{useCountUp(value).toLocaleString("en-IN")}</>;
}

/** One big number with a label (and an optional hint). */
export function StatCard({ label, value, hint, icon: Icon, className, style }: StatCardProps) {
  return (
    <GlassCard padding="sm" lift className={cn("rise", className)} style={style}>
      <div className="flex items-center justify-between gap-2">
        <p className="font-mono text-11 tracking-widest text-muted-on-navy">{label.toUpperCase()}</p>
        {Icon && <Icon className="size-4 text-muted-on-navy" aria-hidden="true" />}
      </div>
      <p className="mt-2 font-serif text-58 text-cream">{typeof value === "number" ? <Counting value={value} /> : value}</p>
      {hint && <p className="mt-1 text-13 text-muted-on-navy">{hint}</p>}
    </GlassCard>
  );
}
