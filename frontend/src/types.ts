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
