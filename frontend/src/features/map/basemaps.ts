import type { StyleSpecification } from "maplibre-gl";

export type BasemapId = "light" | "dark" | "satellite";

export interface Basemap {
  id: BasemapId;
  label: string;
  /** the map style: a style.json address, or a style object */
  style: string | StyleSpecification;
  /** plain-text credit, repeated in the Layers popover (the map also shows it on the map itself) */
  credit: string;
  /** true when the basemap is light, so plot lines and labels switch to dark ink */
  onLight: boolean;
}

// Free, keyless endpoints are used by default. If a key is provided (a free CARTO key, an Esri API key),
// it is added. CARTO has said its basemaps need a free key; the keyless address works today but may stop.
const CARTO_KEY = import.meta.env.VITE_CARTO_KEY;
const ESRI_KEY = import.meta.env.VITE_ESRI_KEY;

function carto(name: "positron" | "dark-matter"): string {
  const url = `https://basemaps.cartocdn.com/gl/${name}-gl-style/style.json`;
  return CARTO_KEY ? `${url}?key=${encodeURIComponent(CARTO_KEY)}` : url;
}

const ESRI_TILES = ESRI_KEY
  ? `https://ibasemaps-api.arcgis.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}?token=${encodeURIComponent(ESRI_KEY)}`
  : "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

const CARTO_CREDIT = "© OpenStreetMap contributors © CARTO";
const ESRI_CREDIT = "Powered by Esri | Esri, Maxar, Earthstar Geographics, and the GIS User Community";

const SATELLITE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    imagery: {
      type: "raster",
      tiles: [ESRI_TILES],
      tileSize: 256,
      maxzoom: 19,
      attribution:
        'Powered by <a href="https://www.esri.com" target="_blank" rel="noopener">Esri</a> | Esri, Maxar, Earthstar Geographics, and the GIS User Community',
    },
  },
  layers: [{ id: "imagery", type: "raster", source: "imagery" }],
};

export const BASEMAPS: Record<BasemapId, Basemap> = {
  light: { id: "light", label: "Light", style: carto("positron"), credit: CARTO_CREDIT, onLight: true },
  dark: { id: "dark", label: "Dark", style: carto("dark-matter"), credit: CARTO_CREDIT, onLight: false },
  satellite: { id: "satellite", label: "Satellite", style: SATELLITE_STYLE, credit: ESRI_CREDIT, onLight: false },
};

export const BASEMAP_ORDER: BasemapId[] = ["light", "dark", "satellite"];
