import type { Band, PlotFeature } from "../types";

export type SortKey = "ulpin" | "village" | "area_sqm" | "score";
export interface PlotQuery {
  /** matches part of the plot id or the village, any case */
  text: string;
  /** any combination of bands; an empty set shows nothing (the page says "no band is selected") */
  bands: ReadonlySet<Band>;
  /** "" = every village */
  village: string;
  sort: { key: SortKey; dir: "asc" | "desc" };
}

/** The officer plots list: search, multi-band filter, village filter, then sort. Pure, so it is tested without a browser. */
export function selectPlots(features: PlotFeature[], query: PlotQuery): PlotFeature[] {
  const needle = query.text.trim().toLowerCase();
  const kept = features.filter((f) => {
    const p = f.properties;
    if (!query.bands.has(p.band)) return false;
    if (query.village && p.village !== query.village) return false;
    return !needle || p.ulpin.toLowerCase().includes(needle) || p.village.toLowerCase().includes(needle);
  });
  const { key, dir } = query.sort;
  const sign = dir === "asc" ? 1 : -1;
  return [...kept].sort((a, b) => {
    const x = a.properties[key];
    const y = b.properties[key];
    // a missing area (invalid outline) always goes last
    if (x === null && y === null) return 0;
    if (x === null) return 1;
    if (y === null) return -1;
    const order = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
    return order !== 0 ? sign * order : a.properties.ulpin.localeCompare(b.properties.ulpin);
  });
}

export function paginate<T>(items: T[], page: number, size: number): { rows: T[]; pages: number; page: number } {
  const pages = Math.max(1, Math.ceil(items.length / size));
  const current = Math.min(Math.max(1, page), pages);
  return { rows: items.slice((current - 1) * size, current * size), pages, page: current };
}
