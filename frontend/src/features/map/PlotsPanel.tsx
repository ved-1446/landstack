import { FileX } from "lucide-react";
import { useMemo, useState } from "react";
import { ErrorState } from "../../components/ErrorState";
import { Chip, EmptyState, Popover, Skeleton } from "../../components/ui";
import { BAND_LABEL } from "../../constants";
import { cn } from "../../lib/cn";
import type { PlotFeature } from "../../types";

interface PlotsPanelProps {
  open: boolean;
  onClose: () => void;
  plots: PlotFeature[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  selected: string | null;
  onPick: (ulpin: string) => void;
}

/** "Passports" (officers and admins): a searchable list of plots, highest risk first. */
export function PlotsPanel({ open, onClose, plots, loading, error, onRetry, selected, onPick }: PlotsPanelProps) {
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...(plots ?? [])]
      .filter((f) => !q || [f.properties.ulpin, f.properties.village, f.properties.survey_no].some((v) => v.toLowerCase().includes(q)))
      .sort((a, b) => b.properties.score - a.properties.score || a.properties.ulpin.localeCompare(b.properties.ulpin));
  }, [plots, query]);

  return (
    <Popover open={open} onClose={onClose} title="Passports">
      <label htmlFor="passport-filter" className="sr-only">
        Search the list by ULPIN, village or survey number
      </label>
      <input
        id="passport-filter"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Filter by ULPIN, village, survey"
        autoComplete="off"
        className="mb-3 mt-3 h-11 w-full rounded-control border border-line-on-navy bg-navy-950 px-3 font-mono text-13 text-cream placeholder:font-sans placeholder:text-faint-on-navy"
      />
      {error ? (
        <ErrorState message={error} onRetry={onRetry} />
      ) : loading && !plots ? (
        <div className="space-y-2" aria-label="Loading plots">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState icon={FileX} title="No plots found" description={query ? "Nothing matches that search." : "No plots match the current filters."} />
      ) : (
        <ul className="space-y-1">
          {rows.map((f) => (
            <li key={f.properties.ulpin}>
              <button
                type="button"
                onClick={() => onPick(f.properties.ulpin)}
                aria-current={selected === f.properties.ulpin ? "true" : undefined}
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded-control border px-3 py-2 text-left transition-colors duration-150 ease-out",
                  selected === f.properties.ulpin ? "border-cream bg-navy-800" : "border-transparent hover:bg-navy-800",
                )}
              >
                <span className="min-w-0">
                  <span className="block font-mono text-13 text-cream">{f.properties.ulpin}</span>
                  <span className="block truncate text-12 text-muted-on-navy">{f.properties.village}</span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="font-mono text-14 text-cream">{f.properties.score}</span>
                  <Chip tone={f.properties.band}>{BAND_LABEL[f.properties.band]}</Chip>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Popover>
  );
}
