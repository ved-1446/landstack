# Handoff

## Current phase
Phase 2 (checks engine) is finished and waiting for the user's commit. Phase 3 (API) has NOT been started.

## Done so far
- Phase 0: CLAUDE.md, docs, docker-compose.yml (PostGIS 16-3.4, volume `pgdata`), .env.example, .gitignore, README, empty folders, `git init`.
- Phase 1: `db/schema.sql` (8 tables), `db/seed.py` (deterministic fake data, writes `db/planted_truth.json`), 100 plots with 40 planted problem plots and 6 decoy owner pairs.
- Phase 2, in `backend/app/` (with `__init__.py` files so `python -m backend.app.checks` works):
  - `config.py`: REFERENCE_DATE, POINTS, SCORE_CAP, band limits, ZONE_SHARE_LIMIT (0.20), AREA_MISMATCH_LIMIT (0.10), TAX_OVERDUE_YEARS (2), NAME_MATCH_THRESHOLD (0.60). `db/seed.py` now imports REFERENCE_DATE from here (one copy).
  - `db.py`: psycopg connection from `.env`.
  - `names.py`: `same_person(a, b) -> (bool, score)`. Normalise (lowercase, strip ASCII punctuation, drop one-letter initials, sort words), then TF-IDF char n-grams (2-3, char_wb, fitted on just the two names) and cosine similarity.
  - `checks.py`: 8 `check_*` functions with visible raw PostGIS SQL, `ALL_CHECKS`, `run_checks(conn)`, and the CLI `main()`.
  - `scoring.py`: `band_for`, `score_plot(findings)` returning `{score, band, findings}`, `run_all(conn)` returning `{ulpin: result}` for every plot.
- Tests: 43 pass (`python -m pytest backend/tests -q`). Every check flags exactly the planted set. No decoy is flagged. Clean plots score 0. Scoring edges 24/25 and 59/60 and the cap at 100 are tested.
- Summary: `python -m backend.app.checks` prints flagged vs planted counts per type (all equal), band counts (green 80, amber 20, red 0), and the top 3 plots.

## In progress
Nothing.

## Broken or unfinished
- Name scores on this data: the 6 decoys score 1.00 (normalising makes both spellings identical); the 4 real mismatches score 0.02 to 0.15. The threshold of 0.60 is a judgement inside a wide gap; it is above the worst different-owner pair that can be built from the seed's name pool (0.576). Real typos (e.g. "Kulkarny") are not in the data yet. Phase 9 tunes the matcher.
- Containment is not caught by the overlap check: `ST_Overlaps` is false when one plot lies fully inside another. The seed does not plant that case.
- Invalid shapes are skipped (not repaired) by the overlap, zone and area checks.
- Each planted plot has only one problem, so no plot reaches red (60+) yet; the highest score is 40. Red appears only if a plot has several problems.
- `db/seed.py` still has its own copy of the .env reader and `connect()`; `backend/app/db.py` is the app's copy. Left alone on purpose.
- `users`, `audit_log`, `building_snapshots` are still empty (Phases 7 and 10).
- Not built, by instruction: unrecorded-construction alert (Phase 10) and any ML (Phase 9).

## Next steps
1. User commits Phase 2.
2. Phase 3: FastAPI app in `backend/app/` (plots as GeoJSON, land passport per ulpin, score and findings), raw SQL, no ORM.
3. Phase 3 tests against the live database; keep the checks tests green.

## How to run
See README.md. Short version: `docker compose up -d`, create the schema (psql with `db/schema.sql`), `python db/seed.py`, `python -m pytest backend/tests -q`, `python -m backend.app.checks`.
Run Python from the repo root with the venv active (`.venv\Scripts\activate`).

## Files touched
Phase 2: `backend/__init__.py`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/names.py`, `backend/app/checks.py`, `backend/app/scoring.py`, `backend/requirements.txt` (added scikit-learn), `db/seed.py` (imports REFERENCE_DATE), `backend/tests/conftest.py`, `test_checks.py`, `test_scoring.py`, `test_names.py`, `test_config.py`, `README.md`, `docs/HANDOFF.md`, `docs/PROJECT_BRIEF.md`.
Test note: the tests re-seed the live database from `db/planted_truth.json`'s own settings, and use an autocommit connection so no open transaction blocks the seed's TRUNCATE.
