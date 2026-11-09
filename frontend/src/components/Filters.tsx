import { ALL_BANDS, BAND_COLOR, BAND_LABEL, prettyType } from "../constants";
import type { Band, ConflictType, ConflictTypeInfo } from "../types";

export interface FilterState {
  bands: Set<Band>;
  village: string; // "" = all villages
  conflictType: ConflictType | ""; // "" = all conflict types
}

interface Props {
  filters: FilterState;
  villages: string[];
  conflictTypes: ConflictTypeInfo[];
  shown: number | null;
  loading: boolean;
  onChange: (next: FilterState) => void;
}

export default function Filters({ filters, villages, conflictTypes, shown, loading, onChange }: Props) {
  function toggleBand(band: Band) {
    const bands = new Set(filters.bands);
    if (bands.has(band)) bands.delete(band);
    else bands.add(band);
    onChange({ ...filters, bands });
  }

  return (
    <div className="flex flex-wrap items-center gap-4 px-4 py-2 text-sm">
      <div className="flex items-center gap-1" role="group" aria-label="Band">
        {ALL_BANDS.map((band) => {
          const on = filters.bands.has(band);
          return (
            <button key={band} type="button" aria-pressed={on} onClick={() => toggleBand(band)}
                    className={`flex items-center gap-1 rounded border px-2 py-1 ${
                      on ? "border-gray-700 bg-white font-medium" : "border-gray-300 bg-gray-100 text-gray-500"}`}>
              <span className="inline-block h-3 w-3 rounded-sm border border-gray-500"
                    style={{ backgroundColor: on ? BAND_COLOR[band] : "transparent" }} />
              {BAND_LABEL[band]}
            </button>
          );
        })}
      </div>

      <label className="flex items-center gap-1">
        Village
        <select value={filters.village} onChange={(e) => onChange({ ...filters, village: e.target.value })}
                className="rounded border border-gray-300 px-2 py-1">
          <option value="">All villages</option>
          {villages.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>

      <label className="flex items-center gap-1">
        Conflict
        <select value={filters.conflictType}
                onChange={(e) => onChange({ ...filters, conflictType: e.target.value as ConflictType | "" })}
                className="rounded border border-gray-300 px-2 py-1">
          <option value="">All conflict types</option>
          {conflictTypes.map((t) => <option key={t.type} value={t.type}>{prettyType(t.type)}</option>)}
        </select>
      </label>

      <span className="text-gray-600" aria-live="polite">
        {loading ? "Loading plots…" : shown === null ? "" : `Showing ${shown} plots`}
      </span>
    </div>
  );
}
