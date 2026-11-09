import type { Band } from "./types";

export const ALL_BANDS: Band[] = ["green", "amber", "red"];

// Colour-blind-friendly set (Okabe-Ito): bluish green, yellow, vermillion. No pure red or green.
export const BAND_COLOR: Record<Band, string> = {
  green: "#009E73",
  amber: "#F0E442",
  red: "#D55E00",
};

// Text colour that stays readable on top of each band colour.
export const BAND_TEXT: Record<Band, string> = {
  green: "#ffffff",
  amber: "#1f2937",
  red: "#ffffff",
};

export const BAND_LABEL: Record<Band, string> = {
  green: "Green",
  amber: "Amber",
  red: "Red",
};

/** "boundary_overlap" -> "Boundary overlap". Names come from the API; this only makes them readable. */
export function prettyType(type: string): string {
  const text = type.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}
