-- LandStack schema. Safe to re-run: it drops and recreates every table.
-- All geometry columns use SRID 4326 (GPS longitude/latitude).

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS passport_issues, audit_log, user_plots, users, building_snapshots, zones,
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

-- Phase 10 (SIMULATED change detection; there is no real satellite or imagery data anywhere in this project).
-- Building outlines from two survey rounds: 'T0' (the earlier one) and 'T1' (the later one). A building that is
-- in T1 but not in T0 is "new". ulpin deliberately has NO foreign key to plots: db/seed.py clears `plots` with
-- TRUNCATE ... CASCADE on every re-seed (it clears this table too).
CREATE TABLE building_snapshots (
    id         bigserial PRIMARY KEY,
    ulpin      text NOT NULL,                              -- the plot this building stands on
    snapshot   text NOT NULL CHECK (snapshot IN ('T0', 'T1')),
    footprint  geometry(Polygon, 4326) NOT NULL
);
CREATE INDEX building_snapshots_footprint_gix ON building_snapshots USING GIST (footprint);
CREATE INDEX building_snapshots_ulpin_snapshot_idx ON building_snapshots (ulpin, snapshot);

CREATE TABLE users (
    username       text PRIMARY KEY,
    password_hash  text NOT NULL,          -- an argon2 hash, never the password itself
    role           text NOT NULL CHECK (role IN ('admin', 'officer', 'citizen'))
);

-- Which plots a citizen owns. ulpin deliberately has NO foreign key to plots: db/seed.py clears
-- `plots` with TRUNCATE ... CASCADE on every re-seed, and that must not wipe who owns what.
CREATE TABLE user_plots (
    username  text NOT NULL REFERENCES users (username) ON DELETE CASCADE,
    ulpin     text NOT NULL,
    PRIMARY KEY (username, ulpin)
);
CREATE INDEX user_plots_ulpin_idx ON user_plots (ulpin);

-- One row per passport view, including denied ones. No foreign keys on purpose: the log must keep
-- its history if a user is deleted or plots are re-seeded, and denied views may name unknown plots.
-- action: view_passport | view_passport_denied | view_passport_not_found |
--         download_passport_pdf | download_passport_pdf_denied | download_passport_pdf_not_found
CREATE TABLE audit_log (
    id          bigserial PRIMARY KEY,
    username    text NOT NULL,
    role        text NOT NULL,             -- the role the user had at that moment
    ulpin       text,
    action      text NOT NULL,
    looked_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_log_looked_at_idx ON audit_log (looked_at DESC);
CREATE INDEX audit_log_username_idx ON audit_log (username);
CREATE INDEX audit_log_ulpin_idx ON audit_log (ulpin);

-- Every printed passport. The QR code on the paper holds doc_id; GET /verify/{doc_id} looks it up and
-- compares content_hash (SHA-256 of the passport data as it was) with the data as it is now.
-- No foreign key to plots, for the same reason as audit_log (re-seeding must not wipe it).
CREATE TABLE passport_issues (
    doc_id        text PRIMARY KEY,         -- short random id printed on the paper, e.g. 7KQ2-M9XD-4TPA
    ulpin         text NOT NULL,
    issued_to     text NOT NULL,            -- username who generated it
    issued_at     timestamptz NOT NULL DEFAULT now(),
    content_hash  text NOT NULL             -- 64 hex characters
);
CREATE INDEX passport_issues_ulpin_idx ON passport_issues (ulpin);
