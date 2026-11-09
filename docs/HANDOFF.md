# Handoff

## Current phase
Phase 1 (data foundation) is finished and waiting for the user's commit. Phase 2 (checks engine) has NOT been started.

## Done so far
- Phase 0: CLAUDE.md, docs, docker-compose.yml (PostGIS 16-3.4, volume `pgdata`), .env.example, .gitignore, README, empty folders, `git init`.
- Phase 1:
  - `db/schema.sql` creates the 8 tables (SRID 4326, GiST indexes on `plots.geom`, `zones.geom`, `building_snapshots.footprint`, foreign keys to `plots`). Safe to re-run.
  - `db/seed.py` builds 100 deterministic fake plots near Pune (flags `--plots`, `--problem-rate`, `--seed`), loads them with raw SQL, and writes `db/planted_truth.json`.
  - The default run plants 40 problem plots: 4 each of restricted_zone_clash, area_mismatch, owner_mismatch, invalid_boundary, tax_overdue and missing_record, plus 4 overlap pairs and 4 duplicate-survey pairs (8 plots each). Both plots of a pair are listed in the truth file. There are also 6 decoy owner pairs (same person, spelled differently) on clean plots.
  - `backend/tests/test_seed.py`: 11 tests pass.
  - `.venv` exists with `backend/requirements.txt` installed.

## In progress
Nothing.

## Broken or unfinished
- `users`, `audit_log` and `building_snapshots` are created but empty on purpose (Phases 7 and 10 fill them).
- Rows with `missing_record` have one of ror/registration/tax missing (rotating); the truth file's `details` says which table.
- Truth file shape: `{seed, plots, problem_rate, reference_date, conflicts: {ulpin: [types]}, details: {ulpin: {...}}, decoys: [{ulpin, ror_owner, registration_owner}]}`.

## Next steps
1. User commits Phase 1.
2. Phase 2: `backend/app/checks.py` with one visible raw-SQL check per conflict type, a fuzzy name matcher that must not flag the 6 decoys, and the risk score by code.
3. One pytest per check comparing against `db/planted_truth.json`.

## How to run
See README.md. Short version: `docker compose up -d`, create the schema (psql with `db/schema.sql`), `python db/seed.py`, `python -m pytest backend/tests -q`.

## Files touched
Phase 1: `db/schema.sql`, `db/seed.py`, `db/planted_truth.json` (generated), `backend/requirements.txt`, `backend/tests/test_seed.py`, `README.md`, `docs/HANDOFF.md`, `.venv/` (git-ignored).
Decisions: column `audit_log.username` instead of `user` (reserved word in SQL); `building_snapshots.snapshot` is a text label; every table has a surrogate `id` except `plots` (key `ulpin`) and `users` (key `username`).
