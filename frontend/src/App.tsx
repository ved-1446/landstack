import { useEffect, useMemo, useState } from "react";
import { getConflictTypes, getPlots, getSummary } from "./api";
import Filters, { type FilterState } from "./components/Filters";
import { ErrorMessage, Spinner } from "./components/Feedback";
import PlotMap from "./components/Map";
import PassportPanel from "./components/PassportPanel";
import SummaryStrip from "./components/SummaryStrip";
import { ALL_BANDS } from "./constants";
import { useFetch } from "./hooks";
import type { PlotCollection, PlotFilters } from "./types";

export default function App() {
  const [filters, setFilters] = useState<FilterState>({
    bands: new Set(ALL_BANDS),
    village: "",
    conflictType: "",
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [villages, setVillages] = useState<string[]>([]);

  // The API takes one band at a time. With exactly one band switched on we ask the API for it;
  // with two bands on we ask for all and hide the third here.
  const apiFilters: PlotFilters = {
    band: filters.bands.size === 1 ? [...filters.bands][0] : undefined,
    village: filters.village || undefined,
    conflict_type: filters.conflictType || undefined,
  };

  const summary = useFetch((signal) => getSummary(signal), []);
  const types = useFetch((signal) => getConflictTypes(signal), []);
  const plots = useFetch(
    (signal) => getPlots(apiFilters, signal),
    [apiFilters.band, apiFilters.village, apiFilters.conflict_type],
    true, // keep the old plots on the map while new ones load
  );

  const visible = useMemo<PlotCollection | null>(() => {
    if (!plots.data) return null;
    return {
      type: "FeatureCollection",
      features: plots.data.features.filter((f) => filters.bands.has(f.properties.band)),
    };
  }, [plots.data, filters.bands]);

  // The API has no list of villages, so remember every village seen in a response.
  useEffect(() => {
    if (!plots.data) return;
    setVillages((old) => {
      const all = new Set(old);
      plots.data!.features.forEach((f) => all.add(f.properties.village));
      return all.size === old.length ? old : [...all].sort();
    });
  }, [plots.data]);

  // Escape deselects.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const apiDown = !!(summary.error && types.error && plots.error && !plots.data);
  function retryAll() {
    summary.retry();
    types.retry();
    plots.retry();
  }

  if (apiDown) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="max-w-md">
          <h1 className="mb-2 text-xl font-semibold">LandStack can't reach its data</h1>
          <ErrorMessage message={plots.error!} onRetry={retryAll} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-gray-200 bg-white">
        <div className="flex items-baseline gap-3 px-4 pt-2">
          <h1 className="text-lg font-semibold">LandStack</h1>
          <span className="text-xs text-gray-500">Land records on a map (fake demo data)</span>
        </div>
        <SummaryStrip summary={summary.data} conflictTypes={types.data} loading={summary.loading || types.loading}
                      error={summary.error ?? types.error}
                      onRetry={() => { summary.retry(); types.retry(); }} />
        <div className="border-t border-gray-100">
          <Filters filters={filters} villages={villages} conflictTypes={types.data ?? []}
                   shown={visible ? visible.features.length : null} loading={plots.loading}
                   onChange={setFilters} />
        </div>
      </header>

      <main className="relative flex-1">
        <PlotMap data={visible} selected={selected} onSelect={setSelected} />

        {plots.loading && !plots.data && (
          <div className="absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded bg-white px-4 py-2 shadow">
            <Spinner label="Loading plots…" />
          </div>
        )}
        {plots.error && (
          <div className="absolute left-1/2 top-4 z-10 w-96 max-w-full -translate-x-1/2 shadow">
            <ErrorMessage message={plots.error} onRetry={plots.retry} />
          </div>
        )}
        {selected && (
          <PassportPanel key={selected} ulpin={selected} conflictTypes={types.data}
                         onClose={() => setSelected(null)} />
        )}
      </main>
    </div>
  );
}
