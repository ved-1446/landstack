import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, SearchX } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router";
import { Async } from "../../components/Async";
import { BandChip, Button, Chip, EmptyState, GlassCard, PageHeader } from "../../components/ui";
import { ALL_BANDS, BAND_LABEL } from "../../constants";
import { useAppData } from "../../lib/appData";
import { sqm } from "../../lib/format";
import { paginate, selectPlots, type SortKey } from "../../lib/plotFilters";
import type { Band } from "../../types";

const PAGE_SIZE = 15;
const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "ulpin", label: "Plot id" },
  { key: "village", label: "Village" },
  { key: "area_sqm", label: "Area", numeric: true },
  { key: "score", label: "Score", numeric: true },
];

/** Officer "Plots": every plot in a table with search, a multi-band filter, a village filter, sorting and pages. */
export default function PlotsTable() {
  const { plots } = useAppData();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [bands, setBands] = useState<Set<Band>>(new Set(ALL_BANDS));
  const [village, setVillage] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "score", dir: "desc" });
  const [page, setPage] = useState(1);

  const villages = useMemo(() => [...new Set((plots.data?.features ?? []).map((f) => f.properties.village))].sort(), [plots.data]);
  const matching = useMemo(() => (plots.data ? selectPlots(plots.data.features, { text, bands, village, sort }) : []), [plots.data, text, bands, village, sort]);
  const view = paginate(matching, page, PAGE_SIZE);

  const toggleBand = (band: Band) => {
    setBands((old) => {
      const next = new Set(old);
      if (next.has(band)) next.delete(band);
      else next.add(band);
      return next;
    });
    setPage(1);
  };
  const reset = () => {
    setText("");
    setBands(new Set(ALL_BANDS));
    setVillage("");
    setPage(1);
  };
  const sortBy = (key: SortKey) => {
    setSort((old) => (old.key === key ? { key, dir: old.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "score" || key === "area_sqm" ? "desc" : "asc" }));
    setPage(1);
  };

  return (
    <section>
      <PageHeader eyebrow="OFFICER WORK DESK" title="All" emphasis="plots" subtitle="Search, filter by band or village, sort by any column, and open a plot to see its passport." />
      <GlassCard className="mt-8">
        <Async state={plots} what="the plots">
          {() => (
            <>
              <div className="flex flex-wrap items-end gap-4">
                <div className="min-w-0 flex-1 basis-60">
                  <label htmlFor="plot-search" className="mb-2 block text-13 text-muted-on-navy">
                    Search by plot id or village
                  </label>
                  <input
                    id="plot-search"
                    value={text}
                    onChange={(e) => {
                      setText(e.target.value);
                      setPage(1);
                    }}
                    placeholder="MH0001 or Hinjewadi"
                    autoComplete="off"
                    className="h-11 w-full rounded-control border border-glass-border bg-navy-950 px-3 text-14 text-cream placeholder:text-faint-on-navy"
                  />
                </div>
                <div>
                  <label htmlFor="plot-village" className="mb-2 block text-13 text-muted-on-navy">
                    Village
                  </label>
                  <select
                    id="plot-village"
                    value={village}
                    onChange={(e) => {
                      setVillage(e.target.value);
                      setPage(1);
                    }}
                    className="h-11 rounded-control border border-glass-border bg-navy-950 px-3 text-14 text-cream"
                  >
                    <option value="">All villages</option>
                    {villages.map((v) => (
                      <option key={v} value={v}>
                        {v}
                      </option>
                    ))}
                  </select>
                </div>
                <fieldset>
                  <legend className="mb-2 text-13 text-muted-on-navy">Bands (pick any)</legend>
                  <div className="flex flex-wrap gap-2">
                    {ALL_BANDS.map((band) => (
                      <Chip key={band} tone={band} pressed={bands.has(band)} onClick={() => toggleBand(band)} label={`${BAND_LABEL[band]} band: ${bands.has(band) ? "shown" : "hidden"}`}>
                        {BAND_LABEL[band]}
                      </Chip>
                    ))}
                  </div>
                </fieldset>
              </div>

              <p className="mt-4 text-13 text-muted-on-navy" aria-live="polite">
                {bands.size === 0 ? "No band is selected, so no plots are shown." : `${matching.length} of ${plots.data?.features.length ?? 0} plots.`}
              </p>

              {matching.length === 0 ? (
                <EmptyState
                  icon={SearchX}
                  title="No plots match"
                  description={bands.size === 0 ? "Pick at least one band to see plots." : "Nothing matches this search and these filters."}
                  action={
                    <Button variant="secondary" onClick={reset}>
                      Clear the filters
                    </Button>
                  }
                />
              ) : (
                <>
                  <div className="mt-2 overflow-x-auto">
                    <table className="w-full min-w-xl text-left text-14">
                      <caption className="sr-only">Plots, sorted by {sort.key} ({sort.dir === "asc" ? "ascending" : "descending"})</caption>
                      <thead>
                        <tr className="border-b border-glass-border text-muted-on-navy">
                          {COLUMNS.map((c) => (
                            <th key={c.key} scope="col" aria-sort={sort.key === c.key ? (sort.dir === "asc" ? "ascending" : "descending") : "none"} className={`py-2 pr-4 font-mono text-11 font-medium tracking-widest ${c.numeric ? "text-right" : ""}`}>
                              <button type="button" onClick={() => sortBy(c.key)} className={`inline-flex items-center gap-1 rounded-control px-1 py-1 hover:text-cream ${c.numeric ? "flex-row-reverse" : ""}`}>
                                {c.label.toUpperCase()}
                                {sort.key === c.key && (sort.dir === "asc" ? <ArrowUp className="size-3" aria-hidden="true" /> : <ArrowDown className="size-3" aria-hidden="true" />)}
                              </button>
                            </th>
                          ))}
                          <th scope="col" className="py-2 font-mono text-11 font-medium tracking-widest">
                            BAND
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {view.rows.map((f) => {
                          const p = f.properties;
                          return (
                            <tr key={p.ulpin} className="border-b border-glass-border last:border-0 hover:bg-glass-fill">
                              <td className="py-3 pr-4 font-mono">
                                <button type="button" onClick={() => navigate(`/app/plots/${p.ulpin}`)} className="rounded-control text-cream underline underline-offset-4" aria-label={`Open the passport of ${p.ulpin}`}>
                                  {p.ulpin}
                                </button>
                              </td>
                              <td className="py-3 pr-4 text-cream">{p.village}</td>
                              <td className="py-3 pr-4 text-right text-cream">{sqm(p.area_sqm)}</td>
                              <td className="py-3 pr-4 text-right font-mono text-cream">{p.score}</td>
                              <td className="py-3">
                                <BandChip band={p.band} />
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <nav aria-label="Pages" className="mt-4 flex items-center justify-between gap-3">
                    <Button variant="secondary" size="sm" disabled={view.page <= 1} onClick={() => setPage(view.page - 1)}>
                      <ChevronLeft className="size-4" aria-hidden="true" />
                      Previous
                    </Button>
                    <p className="text-13 text-muted-on-navy">
                      Page {view.page} of {view.pages}
                    </p>
                    <Button variant="secondary" size="sm" disabled={view.page >= view.pages} onClick={() => setPage(view.page + 1)}>
                      Next
                      <ChevronRight className="size-4" aria-hidden="true" />
                    </Button>
                  </nav>
                </>
              )}
            </>
          )}
        </Async>
      </GlassCard>
    </section>
  );
}
