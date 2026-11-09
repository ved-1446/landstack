import { useEffect, useRef, useState } from "react";
import * as maplibregl from "maplibre-gl";
// maplibre-gl v6 runs its heavy work in a separate worker file. With Vite we hand it the file's
// URL ourselves; without this the map never starts ("Worker failed to load").
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { BAND_COLOR } from "../constants";
import type { PlotCollection } from "../types";

maplibregl.setWorkerUrl(workerUrl);

const STYLE_URL = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json";
const BLANK_STYLE: maplibregl.StyleSpecification = { version: 8, sources: {}, layers: [] };
const SOURCE = "plots";
const FILL = "plots-fill";
const LINE = "plots-outline";

interface Props {
  data: PlotCollection | null;
  selected: string | null;
  onSelect: (ulpin: string | null) => void;
}

/** Corner points of every plot -> [west, south, east, north], or null for no plots. */
function boundsOf(data: PlotCollection): maplibregl.LngLatBoundsLike | null {
  const b = new maplibregl.LngLatBounds();
  let any = false;
  for (const f of data.features) {
    for (const ring of f.geometry.coordinates) {
      for (const [lon, lat] of ring) {
        b.extend([lon, lat]);
        any = true;
      }
    }
  }
  return any ? b : null;
}

export default function PlotMap({ data, selected, onSelect }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const onSelectRef = useRef(onSelect);
  const fitted = useRef(false);
  const hovered = useRef<string | null>(null);
  const selectedPrev = useRef<string | null>(null);
  const [ready, setReady] = useState(false);
  const [basemapProblem, setBasemapProblem] = useState(false);

  onSelectRef.current = onSelect;

  // 1. Create the map once.
  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: STYLE_URL,
      center: [73.8, 18.55],
      zoom: 15,
      // Keep the basemap credit (OpenStreetMap, CARTO) open and visible, not collapsed.
      attributionControl: { compact: false },
    });
    mapRef.current = map;
    // Dev only (stripped from production builds): lets a test script find where a plot is on screen.
    if (import.meta.env.DEV) (window as unknown as { __map?: maplibregl.Map }).__map = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");

    // Runs every time a style finishes loading (also after the fallback style below).
    map.on("style.load", () => {
      if (map.getSource(SOURCE)) return;
      map.addSource(SOURCE, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
        promoteId: "ulpin", // use properties.ulpin as the feature id, so feature-state can address it
      });
      // Data-driven colour: each plot's fill is looked up from its "band" property.
      map.addLayer({
        id: FILL,
        type: "fill",
        source: SOURCE,
        paint: {
          "fill-color": ["match", ["get", "band"],
            "green", BAND_COLOR.green, "amber", BAND_COLOR.amber, "red", BAND_COLOR.red, "#999999"],
          "fill-opacity": ["case",
            ["boolean", ["feature-state", "selected"], false], 0.9,
            ["boolean", ["feature-state", "hover"], false], 0.8,
            0.55],
        },
      });
      map.addLayer({
        id: LINE,
        type: "line",
        source: SOURCE,
        paint: {
          "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#000000", "#374151"],
          "line-width": ["case",
            ["boolean", ["feature-state", "selected"], false], 4,
            ["boolean", ["feature-state", "hover"], false], 3,
            1],
        },
      });
      setReady(true);
    });

    // If the basemap cannot load (offline, blocked), still show the plots on a plain background.
    map.on("error", () => {
      if (!map.isStyleLoaded() && !map.getSource(SOURCE)) {
        setBasemapProblem(true);
        map.setStyle(BLANK_STYLE);
      }
    });

    map.on("mousemove", FILL, (e) => {
      map.getCanvas().style.cursor = "pointer";
      const id = e.features?.[0]?.properties?.ulpin as string | undefined;
      if (!id || id === hovered.current) return;
      if (hovered.current) map.setFeatureState({ source: SOURCE, id: hovered.current }, { hover: false });
      hovered.current = id;
      map.setFeatureState({ source: SOURCE, id }, { hover: true });
    });
    map.on("mouseleave", FILL, () => {
      map.getCanvas().style.cursor = "";
      if (hovered.current) map.setFeatureState({ source: SOURCE, id: hovered.current }, { hover: false });
      hovered.current = null;
    });
    map.on("click", (e) => {
      const hit = map.queryRenderedFeatures(e.point, { layers: [FILL] })[0];
      onSelectRef.current((hit?.properties?.ulpin as string | undefined) ?? null);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      fitted.current = false;
      hovered.current = null;
      selectedPrev.current = null;
      setReady(false);
    };
  }, []);

  // 2. Push new plot data into the source; fit the view to the plots the first time.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !data) return;
    (map.getSource(SOURCE) as maplibregl.GeoJSONSource).setData(data as unknown as Parameters<maplibregl.GeoJSONSource["setData"]>[0]);
    if (!fitted.current) {
      const bounds = boundsOf(data);
      if (bounds) {
        map.fitBounds(bounds, { padding: 60, duration: 0 });
        fitted.current = true;
      }
    }
  }, [ready, data]);

  // 3. Mark the selected plot (re-applied after new data arrives, to be safe).
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    if (selectedPrev.current) map.setFeatureState({ source: SOURCE, id: selectedPrev.current }, { selected: false });
    if (selected) map.setFeatureState({ source: SOURCE, id: selected }, { selected: true });
    selectedPrev.current = selected;
  }, [ready, selected, data]);

  return (
    <div className="absolute inset-0">
      <div ref={container} className="h-full w-full" data-testid="map" />
      {basemapProblem && (
        <div role="status" className="absolute bottom-8 left-2 rounded bg-yellow-100 px-3 py-1 text-xs text-yellow-900 shadow">
          The street basemap could not load. Plots are shown on a plain background.
        </div>
      )}
    </div>
  );
}
