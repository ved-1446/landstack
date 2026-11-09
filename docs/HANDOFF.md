# Handoff

## Current phase
Phase 6 (state adapters) is finished and waiting for the user's commit. Phase 7 has NOT been started.

**ORDER CHANGE (from the user):** the design pass (Phase 5) is done AFTER Phase 8, not now. Order of work: 7, 8, then 5, then 9, 10, 11, 12. `frontend/` was not touched in Phase 6, and the checks and the score were not changed.

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
- Phase 3: `backend/app/main.py` (FastAPI, Pydantic response models, raw SQL, one connection per request via a dependency, CORS for http://localhost:5173 only, clean JSON errors 404/422/503/500). Endpoints: /health, /plots (filters band, village, conflict_type), /plots/{ulpin} (land passport), /summary, /conflict-types. `docs/api-contract.md` is the contract; `config.CONFLICT_DESCRIPTIONS` holds the one-line descriptions. 64 tests pass in total (43 old + 21 in `backend/tests/test_api.py`).
- Phase 4: `frontend/` (React 19 + TypeScript + Vite 8 + Tailwind 4 + MapLibre GL JS 6). Files: `src/api.ts` (the ONLY file that calls the backend), `src/types.ts` (types from `docs/api-contract.md`), `src/hooks.ts` (`useFetch`: loading/error/retry, cancels stale requests), `src/constants.ts` (band colours, `prettyType`), `src/App.tsx`, and `src/components/` Map, SummaryStrip, Filters, PassportPanel, Feedback (Spinner, ErrorMessage). Map: CARTO Positron basemap with attribution shown, `plots` GeoJSON source with `promoteId: "ulpin"`, fill layer coloured by band (Okabe-Ito colours: #009E73 / #F0E442 / #D55E00), outline layer, hover and selected via feature-state. Filters (band toggles, village, conflict type) re-request `/plots`. Side panel = land passport (missing record shown as "Missing"); Close button, Escape and clicking empty map all deselect. API down gives a clear message and Retry. Checked in real Chrome (headless, scripted): clean plot, overlap plot and missing-record plot all showed the right passport; 0 console errors or warnings; dev and production builds both load the map.
- Phase 6, in `db/adapters/` (plus an empty `db/__init__.py` so `python -m db.adapters.ingest` works): `base.py` (abstract `BaseAdapter` with `read_rows` and `convert`; the loop, the shared checks and the collecting of rejected rows are in `parse()`; dataclasses `RorRecord`, `RegistrationRecord`, `TaxRecord`, `StandardRow`, `RejectedRow`, `AdapterResult`), `units.py` (all unit constants and conversions), `formats.py` (number, date and owner-name readers/writers), `maharashtra.py`, `karnataka.py`, `uttar_pradesh.py`, `__init__.py` (`get_adapter`, `available_states`, clear `UnknownStateError`), `make_samples.py` (+ `samples/` with 3 generated files), `ingest.py`. "Row number" = the Nth data row, counting from 1 (CSV header excluded).
- Tests: 149 pass in total (64 old + 36 in `test_units.py` + 49 in `test_adapters.py`). They cover each unit conversion, each date format, hand-written raw files with hand-worked answers, bad rows (bad date, negative area, zero area, missing ulpin, unreadable number, owner without area) for all three states, round trip DB -> raw style -> adapter -> equal to the original (exact to the cent), unknown state, ingest twice = no duplicates, dry-run changes nothing, CLI errors. Database tests run in a rolled-back transaction and compare table snapshots before and after.
- Summary: `python -m backend.app.checks` prints flagged vs planted counts per type (all equal), band counts (green 80, amber 20, red 0), and the top 3 plots.

## In progress
Nothing.

## Broken or unfinished
- Name scores on this data: the 6 decoys score 1.00 (normalising makes both spellings identical); the 4 real mismatches score 0.02 to 0.15. The threshold of 0.60 is a judgement inside a wide gap; it is above the worst different-owner pair that can be built from the seed's name pool (0.576). Real typos (e.g. "Kulkarny") are not in the data yet. Phase 9 tunes the matcher.
- Containment is not caught by the overlap check: `ST_Overlaps` is false when one plot lies fully inside another. The seed does not plant that case.
- Invalid shapes are skipped (not repaired) by the overlap, zone and area checks.
- Each planted plot has only one problem, so no plot reaches red (60+) yet; the highest score is 40. Red appears only if a plot has several problems.
- `db/seed.py` still has its own copy of the .env reader and `connect()`; `backend/app/db.py` is the app's copy. Left alone on purpose.
- Phase 6 limits: (1) the raw formats are made up, so adapters are proven against our own samples and hand-written examples, not against real state files. (2) The round trip proves the reader and the sample writer agree; the hand-written tests are the independent check. (3) Owner names are rotated mechanically, so a name that already ends in an initial looks odd in a sample (the decoy "Kulkarni Ramesh S." appears as "S. Kulkarni Ramesh" in the Maharashtra file) but still round-trips exactly. Karnataka upper-casing round-trips exactly only for ordinarily capitalised names (no "McDonald"). (4) `ror_records`, `registrations` and `tax_records` have no UNIQUE(ulpin) constraint (kept from Phase 1), so ingest enforces one row per ulpin in code; two ingests running at the same moment could still insert twice. A UNIQUE constraint would fix that if "one row per plot" is the rule. (5) Ingest is not wired into the API or the frontend, and does not re-run the checks. (6) A blank hectare/acre/guntas/are part counts as 0 when its partner is filled in. (7) 40 guntas is not exactly 1 acre with the constants given (40 x 101.17 = 4046.8 vs 4046.8564), so a remainder can be a hair over 40 guntas; harmless.
- `frontend/.env.example` was NOT created: a permission rule in the user's settings blocks writing `.env*` files. It should contain two lines: a comment and `VITE_API_URL=http://localhost:8000`. The app works without it (it defaults to that address).
- API gaps found while building the frontend (backend untouched, by instruction): (1) no endpoint lists villages, so the village dropdown is filled from the villages seen in `/plots` responses; suggest `GET /villages`. (2) `/plots?band=` takes one band, so with two bands switched on the frontend asks for all and hides the third itself. (3) `/summary` always covers all plots, so the strip does not change with filters. (4) GeoJSON features have no top-level `id`, so the map uses `promoteId: "ulpin"`.
- MapLibre 6 needs its worker URL set by hand under Vite: `Map.tsx` imports `maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url` and calls `setWorkerUrl`. Without it the map never starts ("Worker failed to load"). Keep this if the map code is moved.
- Dev-only hook: in `npm run dev`, `window.__map` exposes the map (used by the browser test script). It is stripped from production builds.
- The production bundle is large (MapLibre, about 1.3 MB before gzip); Vite warns about chunk size. Harmless for now.
- No frontend unit tests yet (not requested). The browser check was a throw-away script outside the repo.
- `users`, `audit_log`, `building_snapshots` are still empty (Phases 7 and 10).
- Not built, by instruction: unrecorded-construction alert (Phase 10) and any ML (Phase 9).

## Next steps
1. User commits Phase 6 (and creates `frontend/.env.example`, see below).
2. Phase 7: roles, audit log and rate limits (fills `users` and `audit_log`).
3. Phase 8: printable passport. After that, the design pass (Phase 5, moved), then Phase 9.

## How to run
Adapters: `python -m db.adapters.make_samples`, then `python -m db.adapters.ingest --state maharashtra --file db/adapters/samples/maharashtra_sample.csv --dry-run` (drop `--dry-run` to load).
Frontend: start the API, then `cd frontend && npm install && npm run dev`, open http://localhost:5173.
API: `uvicorn backend.app.main:app --reload` then http://localhost:8000/docs.
See README.md. Short version: `docker compose up -d`, create the schema (psql with `db/schema.sql`), `python db/seed.py`, `python -m pytest backend/tests -q`, `python -m backend.app.checks`.
Run Python from the repo root with the venv active (`.venv\Scripts\activate`).

## Files touched
Phase 6: `db/__init__.py`, `db/adapters/{base,units,formats,maharashtra,karnataka,uttar_pradesh,__init__,make_samples,ingest}.py`, `db/adapters/samples/{maharashtra_sample.csv,karnataka_sample.json,uttar_pradesh_sample.json}`, `backend/tests/test_units.py`, `backend/tests/test_adapters.py`, `README.md`, `docs/HANDOFF.md`, `docs/PROJECT_BRIEF.md`. Removed `db/adapters/.gitkeep`. Nothing in `frontend/`, `backend/app/` or `db/schema.sql`/`db/seed.py` changed.

Phase 4 (all new, inside `frontend/`): `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `.gitignore`, `src/{main.tsx,App.tsx,api.ts,types.ts,hooks.ts,constants.ts,index.css,vite-env.d.ts}`, `src/components/{Map,SummaryStrip,Filters,PassportPanel,Feedback}.tsx`. Also `README.md`, `docs/HANDOFF.md`, `docs/PROJECT_BRIEF.md`. Removed `frontend/.gitkeep`. `node_modules/` and `dist/` are git-ignored.

Phase 3: `backend/app/main.py` (new), `backend/app/config.py` (added CONFLICT_DESCRIPTIONS only), `backend/requirements.txt` (fastapi, uvicorn, httpx), `backend/tests/test_api.py` (new), `docs/api-contract.md` (new), `README.md`, `docs/HANDOFF.md`, `docs/PROJECT_BRIEF.md`.
API notes: every request recomputes all scores (fine for 100 plots; cache spot is `scored()` in main.py). `findings_per_type` counts findings, not plots. FastAPI's TestClient warns that `httpx` is deprecated in favour of `httpx2`; harmless, left as you asked for httpx. No `id` on GeoJSON features (use MapLibre `promoteId: "ulpin"`).

Phase 2: `backend/__init__.py`, `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/db.py`, `backend/app/names.py`, `backend/app/checks.py`, `backend/app/scoring.py`, `backend/requirements.txt` (added scikit-learn), `db/seed.py` (imports REFERENCE_DATE), `backend/tests/conftest.py`, `test_checks.py`, `test_scoring.py`, `test_names.py`, `test_config.py`, `README.md`, `docs/HANDOFF.md`, `docs/PROJECT_BRIEF.md`.
Test note: the tests re-seed the live database from `db/planted_truth.json`'s own settings, and use an autocommit connection so no open transaction blocks the seed's TRUNCATE.
