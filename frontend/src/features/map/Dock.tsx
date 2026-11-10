import { Chip } from "../../components/ui";
import { ALL_BANDS, BAND_LABEL, BAND_RANGE } from "../../constants";
import { cn } from "../../lib/cn";
import type { Band } from "../../types";

interface DockProps {
  shown: number | null;
  counts: Record<Band, number>;
  active: Set<Band>;
  onToggle: (band: Band) => void;
  loading: boolean;
  drawerOpen: boolean;
}

/** The bottom dock: how many plots are showing, and the three band chips (they toggle, and show the score ranges). */
export function Dock({ shown, counts, active, onToggle, loading, drawerOpen }: DockProps) {
  return (
    <div
      className={cn(
        "pointer-events-none fixed bottom-(--dock-bottom) left-(--rail-width) right-0 z-panel flex justify-center px-4 max-md:left-0",
        drawerOpen && "md:right-[calc(var(--drawer-width)+var(--edge))]",
      )}
    >
      <section aria-label="Risk bands" className="glass pointer-events-auto flex flex-wrap items-center justify-center gap-x-4 gap-y-2 rounded-panel px-4 py-3 shadow-2">
        <p aria-live="polite" className="text-13 text-cream">
          {loading && shown === null ? "Loading plots…" : `Showing ${shown ?? 0} plots`}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2" role="group" aria-label="Show or hide plots by band">
          {ALL_BANDS.map((band) => (
            <Chip
              key={band}
              tone={band}
              count={counts[band]}
              pressed={active.has(band)}
              onClick={() => onToggle(band)}
              label={`${BAND_LABEL[band]}, score ${BAND_RANGE[band]}, ${counts[band]} plots. ${active.has(band) ? "Showing" : "Hidden"}.`}
            >
              {BAND_LABEL[band]} {BAND_RANGE[band]}
            </Chip>
          ))}
        </div>
      </section>
    </div>
  );
}
