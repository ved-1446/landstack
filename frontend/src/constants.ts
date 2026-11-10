import type { Band } from "./types";

export const ALL_BANDS: Band[] = ["green", "amber", "red"];

export const BAND_LABEL: Record<Band, string> = { green: "Green", amber: "Amber", red: "Red" };

/** The score range of each band (green 0-24, amber 25-59, red 60 and up). */
export const BAND_RANGE: Record<Band, string> = { green: "0–24", amber: "25–59", red: "60+" };

/** Risk is never colour-only: the band is always written out as well. */
export const BAND_WORDS: Record<Band, string> = {
  green: "LOW RISK · GREEN BAND",
  amber: "WATCH · AMBER BAND",
  red: "HIGH RISK · RED BAND",
};

/** "boundary_overlap" -> "Boundary overlap". Names come from the API; this only makes them readable. */
export function prettyType(type: string): string {
  const text = type.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function prettyRole(role: string): string {
  return role.charAt(0).toUpperCase() + role.slice(1);
}
