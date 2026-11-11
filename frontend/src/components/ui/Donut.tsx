import { cn } from "../../lib/cn";

export interface DonutSlice {
  label: string;
  value: number;
  /** a Tailwind stroke class from the tokens, for example "stroke-risk-green" */
  strokeClass: string;
  /** the matching text colour class for the legend dot, for example "text-risk-green" */
  dotClass: string;
}

const R = 40;
const C = 2 * Math.PI * R;

/** A ring chart with a legend that writes every number, so colour is never the only signal. */
export function Donut({ slices, centre, className }: { slices: DonutSlice[]; centre?: string; className?: string }) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  let offset = 0;
  return (
    <div className={cn("flex flex-wrap items-center gap-6", className)}>
      <div className="relative size-32 shrink-0">
        <svg viewBox="0 0 100 100" className="size-full -rotate-90" role="img" aria-label={slices.map((s) => `${s.label} ${s.value}`).join(", ")}>
          <circle cx={50} cy={50} r={R} fill="none" strokeWidth={14} className="stroke-glass-fill-strong" />
          {total > 0 &&
            slices.map((s) => {
              const length = (s.value / total) * C;
              const node = <circle key={s.label} cx={50} cy={50} r={R} fill="none" strokeWidth={14} strokeDasharray={`${length} ${C - length}`} strokeDashoffset={-offset} className={s.strokeClass} />;
              offset += length;
              return node;
            })}
        </svg>
        {centre && <span aria-hidden="true" className="absolute inset-0 flex items-center justify-center font-serif text-26 text-cream">{centre}</span>}
      </div>
      <ul className="space-y-1 text-13">
        {slices.map((s) => (
          <li key={s.label} className="flex items-center gap-2 text-cream">
            <span aria-hidden="true" className={cn("size-2 rounded-pill bg-current", s.dotClass)} />
            {s.label} <span className="font-mono text-muted-on-navy">{s.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
