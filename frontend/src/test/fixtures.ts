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
export const api: Record<string, ReturnType<typeof vi.fn>> = {
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
  resetAdminApi();
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

// ---- Phase 13c: the admin's Control Room ----
export const ADMIN_USERS = [
  { username: "admin", role: "admin" as const, plots: 0, last_active: "2026-11-11T10:00:00Z", actions_30d: 6 },
  { username: "officer", role: "officer" as const, plots: 0, last_active: "2026-11-11T09:00:00Z", actions_30d: 41 },
  { username: "citizen1", role: "citizen" as const, plots: 3, last_active: null, actions_30d: 0 },
  { username: "citizen2", role: "citizen" as const, plots: 1, last_active: "2026-11-10T09:00:00Z", actions_30d: 2 },
];

const ACTIONS = ["view_passport", "view_passport_denied", "download_passport_pdf", "guide_ask", "explain_passport", "view_passport_not_found"];
export const AUDIT_ROWS = Array.from({ length: 20 }, (_, i) => ({
  id: 500 - i,
  username: i % 2 ? "citizen2" : "officer",
  role: (i % 2 ? "citizen" : "officer") as "citizen" | "officer",
  ulpin: ACTIONS[i % 6].endsWith("_denied") || ACTIONS[i % 6].endsWith("_not_found") || ACTIONS[i % 6] === "guide_ask" ? null : `MH0001000000${String(10 + i)}`,
  action: ACTIONS[i % 6],
  looked_at: `2026-11-11T${String(10 - Math.floor(i / 4)).padStart(2, "0")}:${String(59 - i).padStart(2, "0")}:00Z`,
}));

export const SYSTEM = {
  checked_at: "2026-11-11T10:05:00Z",
  api: { state: "ok" as const, detail: "The API is answering this request." },
  api_started_at: "2026-11-11T08:00:00Z",
  api_version: "0.13.3",
  database: { state: "ok" as const, detail: "PostgreSQL 16.4 answered a query." },
  postgis: { state: "ok" as const, detail: "PostGIS 3.4.2" },
  ai_explainer: { state: "off" as const, detail: "Switched off (no key is set). Explanations are written by code instead." },
  model: { loaded: true, kind: "Isolation Forest (a statistical hint, not a conflict)", trained_on_plots: 5000, trained_on: "2026-11-11", explanation_method: "shap", flag_percentile: 95 },
  counts: { plots: 100, users: 4, audit_rows: 37, passports_issued: 9 },
  versions: { python: "3.14.7", fastapi: "0.162.2", psycopg: "3.3.8", "scikit-learn": "1.9.1", shap: "0.54.1", shapely: "2.2.0", postgresql: "16.4", postgis: "3.4.2" },
};

export const INSIGHTS = {
  available: true,
  note: "Explanation only. A statistical model learned from made-up data and points out plots that look unusual. It adds no points and never changes a score or a band: scores are added up by code from the nine checks.",
  method: "shap",
  plots_checked: 100,
  flagged: 5,
  flagged_also_amber_or_red: 4,
  trained_on_plots: 5000,
  flag_percentile: 95,
  features: [
    ["neighbour_count", "How many other plots it overlaps or touches", 0.3, 2],
    ["years_since_tax_paid", "How long ago tax was last paid", 0.2, 2],
    ["area_sqm", "How big the plot is", 0.1, 1],
    ["perimeter_m", "How long its boundary is", 0.1, 0],
    ["compactness", "How round or stretched its shape is", 0.08, 0],
    ["aspect_ratio", "How much longer than wide it is", 0.05, 0],
    ["vertex_count", "How many corners its outline has", 0.05, 0],
    ["recorded_over_mapped", "How the recorded area compares with the mapped area", 0.04, 0],
    ["years_since_registration", "How long ago it was registered", 0.03, 0],
    ["zone_distance_m", "How close it is to a restricted zone", 0.02, 0],
    ["area_vs_village_median", "How its size compares with other plots in its village", 0.02, 0],
    ["invalid_shape", "Whether its outline is a broken shape", 0.01, 0],
  ].map(([name, label, share, top]) => ({ name: name as string, label: label as string, share: share as number, top_reason_for: top as number })),
};

api.getAdminUsers = vi.fn();
api.getAdminSystem = vi.fn();
api.getAdminInsights = vi.fn();
api.getAuditLog = vi.fn();

export function resetAdminApi() {
  api.getAdminUsers.mockReset().mockResolvedValue(ADMIN_USERS);
  api.getAdminSystem.mockReset().mockResolvedValue(SYSTEM);
  api.getAdminInsights.mockReset().mockResolvedValue(INSIGHTS);
  api.getAuditLog.mockReset().mockResolvedValue({ rows: AUDIT_ROWS, total: 45 });
}
