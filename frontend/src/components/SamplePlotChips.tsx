import { SAMPLE_PLOTS } from "../lib/samplePlots";
import { BandChip } from "./ui";

/** "Not sure what to type?" example chips: the plot id in mono type and the band as icon plus word. A click only calls onPick. */
export function SamplePlotChips({ onPick, disabled, label = "Not sure what to type? Try one of these" }: { onPick: (ulpin: string) => void; disabled?: boolean; label?: string }) {
  return (
    <div className="mt-4">
      <p id="sample-plots-label" className="text-13 text-muted-on-navy">
        {label}
      </p>
      <ul aria-labelledby="sample-plots-label" className="mt-2 flex flex-wrap gap-2">
        {SAMPLE_PLOTS.map((sample) => (
          <li key={sample.ulpin}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(sample.ulpin)}
              className="lift flex items-center gap-3 rounded-pill border border-glass-border bg-glass-fill px-3 py-1.5 hover:bg-glass-fill-strong disabled:opacity-60"
            >
              <span className="font-mono text-13 text-cream">{sample.ulpin}</span>
              <BandChip band={sample.band} className="px-2 py-0.5" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
