import { cn } from "../../lib/cn";

export interface BarItem {
  label: string;
  value: number;
  /** a Tailwind background class from the tokens, for example "bg-risk-red"; defaults to coral */
  barClass?: string;
}

/** A list of labelled horizontal bars. The number is always written, so the bar is never the only signal. */
export function BarList({ items, className }: { items: BarItem[]; className?: string }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <ul className={cn("space-y-3", className)}>
      {items.map((item) => (
        <li key={item.label}>
          <div className="flex items-baseline justify-between gap-3 text-13">
            <span className="text-cream">{item.label}</span>
            <span className="font-mono text-muted-on-navy">{item.value}</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-pill bg-glass-fill-strong" aria-hidden="true">
            <div className={cn("h-full rounded-pill", item.barClass ?? "bg-coral")} style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
