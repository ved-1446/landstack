-- LandStack schema. Safe to re-run: it drops and recreates every table.
-- All geometry columns use SRID 4326 (GPS longitude/latitude).

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS audit_log, users, building_snapshots, zones,
    tax_records, registrations, ror_records, plots CASCADE;

CREATE TABLE plots (
    ulpin      text PRIMARY KEY,
    geom       geometry(Polygon, 4326) NOT NULL,
    village    text NOT NULL,
    land_use   text NOT NULL,
    survey_no  text NOT NULL
);
CREATE INDEX plots_geom_gix ON plots USING GIST (geom);
CREATE INDEX plots_village_survey_idx ON plots (village, survey_no);

CREATE TABLE ror_records (
    id                  bigserial PRIMARY KEY,
    ulpin               text NOT NULL REFERENCES plots (ulpin) ON DELETE CASCADE,
    owner_name          text NOT NULL,
    recorded_area_sqm   numeric(12, 2) NOT NULL
);
CREATE INDEX ror_records_ulpin_idx ON ror_records (ulpin);

CREATE TABLE registrations (
    id             bigserial PRIMARY KEY,
    ulpin          text NOT NULL REFERENCES plots (ulpin) ON DELETE CASCADE,
    owner_name     text NOT NULL,
    registered_on  date NOT NULL
);
CREATE INDEX registrations_ulpin_idx ON registrations (ulpin);

CREATE TABLE tax_records (
    id          bigserial PRIMARY KEY,
    ulpin       text NOT NULL REFERENCES plots (ulpin) ON DELETE CASCADE,
    paid_until  date NOT NULL
);
CREATE INDEX tax_records_ulpin_idx ON tax_records (ulpin);

CREATE TABLE zones (
    id         bigserial PRIMARY KEY,
    zone_type  text NOT NULL,
    geom       geometry(Polygon, 4326) NOT NULL
);
CREATE INDEX zones_geom_gix ON zones USING GIST (geom);

CREATE TABLE building_snapshots (
    id         bigserial PRIMARY KEY,
    snapshot   text NOT NULL,            -- label of the survey round, e.g. 'T0'
    footprint  geometry(Polygon, 4326) NOT NULL
);
CREATE INDEX building_snapshots_footprint_gix ON building_snapshots USING GIST (footprint);

CREATE TABLE users (
    username       text PRIMARY KEY,
    password_hash  text NOT NULL,
    role           text NOT NULL
);

-- The brief calls the first column "user"; that is a reserved word in SQL,
-- so the column is named username.
CREATE TABLE audit_log (
    id          bigserial PRIMARY KEY,
    username    text NOT NULL REFERENCES users (username),
    ulpin       text NOT NULL REFERENCES plots (ulpin) ON DELETE CASCADE,
    looked_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_ulpin_idx ON audit_log (ulpin);
