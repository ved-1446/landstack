-- LandStack schema. Safe to re-run: it drops and recreates every table.
-- All geometry columns use SRID 4326 (GPS longitude/latitude).

CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS audit_log, user_plots, users, building_snapshots, zones,
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
-- action: view_passport | view_passport_denied | view_passport_not_found
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
