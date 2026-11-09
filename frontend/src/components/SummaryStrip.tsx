import { ALL_BANDS, BAND_COLOR, BAND_LABEL, prettyType } from "../constants";
import type { ConflictTypeInfo, Summary } from "../types";
import { ErrorMessage, Spinner } from "./Feedback";

interface Props {
  summary: Summary | null;
  conflictTypes: ConflictTypeInfo[] | null;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
}

export default function SummaryStrip({ summary, conflictTypes, loading, error, onRetry }: Props) {
  if (error) return <div className="p-2"><ErrorMessage message={error} onRetry={onRetry} /></div>;
  if (loading || !summary || !conflictTypes) {
    return <div className="p-3"><Spinner label="Loading summary…" /></div>;
  }

  return (
    <div className="flex flex-wrap items-stretch gap-x-6 gap-y-2 px-4 py-2">
      <div>
        <div className="text-xs uppercase text-gray-500">Plots</div>
        <div className="text-2xl font-semibold">{summary.total_plots}</div>
      </div>

      <div className="flex gap-2">
        {ALL_BANDS.map((band) => (
          <div key={band} className="rounded border border-gray-300 px-3 py-1">
            <div className="flex items-center gap-1 text-xs uppercase text-gray-500">
              <span className="inline-block h-3 w-3 rounded-sm border border-gray-500"
                    style={{ backgroundColor: BAND_COLOR[band] }} />
              {BAND_LABEL[band]}
            </div>
            <div className="text-xl font-semibold">{summary.plots_per_band[band]}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        {conflictTypes.map((t) => (
          <div key={t.type} title={t.description}
               className="w-44 rounded border border-gray-200 bg-gray-50 px-2 py-1">
            <div className="flex justify-between text-sm">
              <span className="font-medium">{prettyType(t.type)}</span>
              <span className="font-semibold">{summary.findings_per_type[t.type]}</span>
            </div>
            <div className="text-[11px] leading-tight text-gray-500">{t.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
