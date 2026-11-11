import { LayoutGrid } from "lucide-react";
import { useMemo } from "react";
import { ErrorState } from "../../components/ErrorState";
import { Chip, GlassCard, EmptyState, Popover, Skeleton } from "../../components/ui";
import { BAND_LABEL } from "../../constants";
import { cn } from "../../lib/cn";
import type { PlotFeature } from "../../types";

interface MyPlotsProps {
  open: boolean;
  onClose: () => void;
  plots: PlotFeature[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  selected: string | null;
  onPick: (ulpin: string) => void;
}

/** "My plots" (citizens): a bento grid with one tile per owned plot. The highest-risk plot gets the big tile. */
export function MyPlots({ open, onClose, plots, loading, error, onRetry, selected, onPick }: MyPlotsProps) {
  const tiles = useMemo(
    () => [...(plots ?? [])].sort((a, b) => b.properties.score - a.properties.score || a.properties.ulpin.localeCompare(b.properties.ulpin)),
    [plots],
  );

  return (
    <Popover open={open} onClose={onClose} title="My plots" className="md:w-(--bento-width)">
      {error ? (
        <ErrorState message={error} onRetry={onRetry} />
      ) : loading && !plots ? (
        <div className="mt-3 grid grid-cols-2 gap-2" aria-label="Loading your plots">
          <Skeleton className="col-span-2 h-32" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : tiles.length === 0 ? (
        <EmptyState icon={LayoutGrid} title="No plots yet" description="You do not own any plots in this demo, or none match the filters." />
      ) : (
        <>
          <p className="mt-1 text-13 text-muted-on-navy">
            {tiles.length} {tiles.length === 1 ? "plot" : "plots"}. Select one to open its passport.
          </p>
          <ul className="mt-3 grid grid-cols-2 gap-2">
            {tiles.map((f, index) => (
              <li key={f.properties.ulpin} className={cn(index === 0 && tiles.length > 1 && "col-span-2")}>
                <GlassCard padding="none" className={cn("h-full transition-[background-color,transform] duration-150 ease-out hover:-translate-y-0.5 hover:bg-glass-fill-strong motion-reduce:transform-none", selected === f.properties.ulpin && "border-cream")}>
                  <button type="button" onClick={() => onPick(f.properties.ulpin)} className="flex h-full w-full flex-col items-start gap-3 rounded-card p-4 text-left">
                    <span className="font-mono text-12 text-muted-on-navy">{f.properties.ulpin}</span>
                    <span className={cn("font-serif text-cream", index === 0 ? "text-58" : "text-34")}>{f.properties.score}</span>
                    <span className="flex w-full flex-wrap items-center justify-between gap-2">
                      <Chip tone={f.properties.band}>{BAND_LABEL[f.properties.band]}</Chip>
                      <span className="text-12 text-muted-on-navy">{f.properties.village}</span>
                    </span>
                  </button>
                </GlassCard>
              </li>
            ))}
          </ul>
        </>
      )}
    </Popover>
  );
}
