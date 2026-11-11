import { CircleCheck, ShieldAlert, TriangleAlert } from "lucide-react";
import { cn } from "../../lib/cn";
import type { Band } from "../../types";

const WORDS: Record<Band, string> = { green: "Low risk · green", amber: "Watch · amber", red: "High risk · red" };
const ICON = { green: CircleCheck, amber: TriangleAlert, red: ShieldAlert } as const;

// text colours: the light "tint" shades on dark surfaces, the dark "ink" shades on cream
const TEXT = {
  navy: { green: "text-risk-green-tint", amber: "text-risk-amber-tint", red: "text-risk-red-tint" },
  cream: { green: "text-risk-green-ink", amber: "text-risk-amber-ink", red: "text-risk-red-ink" },
} as const;
const BORDER = { green: "border-risk-green", amber: "border-risk-amber", red: "border-risk-red" } as const;

interface BandChipProps {
  band: Band;
  surface?: "navy" | "cream";
  className?: string;
}

/** A risk band as an icon plus words, never colour alone. Coral is never used for risk. */
export function BandChip({ band, surface = "navy", className }: BandChipProps) {
  const Icon = ICON[band];
  return (
    <span className={cn("inline-flex items-center gap-2 rounded-pill border px-3 py-1 font-mono text-11 font-medium tracking-wider", BORDER[band], TEXT[surface][band], className)}>
      <Icon className="size-4" aria-hidden="true" />
      {WORDS[band].toUpperCase()}
    </span>
  );
}
