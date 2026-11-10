import { useReducedMotion } from "framer-motion";
import * as maplibregl from "maplibre-gl";
// maplibre-gl v6 runs its heavy work in a separate worker file. With Vite we hand it the file's
// URL ourselves; without this the map never starts ("Worker failed to load").
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useMemo, useRef, useState } from "react";
import { cn } from "../../lib/cn";
import { readPalette, type Palette } from "../../lib/tokens";
import type { ConstructionCollection, PlotFeature, PlotCollection, PolygonGeometry } from "../../types";
import { BASEMAPS, type BasemapId } from "./basemaps";

maplibregl.setWorkerUrl(workerUrl);

const SOURCE = "plots";
const FILL = "plots-fill";
const LINE = "plots-line";
const GLOW = "plots-ring-glow";
const RING = "plots-ring";
const C_SOURCE = "construction"; // SIMULATED new buildings
const C_FILL = "construction-fill";
const C_LINE = "construction-line";
const EMPTY_CONSTRUCTION: ConstructionCollection = { type: "FeatureCollection", features: [] };
const LABEL_MIN_ZOOM = 16;
const LABEL_CAP = 150; // never more than this many HTML labels, so the map stays fast
const STYLE_TIMEOUT_MS = 10_000;
const BLANK: maplibregl.StyleSpecification = { version: 8, sources: {}, layers: [] };

export interface FocusRequest {
  ulpin: string;
  /** the plot's outline, when it is not in the loaded plots (for example it was filtered out) */
  geometry?: PolygonGeometry;
  /** changes on every request, so asking for the same plot twice still flies there */
  nonce: number;
}
export interface MapLayerSwitches {
  boundaries: boolean;
  labels: boolean;
  risk: boolean;
  /** the SIMULATED new-building footprints (off by default) */
  construction: boolean;
}

interface MapViewProps {
  features: PlotFeature[];
  /** SIMULATED new-building outlines to draw while layers.construction is on */
  construction: ConstructionCollection | null;
  selected: string | null;
  onSelect: (ulpin: string | null) => void;
  basemap: BasemapId;
  layers: MapLayerSwitches;
  focus: FocusRequest | null;
  drawerOpen: boolean;
  onBasemapError: (failed: BasemapId) => void;
}

function centroidOf(geometry: PolygonGeometry): [number, number] {
  const ring = geometry.coordinates[0].slice(0, -1);
  return [ring.reduce((s, p) => s + p[0], 0) / ring.length, ring.reduce((s, p) => s + p[1], 0) / ring.length];
}

function boundsOf(geometries: PolygonGeometry[]): maplibregl.LngLatBounds | null {
  const bounds = new maplibregl.LngLatBounds();
  let any = false;
  for (const g of geometries) {
    for (const ring of g.coordinates) {
      for (const [lon, lat] of ring) {
        bounds.extend([lon, lat]);
        any = true;
      }
    }
  }
  return any ? bounds : null;
}


function asGeoJson(data: PlotCollection | ConstructionCollection) {
  return data as unknown as Parameters<maplibregl.GeoJSONSource["setData"]>[0];
}

/** Add our source and layers to whatever style is loaded (runs again after every basemap switch). */
function addPlotLayers(map: maplibregl.Map, data: PlotCollection, construction: ConstructionCollection) {
  if (!map.getSource(SOURCE)) {
    map.addSource(SOURCE, { type: "geojson", data: asGeoJson(data), promoteId: "ulpin" });
  }
  if (!map.getSource(C_SOURCE)) map.addSource(C_SOURCE, { type: "geojson", data: asGeoJson(construction) });
  if (!map.getLayer(FILL)) map.addLayer({ id: FILL, type: "fill", source: SOURCE });
  if (!map.getLayer(LINE)) map.addLayer({ id: LINE, type: "line", source: SOURCE });
  // the simulated new buildings sit above the plots but under the selected-plot ring
  if (!map.getLayer(C_FILL)) map.addLayer({ id: C_FILL, type: "fill", source: C_SOURCE });
  if (!map.getLayer(C_LINE)) map.addLayer({ id: C_LINE, type: "line", source: C_SOURCE });
  if (!map.getLayer(GLOW)) map.addLayer({ id: GLOW, type: "line", source: SOURCE, layout: { "line-cap": "round", "line-join": "round" } });
  if (!map.getLayer(RING)) map.addLayer({ id: RING, type: "line", source: SOURCE, layout: { "line-cap": "round", "line-join": "round" } });
}

interface PaintOptions {
  palette: Palette;
  risk: boolean;
  boundaries: boolean;
  construction: boolean;
  onLight: boolean;
  selected: string | null;
}

/** Colours and visibility, all from the design tokens (read into `palette`), never hard-coded here. */
function applyPaint(map: maplibregl.Map, { palette, risk, boundaries, construction, onLight, selected }: PaintOptions) {
  if (!map.getLayer(FILL)) return;
  const hover: maplibregl.ExpressionSpecification = ["boolean", ["feature-state", "hover"], false];
  map.setPaintProperty(
    FILL,
    "fill-color",
    risk
      ? (["match", ["get", "band"], "green", palette.riskGreen, "amber", palette.riskAmber, "red", palette.riskRed, palette.cream] as maplibregl.ExpressionSpecification)
      : palette.cream,
  );
  map.setPaintProperty(FILL, "fill-opacity", ["case", hover, risk ? 0.5 : 0.2, risk ? 0.35 : 0.1]);
  map.setPaintProperty(LINE, "line-color", onLight ? palette.navy900 : palette.cream);
  map.setPaintProperty(LINE, "line-width", ["case", hover, 2, 1]);
  map.setPaintProperty(LINE, "line-opacity", 0.85);
  map.setLayoutProperty(LINE, "visibility", boundaries ? "visible" : "none");

  // SIMULATED new buildings: their own colour (never a risk colour), a dashed outline, so they read as "not real"
  if (map.getLayer(C_FILL)) {
    map.setPaintProperty(C_FILL, "fill-color", palette.sim);
    map.setPaintProperty(C_FILL, "fill-opacity", 0.8);
    map.setLayoutProperty(C_FILL, "visibility", construction ? "visible" : "none");
    map.setPaintProperty(C_LINE, "line-color", onLight ? palette.navy900 : palette.cream);
    map.setPaintProperty(C_LINE, "line-width", 1.5);
    map.setPaintProperty(C_LINE, "line-dasharray", [2, 1]);
    map.setLayoutProperty(C_LINE, "visibility", construction ? "visible" : "none");
  }

  const isSelected = ["==", ["get", "ulpin"], selected ?? ""] as maplibregl.FilterSpecification;
  map.setFilter(GLOW, isSelected);
  map.setFilter(RING, isSelected);
  map.setPaintProperty(GLOW, "line-color", palette.coral);
  map.setPaintProperty(GLOW, "line-width", 10);
  map.setPaintProperty(GLOW, "line-blur", 6);
  map.setPaintProperty(GLOW, "line-opacity", 0.4);
  map.setPaintProperty(RING, "line-color", palette.coral);
  map.setPaintProperty(RING, "line-width", 3);
}

export default function MapView(props: MapViewProps) {
  const { features, construction, selected, basemap, layers, focus, drawerOpen } = props;
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [epoch, setEpoch] = useState(0); // goes up every time a style finishes loading
  const reduceMotion = useReducedMotion();
  const live = useRef(props);
  live.current = props;
  const palette = useRef<Palette | null>(null);
  const fitted = useRef(false);
  const hovered = useRef<string | null>(null);
  const markers = useRef(new Map<string, maplibregl.Marker>());
  const simMarkers = useRef(new Map<string, maplibregl.Marker>());
  const watch = useRef({ failed: false, tileErrors: 0, tileLoaded: false, timer: 0 });
  const firstBasemap = useRef(basemap);

  const data = useMemo<PlotCollection>(() => ({ type: "FeatureCollection", features }), [features]);
  const dataRef = useRef(data);
  dataRef.current = data;
  const centroids = useMemo(() => new Map(features.map((f) => [f.properties.ulpin, centroidOf(f.geometry)] as const)), [features]);
  const centroidsRef = useRef(centroids);
  centroidsRef.current = centroids;
  const constructionData = construction ?? EMPTY_CONSTRUCTION;
  const constructionRef = useRef(constructionData);
  constructionRef.current = constructionData;

  // 1. create the map once
  useEffect(() => {
    if (!container.current) return;
    palette.current = readPalette();
    const map = new maplibregl.Map({
      container: container.current,
      style: BASEMAPS[firstBasemap.current].style,
      center: [73.8, 18.55],
      zoom: 15,
      maxZoom: 19,
      attributionControl: { compact: false }, // the basemap credit stays open and visible
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    // Dev only (stripped from production builds): lets a test script find where a plot is on screen.
    if (import.meta.env.DEV) (window as unknown as { __map?: maplibregl.Map }).__map = map;

    const fail = () => {
      const w = watch.current;
      if (w.failed) return;
      w.failed = true;
      window.clearTimeout(w.timer);
      live.current.onBasemapError(live.current.basemap);
      if (live.current.basemap === "dark") map.setStyle(BLANK); // nothing left to fall back to: keep the plots visible
    };

    map.on("style.load", () => {
      window.clearTimeout(watch.current.timer);
      addPlotLayers(map, dataRef.current, constructionRef.current);
      setEpoch((n) => n + 1);
    });
    map.on("error", (event) => {
      const sourceId = (event as unknown as { sourceId?: string }).sourceId;
      if (!map.isStyleLoaded() && !sourceId) fail(); // the style itself could not be loaded
      if (sourceId === "imagery") {
        watch.current.tileErrors += 1;
        if (watch.current.tileErrors >= 3 && !watch.current.tileLoaded) fail();
      }
    });
    map.on("sourcedata", (event) => {
      if (event.sourceId === "imagery" && event.isSourceLoaded) watch.current.tileLoaded = true;
    });

    map.on("mousemove", FILL, (event) => {
      map.getCanvas().style.cursor = "pointer";
      const id = event.features?.[0]?.properties?.ulpin as string | undefined;
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
    map.on("click", (event) => {
      const hit = map.getLayer(FILL) ? map.queryRenderedFeatures(event.point, { layers: [FILL] })[0] : undefined;
      live.current.onSelect((hit?.properties?.ulpin as string | undefined) ?? null);
    });

    const markerStore = markers.current;
    const simStore = simMarkers.current;
    return () => {
      window.clearTimeout(watch.current.timer);
      markerStore.forEach((marker) => marker.remove());
      markerStore.clear();
      simStore.forEach((marker) => marker.remove());
      simStore.clear();
      map.remove();
      mapRef.current = null;
      fitted.current = false;
    };
  }, []);

  // 2. switching basemap: load the new style, then our layers come back on "style.load"
  useEffect(() => {
    const map = mapRef.current;
    if (!map || basemap === firstBasemap.current) return;
    firstBasemap.current = basemap;
    const w = watch.current;
    w.failed = false;
    w.tileErrors = 0;
    w.tileLoaded = false;
    window.clearTimeout(w.timer);
    markers.current.forEach((marker) => marker.remove());
    markers.current.clear();
    simMarkers.current.forEach((marker) => marker.remove());
    simMarkers.current.clear();
    map.setStyle(BASEMAPS[basemap].style);
    w.timer = window.setTimeout(() => {
      if (!map.isStyleLoaded() && !watch.current.failed) {
        watch.current.failed = true;
        live.current.onBasemapError(live.current.basemap);
        if (live.current.basemap === "dark") map.setStyle(BLANK);
      }
    }, STYLE_TIMEOUT_MS);
  }, [basemap]);

  // 3. the plots themselves
  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0) return;
    (map.getSource(SOURCE) as maplibregl.GeoJSONSource | undefined)?.setData(asGeoJson(data));
    if (!fitted.current && features.length > 0) {
      const bounds = boundsOf(features.map((f) => f.geometry));
      if (bounds) {
        map.fitBounds(bounds, { padding: 80, duration: 0 });
        fitted.current = true;
      }
    }
  }, [epoch, data, features]);

  // 3b. the simulated new buildings
  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0) return;
    (map.getSource(C_SOURCE) as maplibregl.GeoJSONSource | undefined)?.setData(asGeoJson(constructionData));
  }, [epoch, constructionData]);

  // 4. colours, boundaries on/off, the selected ring
  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0 || !palette.current) return;
    applyPaint(map, {
      palette: palette.current,
      risk: layers.risk,
      boundaries: layers.boundaries,
      construction: layers.construction,
      onLight: BASEMAPS[basemap].onLight,
      selected,
    });
  }, [epoch, layers.risk, layers.boundaries, layers.construction, basemap, selected]);

  // 5. the selected ring pulses softly (still when the visitor prefers reduced motion)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0 || !selected || reduceMotion) return;
    let frame = 0;
    const tick = (time: number) => {
      if (map.getLayer(GLOW)) map.setPaintProperty(GLOW, "line-opacity", 0.15 + 0.35 * (0.5 + 0.5 * Math.sin(time / 320)));
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [epoch, selected, reduceMotion]);

  // 6. fly to a plot when asked to
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !focus) return;
    const geometry = focus.geometry ?? live.current.features.find((f) => f.properties.ulpin === focus.ulpin)?.geometry;
    const bounds = geometry ? boundsOf([geometry]) : null;
    if (!bounds) return;
    const wide = window.innerWidth >= 768;
    const open = live.current.drawerOpen;
    map.fitBounds(bounds, {
      padding: {
        top: 96,
        left: wide ? 120 : 48,
        right: wide && open ? 500 : 96,
        bottom: !wide && open ? Math.round(window.innerHeight * 0.55) + 24 : 96,
      },
      maxZoom: 18.5,
      duration: reduceMotion ? 0 : 900,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus?.nonce]);

  // 7. ULPIN labels: small HTML labels, from zoom 16, only for plots in view, at most LABEL_CAP of them
  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0) return;
    const update = () => {
      const wanted = new Map<string, [number, number]>();
      if (live.current.layers.labels && map.getZoom() >= LABEL_MIN_ZOOM) {
        const view = map.getBounds();
        const centre = map.getCenter();
        const inView = [...centroidsRef.current.entries()]
          .filter(([, point]) => view.contains(point))
          .sort((a, b) => (a[1][0] - centre.lng) ** 2 + (a[1][1] - centre.lat) ** 2 - ((b[1][0] - centre.lng) ** 2 + (b[1][1] - centre.lat) ** 2))
          .slice(0, LABEL_CAP);
        inView.forEach(([ulpin, point]) => wanted.set(ulpin, point));
      }
      markers.current.forEach((marker, ulpin) => {
        if (!wanted.has(ulpin)) {
          marker.remove();
          markers.current.delete(ulpin);
        }
      });
      wanted.forEach((point, ulpin) => {
        if (markers.current.has(ulpin)) return;
        const element = document.createElement("div");
        element.className = cn("plot-label", BASEMAPS[live.current.basemap].onLight && "plot-label--on-light");
        element.textContent = ulpin;
        element.setAttribute("aria-hidden", "true");
        markers.current.set(ulpin, new maplibregl.Marker({ element, anchor: "center" }).setLngLat(point).addTo(map));
      });
    };
    update();
    map.on("moveend", update);
    return () => {
      map.off("moveend", update);
    };
  }, [epoch, features, layers.labels, basemap]);

  // 8. labels on the simulated new buildings: "SIMULATED · 61 sq m", from zoom 16, one per building outline
  useEffect(() => {
    const map = mapRef.current;
    if (!map || epoch === 0) return;
    const update = () => {
      const wanted = new Map<string, { point: [number, number]; text: string }>();
      if (live.current.layers.construction && map.getZoom() >= LABEL_MIN_ZOOM) {
        const view = map.getBounds();
        constructionRef.current.features.forEach((f, i) => {
          const point = centroidOf(f.geometry);
          if (view.contains(point) && wanted.size < LABEL_CAP) {
            wanted.set(`${f.properties.ulpin}-${i}`, { point, text: `SIMULATED · ${Math.round(f.properties.piece_sqm)} sq m` });
          }
        });
      }
      simMarkers.current.forEach((marker, key) => {
        if (!wanted.has(key)) {
          marker.remove();
          simMarkers.current.delete(key);
        }
      });
      wanted.forEach(({ point, text }, key) => {
        if (simMarkers.current.has(key)) return;
        const element = document.createElement("div");
        element.className = "sim-label";
        element.textContent = text; // the visible word SIMULATED is part of the label text
        simMarkers.current.set(key, new maplibregl.Marker({ element, anchor: "center" }).setLngLat(point).addTo(map));
      });
    };
    update();
    map.on("moveend", update);
    return () => {
      map.off("moveend", update);
    };
  }, [epoch, constructionData, layers.construction, basemap]);

  return (
    <div className={cn("absolute inset-0 z-map", drawerOpen && "drawer-open")}>
      <div ref={container} data-testid="map" className="size-full" />
    </div>
  );
}

