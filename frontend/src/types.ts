// Shared types. They mirror docs/api-contract.md exactly. This is the only place they are defined.

export type Band = "green" | "amber" | "red";

export type ConflictType =
  | "boundary_overlap"
  | "restricted_zone_clash"
  | "area_mismatch"
  | "owner_mismatch"
  | "duplicate_survey_no"
  | "invalid_boundary"
  | "tax_overdue"
  | "missing_record"
  | "unrecorded_construction"; // SIMULATED (Phase 10)

export interface Finding {
  type: ConflictType;
  points: number;
  evidence: string;
}

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: number[][][]; // [ring][point][lon, lat]
}

export interface PlotProperties {
  ulpin: string;
  village: string;
  land_use: string;
  survey_no: string;
  score: number;
  band: Band;
  /** square metres (geography cast); null when the outline is invalid */
  area_sqm: number | null;
}

export interface PlotFeature {
  type: "Feature";
  geometry: PolygonGeometry;
  properties: PlotProperties;
}

export interface PlotCollection {
  type: "FeatureCollection";
  features: PlotFeature[];
}

export interface RorRecord {
  owner_name: string;
  recorded_area_sqm: number;
}

export interface RegistrationRecord {
  owner_name: string;
  registered_on: string; // YYYY-MM-DD
}

export interface TaxRecord {
  paid_until: string; // YYYY-MM-DD
}

/** Phase 9: a statistical hint. NOT a conflict, adds no points. null when the server has no model installed. */
export interface Unusual {
  flag: boolean;
  percentile: number; // 0 to 100: share of the model's training plots that are less unusual than this one
  reasons: string[]; // up to 3 plain-English reasons, only when flag is true
}

export interface Passport {
  ulpin: string;
  village: string;
  land_use: string;
  survey_no: string;
  area_sqm: number | null; // null when the boundary shape is invalid
  geometry: PolygonGeometry;
  ror: RorRecord | null;
  registration: RegistrationRecord | null;
  tax: TaxRecord | null;
  score: number;
  band: Band;
  findings: Finding[];
  unusual: Unusual | null;
  capped: boolean; // the findings' points add up to more than 100, so the score is held at 100
}

export interface Summary {
  total_plots: number;
  plots_per_band: Record<Band, number>;
  findings_per_type: Record<ConflictType, number>;
}

export interface ConflictTypeInfo {
  type: ConflictType;
  points: number;
  description: string;
  simulated: boolean; // true when the data behind this check is SIMULATED (the construction alert)
}

// GET /construction-alerts (SIMULATED): outlines of new buildings, in T1 but not in T0.
export interface ConstructionFeature {
  type: "Feature";
  geometry: PolygonGeometry;
  properties: { ulpin: string; new_sqm: number; piece_sqm: number; simulated: true };
}
export interface ConstructionCollection {
  type: "FeatureCollection";
  features: ConstructionFeature[];
}

// POST /plots/{ulpin}/explain (Phase 11): plain words for the findings a plot already has.
export type AiStatus = "on" | "off" | "busy" | "failed";
export type Language = "en" | "hi" | "mr";
// why English text is shown instead of a translation: the UI turns the code into a sentence in the user's language
export type TranslationNote = "ai_off" | "ai_busy" | "check_failed";
export interface Explanation {
  language?: Exclude<Language, "en">; // only for a Hindi or Marathi request
  translation?: "machine" | "unavailable";
  translation_note?: TranslationNote | null;
  text: string;
  source: "ai" | "template"; // who wrote it: the AI, or a template written in code
  ai_status: AiStatus;
  label: string; // "AI-written summary of the findings above", or the honest code-written label
  notice: string | null; // a friendly sentence when the AI was not used
}

// POST /guide/ask (Phase 11): the Land Guide.
export type GuideStatus = "answered" | "no_sources" | "ai_off" | "ai_busy" | "ai_failed";
export interface GuideSource {
  n: number;
  title: string;
  url: string | null; // null for the LandStack glossary (it has no web page)
  retrieved: string | null; // YYYY-MM-DD
}
export interface GuideAnswer {
  language?: Exclude<Language, "en">; // only for a Hindi or Marathi question
  translation?: "fixed" | "machine" | "unavailable" | "none"; // fixed = a sentence written by a person; machine = machine-translated
  translation_note?: TranslationNote | null;
  answer: string;
  status: GuideStatus;
  ai_status: AiStatus;
  sources: GuideSource[];
  disclaimer: string;
}

// Query parameters of GET /plots (all optional).
export interface PlotFilters {
  band?: Band;
  village?: string;
  conflict_type?: ConflictType;
}

// ---- login (Phase 7) ----

export type Role = "admin" | "officer" | "citizen";

export interface LoginResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number; // seconds
  user: { username: string; role: Role };
}

// What the page remembers about the logged-in user.
export interface Session {
  token: string;
  username: string;
  role: Role;
}

// ---- verify a printed passport (public endpoint) ----

export interface Verification {
  valid: boolean;
  ulpin: string;
  issued_at: string;
  status: "matches" | "records have changed since this was issued";
}

// ---- public front page endpoints (no login) ----
export interface PublicStats {
  total_plots: number;
  plots_per_band: Record<Band, number>;
}

export interface PublicPlot {
  ulpin: string;
  village: string;
  band: Band;
}

// ---- Phase 13b: role pages ----
/** One of my own recent actions (GET /me/activity). The plot id is null for a refused or not-found request. */
export interface ActivityEntry {
  id: number;
  action: string;
  ulpin: string | null;
  looked_at: string;
}

/** One plot with findings (GET /conflicts, staff only): types and points only, never evidence text. */
export interface ConflictRow {
  ulpin: string;
  village: string;
  score: number;
  band: Band;
  findings: { type: ConflictType; points: number; simulated: boolean }[];
}

/** One restricted zone (GET /zones, staff only). */
export interface ZoneRow {
  id: number;
  zone_type: string;
  area_sqm: number;
  plots_touching: number;
  geometry: { type: "Polygon" | "MultiPolygon"; coordinates: unknown };
}
