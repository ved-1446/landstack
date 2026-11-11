import { vi } from "vitest";
import type { Band, ConflictRow, ConflictType, PlotFeature, PlotCollection, Summary } from "../types";

const square = (x: number, y: number) => ({ type: "Polygon" as const, coordinates: [[[x, y], [x + 0.001, y], [x + 0.001, y + 0.001], [x, y + 0.001], [x, y]]] });

const DATA: [string, string, Band, number, number | null][] = [
  ["MH000100000001", "Hinjewadi", "green", 3, 1200],
  ["MH000100000002", "Hinjewadi", "amber", 40, 980],
  ["MH000100000003", "Wagholi", "red", 95, 1500],
  ["MH000100000004", "Wagholi", "green", 0, null],
  ["MH000100000005", "Baner", "amber", 55, 760],
  ["MH000100000006", "Baner", "red", 100, 1849],
];

export const PLOT_FEATURES: PlotFeature[] = DATA.map(([ulpin, village, band, score, area], i) => ({
  type: "Feature",
  geometry: square(73.7 + i * 0.01, 18.5),
  properties: { ulpin, village, land_use: "residential", survey_no: `1/${i}`, score, band, area_sqm: area },
}));
export const PLOTS: PlotCollection = { type: "FeatureCollection", features: PLOT_FEATURES };

export const SUMMARY: Summary = {
  total_plots: 100,
  plots_per_band: { green: 58, amber: 29, red: 13 },
  findings_per_type: {
    boundary_overlap: 14, restricted_zone_clash: 12, area_mismatch: 12, owner_mismatch: 14, duplicate_survey_no: 8,
    invalid_boundary: 4, tax_overdue: 6, missing_record: 4, unrecorded_construction: 10,
  },
};

// 12 plots with findings, so the "top 10" limit can be tested
export const CONFLICTS: ConflictRow[] = Array.from({ length: 12 }, (_, i) => ({
  ulpin: `MH0001000000${String(60 - i).padStart(2, "0")}`,
  village: i % 2 ? "Baner" : "Wagholi",
  score: 100 - i * 5,
  band: (i < 6 ? "red" : "amber") as Band,
  findings: [
    { type: "boundary_overlap" as ConflictType, points: 40, simulated: false },
    ...(i === 0 ? [{ type: "unrecorded_construction" as ConflictType, points: 15, simulated: true }] : []),
  ],
}));

export const TYPES = (Object.keys(SUMMARY.findings_per_type) as ConflictType[]).map((type) => ({
  type, points: 10, description: `Rule text for ${type}`, simulated: type === "unrecorded_construction",
}));

export const ZONES = [{ id: 1, zone_type: "flood_plain", area_sqm: 50000, plots_touching: 7, geometry: { type: "Polygon" as const, coordinates: [[[73.7, 18.5], [73.71, 18.5], [73.71, 18.51], [73.7, 18.5]]] } }];

/** The mocked API. Tests change what a function resolves to with mockResolvedValue / mockRejectedValue. */
export const api = {
  getPlots: vi.fn(),
  getSummary: vi.fn(),
  getConflicts: vi.fn(),
  getConflictTypes: vi.fn(),
  getZones: vi.fn(),
  getMyActivity: vi.fn(),
  getPassport: vi.fn(),
  getPublicStats: vi.fn(),
  getPublicPlot: vi.fn(),
};

export function resetApi() {
  api.getPlots.mockReset().mockResolvedValue(PLOTS);
  api.getSummary.mockReset().mockResolvedValue(SUMMARY);
  api.getConflicts.mockReset().mockResolvedValue(CONFLICTS);
  api.getConflictTypes.mockReset().mockResolvedValue(TYPES);
  api.getZones.mockReset().mockResolvedValue(ZONES);
  api.getMyActivity.mockReset().mockResolvedValue([]);
  api.getPassport.mockReset().mockRejectedValue(new Error("not used here"));
  api.getPublicStats.mockReset().mockResolvedValue({ total_plots: 100, plots_per_band: { green: 58, amber: 29, red: 13 } });
  api.getPublicPlot.mockReset();
}
