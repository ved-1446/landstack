import { cva } from "class-variance-authority";
import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export type ChipTone = "neutral" | "green" | "amber" | "red" | "ml" | "sim";
export type ChipSurface = "navy" | "cream";

// Risk is shown by a coloured dot and border PLUS the words in the chip, never by colour alone.
// Text is cream on navy and ink on cream, so it always passes contrast (red text on navy-800 would not).
const BORDER: Record<ChipSurface, Record<ChipTone, string>> = {
  navy: {
    neutral: "border-line-on-navy",
    green: "border-risk-green",
    amber: "border-risk-amber",
    red: "border-risk-red",
    ml: "border-mist",
    sim: "border-sim",
  },
  cream: {
    neutral: "border-line-on-cream",
    green: "border-risk-green-ink",
    amber: "border-risk-amber-ink",
    red: "border-risk-red-ink",
    ml: "border-faint-on-cream",
    sim: "border-sim-ink",
  },
};
const DOT: Record<ChipSurface, Record<ChipTone, string>> = {
  navy: {
    neutral: "bg-faint-on-navy",
    green: "bg-risk-green",
    amber: "bg-risk-amber",
    red: "bg-risk-red",
    ml: "bg-mist",
    sim: "bg-sim",
  },
  cream: {
    neutral: "bg-faint-on-cream",
    green: "bg-risk-green-ink",
    amber: "bg-risk-amber-ink",
    red: "bg-risk-red-ink",
    ml: "bg-faint-on-cream",
    sim: "bg-sim-ink",
  },
};

const chip = cva("inline-flex items-center gap-2 rounded-pill border px-3 py-1 font-mono text-11 font-medium tracking-wider", {
  variants: {
    surface: { navy: "text-cream", cream: "text-ink" },
    interactive: { true: "min-h-8 transition-colors duration-150 ease-out", false: "" },
  },
  defaultVariants: { surface: "navy", interactive: false },
});

interface ChipProps {
  tone?: ChipTone;
  surface?: ChipSurface;
  children: ReactNode;
  /** a number shown after the label (for example a count) */
  count?: number;
  className?: string;
  /** makes the chip a toggle button */
  onClick?: () => void;
  pressed?: boolean;
  /** a plain-words name for assistive technology when the visible label is not enough */
  label?: string;
}

export function Chip({ tone = "neutral", surface = "navy", children, count, className, onClick, pressed, label }: ChipProps) {
  const body = (
    <>
      <span
        aria-hidden="true"
        className={cn(
          "size-2 shrink-0 rounded-pill",
          DOT[surface][tone],
          onClick && pressed === false && "bg-transparent ring-1 ring-current",
        )}
      />
      <span>{children}</span>
      {count !== undefined && <span className="font-medium opacity-80">{count}</span>}
    </>
  );
  const classes = cn(
    chip({ surface, interactive: Boolean(onClick) }),
    BORDER[surface][tone],
    onClick && (pressed ? "bg-navy-800" : "opacity-70 hover:opacity-100"),
    className,
  );
  if (onClick) {
    return (
      <button type="button" className={classes} onClick={onClick} aria-pressed={pressed} aria-label={label}>
        {body}
      </button>
    );
  }
  return (
    <span className={classes} aria-label={label}>
      {body}
    </span>
  );
}
