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
  | "missing_record";

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
}

// Query parameters of GET /plots (all optional).
export interface PlotFilters {
  band?: Band;
  village?: string;
  conflict_type?: ConflictType;
}
