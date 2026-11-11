import { AnimatePresence } from "framer-motion";
import { SearchX } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, getConflictTypes, getConstructionAlerts, getPassport, getPlots, getSummary } from "../api";
import { ErrorState } from "../components/ErrorState";
import { Button, EmptyState, SearchPill, Skeleton, useToast } from "../components/ui";
import { ALL_BANDS } from "../constants";
import { BASEMAPS, type BasemapId } from "../features/map/basemaps";
import { Dock } from "../features/map/Dock";
import { FiltersPopover, type MapFilters } from "../features/map/FiltersPopover";
import { LayersPopover } from "../features/map/LayersPopover";
import MapView, { type FocusRequest, type MapLayerSwitches } from "../features/map/MapView";
import { PlotsPanel } from "../features/map/PlotsPanel";
import { MapToolbar, type PanelId } from "../features/map/MapToolbar";
import { MyPlots } from "../features/myplots/MyPlots";
import { PassportDrawer } from "../features/passport/PassportDrawer";
import { useFetch } from "../hooks";
import { useTheme } from "../lib/theme";
import type { Band, ConflictType, Passport, PlotFeature, Summary } from "../types";
import type { Session } from "../types";

// below this width an open panel and the 430px passport drawer cannot sit side by side
const NARROW_DESKTOP = 1200;

interface MapScreenProps {
  session: Session;
}

/** The map, its tools and the passport drawer. It lives inside the app shell as a framed card (see MapPage). */
export default function MapScreen({ session }: MapScreenProps) {
  const staff = session.role !== "citizen";
  const toast = useToast();

  const [panel, setPanel] = useState<PanelId | null>(() => (!staff && window.innerWidth >= 1200 ? "plots" : null));
  const [filters, setFilters] = useState<MapFilters>({ village: "", conflictType: "" });
  const [bands, setBands] = useState<Set<Band>>(new Set(ALL_BANDS));
  // the basemap follows the theme (Light for the light theme, Dark for the dark one) until the person picks one in Layers
  const { theme } = useTheme();
  const [pickedBasemap, setBasemap] = useState<BasemapId | null>(null);
  const basemap: BasemapId = pickedBasemap ?? (theme === "light" ? "light" : "dark");
  const [layers, setLayers] = useState<MapLayerSwitches>({ boundaries: true, labels: true, risk: true, construction: false });
  const [selected, setSelected] = useState<string | null>(null);
  const [focus, setFocus] = useState<FocusRequest | null>(null);
  const [prefetched, setPrefetched] = useState<Passport | null>(null);
  const [villages, setVillages] = useState<string[]>([]);
  const pendingFly = useRef<string | null>(null);
  const nonce = useRef(0);

  // ---- data ----
  const plots = useFetch(
    (signal) => getPlots({ village: filters.village || undefined, conflict_type: filters.conflictType || undefined }, signal),
    [filters.village, filters.conflictType],
    true, // keep the old plots on the map while new ones load
  );
  const types = useFetch((signal) => getConflictTypes(signal), []);
  // Citizens may not see /summary (the server answers 403), so they never ask for it.
  const summary = useFetch<Summary | null>((signal) => (staff ? getSummary(signal) : Promise.resolve(null)), [staff]);

  // SIMULATED new buildings: fetched only while the layer is switched on (citizens get only their own plots)
  const construction = useFetch(
    (signal) => (layers.construction ? getConstructionAlerts(signal) : Promise.resolve(null)),
    [layers.construction],
  );

  const all: PlotFeature[] | null = plots.data ? plots.data.features : null;
  const visible = useMemo(() => (all ? all.filter((f) => bands.has(f.properties.band)) : []), [all, bands]);
  const counts = useMemo(() => {
    const result: Record<Band, number> = { green: 0, amber: 0, red: 0 };
    (all ?? []).forEach((f) => (result[f.properties.band] += 1));
    return result;
  }, [all]);
  const rules = useMemo(() => {
    const byType: Partial<Record<ConflictType, string>> = {};
    (types.data ?? []).forEach((info) => (byType[info.type] = info.description));
    return byType;
  }, [types.data]);

  const simulatedTypes = useMemo(
    () => new Set<ConflictType>((types.data ?? []).filter((info) => info.simulated).map((info) => info.type)),
    [types.data],
  );

  // if the simulated layer cannot load, say so (and switch it off) instead of drawing nothing in silence
  // tells the Land Guide button it is on the map page (on a phone it lifts above the dock)
  useEffect(() => {
    document.documentElement.dataset.map = "open";
    return () => {
      delete document.documentElement.dataset.map;
    };
  }, []);

  useEffect(() => {
    if (!layers.construction || !construction.error) return;
    toast.push({ title: "Simulated buildings could not load", description: construction.error, tone: "error" });
    setLayers((old) => ({ ...old, construction: false }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [construction.error]);

  // the API has no list of villages, so remember every village seen in a response
  useEffect(() => {
    if (!all) return;
    setVillages((old) => {
      const set = new Set(old);
      all.forEach((f) => set.add(f.properties.village));
      return set.size === old.length ? old : [...set].sort();
    });
  }, [all]);

  // ---- actions ----
  const flyTo = useCallback((ulpin: string) => setFocus({ ulpin, nonce: ++nonce.current }), []);

  const choose = useCallback(
    (ulpin: string) => {
      setSelected(ulpin);
      setPrefetched(null);
      if (window.innerWidth < NARROW_DESKTOP) setPanel(null);
      if (all?.some((f) => f.properties.ulpin === ulpin)) flyTo(ulpin);
      else pendingFly.current = ulpin; // not on the map right now: fly once the passport has its outline
    },
    [all, flyTo],
  );

  const onPassportLoaded = useCallback(
    (passport: Passport) => {
      if (pendingFly.current === passport.ulpin) {
        pendingFly.current = null;
        setFocus({ ulpin: passport.ulpin, geometry: passport.geometry, nonce: ++nonce.current });
      }
    },
    [],
  );

  async function search(ulpin: string): Promise<string | null> {
    if (all?.some((f) => f.properties.ulpin === ulpin)) {
      choose(ulpin);
      return null;
    }
    try {
      const passport = await getPassport(ulpin);
      setPrefetched(passport);
      setSelected(ulpin);
      if (window.innerWidth < NARROW_DESKTOP) setPanel(null);
      pendingFly.current = ulpin;
      onPassportLoaded(passport);
      return null;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return "No plot found with that ULPIN, or it is not one of yours.";
      return err instanceof Error ? err.message : "The search failed. Please try again.";
    }
  }

  const onBasemapError = useCallback(
    (failed: BasemapId) => {
      toast.push({
        title: `${BASEMAPS[failed].label} basemap could not load`,
        description: failed === "dark" ? "There is no other basemap to fall back to. Plots are shown on a plain background." : "Showing Dark instead.",
        tone: "error",
      });
      if (failed !== "dark") setBasemap("dark");
    },
    [toast],
  );

  const togglePanel = useCallback((id: PanelId) => setPanel((current) => (current === id ? null : id)), []);
  const closePanel = useCallback(() => setPanel(null), []);

  // Escape: close the open panel first, otherwise close the passport
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (panel) setPanel(null);
      else setSelected(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panel]);

  const noPlots = !plots.loading && all !== null && visible.length === 0;
  const filtersActive = filters.village !== "" || filters.conflictType !== "";

  return (
    <>
    {/* map-frame: "contain: layout paint" makes the panels, dock and popovers position themselves inside THIS card, not the page */}
    <div className="map-frame relative mt-8 h-(--map-card-height) min-h-96 overflow-hidden rounded-glass border border-glass-border bg-navy-950">
      <MapView
        features={visible}
        construction={layers.construction ? construction.data : null}
        selected={selected}
        onSelect={(ulpin) => (ulpin ? choose(ulpin) : setSelected(null))}
        basemap={basemap}
        layers={layers}
        focus={focus}
        drawerOpen={selected !== null}
        onBasemapError={onBasemapError}
      />

      <div className="fixed left-(--edge) top-(--edge) z-panel flex w-(--pill-width) flex-col gap-2 max-md:right-(--edge) max-md:w-auto">
        <SearchPill onSearch={search} />
        <MapToolbar staff={staff} active={panel} onToggle={togglePanel} />
      </div>

      <Dock shown={all ? visible.length : null} counts={counts} active={bands} onToggle={(band) => setBands((current) => {
        const next = new Set(current);
        if (next.has(band)) next.delete(band);
        else next.add(band);
        return next;
      })} loading={plots.loading} drawerOpen={selected !== null}
        construction={layers.construction ? { count: construction.data ? new Set(construction.data.features.map((f) => f.properties.ulpin)).size : null } : null} />

      <LayersPopover open={panel === "layers"} onClose={closePanel} basemap={basemap} onBasemap={setBasemap} layers={layers} onLayers={setLayers} />
      <FiltersPopover
        open={panel === "filters"}
        onClose={closePanel}
        filters={filters}
        onFilters={setFilters}
        villages={villages}
        conflictTypes={types.data}
        summary={summary.data}
      />
      {staff ? (
        <PlotsPanel open={panel === "plots"} onClose={closePanel} plots={all} loading={plots.loading} error={plots.error} onRetry={plots.retry} selected={selected} onPick={choose} />
      ) : (
        <MyPlots open={panel === "plots"} onClose={closePanel} plots={all} loading={plots.loading} error={plots.error} onRetry={plots.retry} selected={selected} onPick={choose} />
      )}

      {plots.loading && !all && (
        <div className="pointer-events-none fixed inset-0 z-panel flex items-center justify-center" role="status" aria-label="Loading plots">
          <Skeleton className="h-24 w-64 rounded-panel" />
        </div>
      )}
      {plots.error && !all && (
        <div className="fixed inset-0 z-panel flex items-center justify-center p-4">
          <div className="w-full max-w-96 rounded-panel border border-line-on-navy bg-navy-900 p-4 shadow-3">
            <ErrorState title="Cannot load plots" message={plots.error} onRetry={plots.retry} />
          </div>
        </div>
      )}
      {noPlots && !plots.error && (
        <div className="pointer-events-none fixed inset-0 z-panel flex items-center justify-center p-4">
          <div className="pointer-events-auto w-full max-w-96 rounded-panel border border-line-on-navy bg-navy-900 shadow-3">
            <EmptyState
              icon={SearchX}
              title="No plots to show"
              description={filtersActive ? "No plots match these filters." : bands.size === 0 ? "All bands are switched off." : "There are no plots to show yet."}
              action={
                filtersActive ? (
                  <Button variant="secondary" onClick={() => setFilters({ village: "", conflictType: "" })}>
                    Clear filters
                  </Button>
                ) : bands.size === 0 ? (
                  <Button variant="secondary" onClick={() => setBands(new Set(ALL_BANDS))}>
                    Show all bands
                  </Button>
                ) : undefined
              }
            />
          </div>
        </div>
      )}

      {/* the passport drawer docks INSIDE the map card: a side panel on a wide screen, a bottom sheet on a phone */}
      <AnimatePresence>
        {selected && (
          <PassportDrawer
            key={selected}
            ulpin={selected}
            role={session.role}
            rules={rules}
            simulatedTypes={simulatedTypes}
            prefetched={prefetched}
            onClose={() => setSelected(null)}
            onLoaded={onPassportLoaded}
          />
        )}
      </AnimatePresence>
    </div>
    </>
  );
}
