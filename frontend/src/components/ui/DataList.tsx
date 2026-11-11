import type { ReactNode } from "react";
import { cn } from "../../lib/cn";

export interface DataRow {
  key: string;
  /** the main text of the row */
  primary: ReactNode;
  secondary?: ReactNode;
  /** shown on the right (a chip, a number) */
  trailing?: ReactNode;
  onClick?: () => void;
}

/** A list of rows (not a table): easy to read on a phone. A row with onClick is a real button. */
export function DataList({ rows, label, className }: { rows: DataRow[]; label: string; className?: string }) {
  return (
    <ul aria-label={label} className={cn("divide-y divide-glass-border", className)}>
      {rows.map((row) => {
        const body = (
          <>
            <div className="min-w-0 flex-1">
              <div className="truncate text-14 text-cream">{row.primary}</div>
              {row.secondary && <div className="truncate text-13 text-muted-on-navy">{row.secondary}</div>}
            </div>
            {row.trailing && <div className="shrink-0">{row.trailing}</div>}
          </>
        );
        return (
          <li key={row.key}>
            {row.onClick ? (
              <button type="button" onClick={row.onClick} className="flex w-full items-center gap-3 rounded-control px-2 py-3 text-left transition-colors duration-150 hover:bg-glass-fill">
                {body}
              </button>
            ) : (
              <div className="flex items-center gap-3 px-2 py-3">{body}</div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
