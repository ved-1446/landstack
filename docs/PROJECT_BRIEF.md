# LandStack: Project Brief

## What it is
A map app on fake land data. It shows plots, gathers each plot's records into one "land passport", finds eight kinds of conflicts with evidence, and gives a risk score from 0 to 100.

## Stack
- **Frontend (`frontend/`):** React + TypeScript + Vite + Tailwind + MapLibre GL JS
- **Backend (`backend/`):** Python + FastAPI + psycopg with raw SQL (no ORM)
- **Database:** PostgreSQL + PostGIS in Docker
- **Data and ML:** pandas, scikit-learn, joblib
- **Chatbot:** rank_bm25, requests, BeautifulSoup
- **LLM:** OpenRouter, model name stored in `.env`

## Database tables
- `plots(ulpin, geom, village, land_use, survey_no)`
- `ror_records(ulpin, owner_name, recorded_area_sqm)`
- `registrations(ulpin, owner_name, registered_on)`
- `tax_records(ulpin, paid_until)`
- `zones(zone_type, geom)`
- `building_snapshots(snapshot, footprint)`
- `users(username, password_hash, role)`
- `audit_log(user, ulpin, looked_at)`

## Conflicts and risk points
| Conflict | Points | Rule |
|---|---|---|
| Boundary overlap | 40 | |
| Restricted-zone clash | 30 | More than 20% of the plot inside a zone |
| Area mismatch | 25 | More than 10% off |
| Owner mismatch | 25 | After fuzzy name matching |
| Duplicate survey number | 20 | Same village |
| Invalid boundary shape | 15 | |
| Tax overdue | 15 | Paid-until more than 2 years before a fixed reference date |
| Missing record | 10 each | |
| Unrecorded-construction alert | 15 | |

- The score caps at 100.
- Bands: green 0-24, amber 25-59, red 60 or more.
- The unusual-plot model adds no points.

## Demo data
- 100 plots near Pune, about 40 with planted problems.
- 6 owner pairs that are the same person spelled differently; they must NOT be flagged.
- Seed script settings: `--plots`, `--problem-rate`, `--seed`.
- The seed script writes `planted_truth.json`.

## Phases
0. Setup
1. Data foundation
2. Checks engine
3. API
4. Frontend v1
5. Design pass (ORDER CHANGE: done after Phase 8, not now)
6. State adapters
7. Roles, audit log and rate limits
8. Printable passport
9. ML (unusual-plot model, tuned name matcher)
10. Simulated change detection
11. LLM explainer and Land Guide chatbot in English, Hindi and Marathi
12. Hardening and demo

**Order of work (changed by the user after Phase 4):** 0, 1, 2, 3, 4, 6, 7, 8, then 5 (design pass), then 9, 10, 11, 12. Phase numbers stay the same; only the order moved. Do not start the design pass before Phase 8 is done.

## Tools and sharing
Claude Code and Antigravity are both used, one at a time, in this same folder. This brief and `docs/HANDOFF.md` are how they share what has been done.

## Status and conventions (updated after Phase 2)
- Phases 0, 1 and 2 are built. See `docs/HANDOFF.md` for the exact state.
- All shared constants (points, bands, thresholds, REFERENCE_DATE) live in `backend/app/config.py`.
- Checks live in `backend/app/checks.py` (raw PostGIS SQL); the score is added up in `backend/app/scoring.py`.
- Owner names are compared by `backend/app/names.py` (normalise, TF-IDF character n-grams, cosine similarity, threshold 0.60). This is not an ML model and never changes the score.
- Invalid shapes are skipped by the overlap, zone and area checks and reported by the invalid-boundary check.
- Run Python from the repo root: `python -m backend.app.checks`, `python -m pytest backend/tests -q`.

## Status update after Phase 3
- Phase 3 is built: a read-only FastAPI app in `backend/app/main.py` (`/health`, `/plots`, `/plots/{ulpin}`, `/summary`, `/conflict-types`). Contract: `docs/api-contract.md`. Live docs at `http://localhost:8000/docs`.
- Scores are recomputed by the Phase 2 engine on every request (a cache would go in `scored()` if data grew). CORS allows only `http://localhost:5173`. No login or rate limits yet (Phase 7).
- Conflict-type descriptions live in `backend/app/config.py` and are served by `/conflict-types`.

## Status update after Phase 4
- Phase 4 is built: `frontend/` (React + TypeScript + Vite + Tailwind + MapLibre) shows the plots on a map coloured by risk band, a summary strip, filters (band, village, conflict type) and a land-passport side panel. It runs on `http://localhost:5173` and talks to the API on `http://localhost:8000` (`VITE_API_URL`).
- `frontend/src/api.ts` is the only file that talks to the backend; shared types live in `frontend/src/types.ts` and mirror `docs/api-contract.md`.
- Band colours are colour-blind friendly: green band #009E73, amber #F0E442, red #D55E00.
- Under Vite, MapLibre 6 needs `setWorkerUrl(...)` (see `frontend/src/components/Map.tsx`).
- Open API gaps (not changed, by instruction): no villages list endpoint, single `band` filter only. Details in `docs/HANDOFF.md`.

## Status update after Phase 6
- Phase 6 is built: state adapters in `db/adapters/`. `base.py` is the abstract adapter contract (read a raw file, return standard records plus rejected rows with a row number and plain reason; bad rows never crash the run). `maharashtra.py` (CSV: surname-first names, hectares + ares, DD/MM/YYYY), `karnataka.py` (JSON: "SURNAME, GIVEN" capitals, acres + guntas, YYYY-MM-DD), `uttar_pradesh.py` (nested JSON: owners list, hectares with comma decimal, DD-Mon-YYYY). Registry: `get_adapter(state)`.
- Standard records mirror the three record tables (land record, registration, tax record); areas are always square metres. All unit constants are in `db/adapters/units.py`.
- `python -m db.adapters.make_samples` writes a format demo (the first 20 plots in three state styles) into `db/adapters/samples/`. `python -m db.adapters.ingest --state <s> --file <path> [--dry-run]` loads standard records for ulpins that exist in `plots`; it matches by ulpin (insert new, update changed, leave identical), so it is safe to run twice; it never deletes.
- The sample formats are made-up, inspired by the real documents. They are not copies of any state's real format.
- The design pass (Phase 5) now comes after Phase 8.

## Status update after Phase 7
- Phase 7 is built: login, roles, audit log and rate limits. New backend modules: `security.py` (argon2 password hashing, JWT, the start-up check that refuses a missing or placeholder `JWT_SECRET`), `auth.py` (`POST /auth/login`, `GET /auth/me`, the token and role dependencies), `audit.py` (one row per passport view, including denied ones; a failure never breaks the request), `limits.py` (slowapi: logins 5/min per IP, everything else 60/min per user, shared across endpoints; 429 with `Retry-After`). `db/seed_users.py` creates the demo users (admin, officer, citizen1, citizen2).
- Roles: **citizen** sees only their own plots (`user_plots`); a plot that is not theirs returns 404, the same as a plot that does not exist, and other plots' ids are removed from their evidence text; `/summary` is 403. **officer**: all plots, all passports, `/summary`. **admin**: all that, plus `GET /audit`. `/health` is open; `/conflict-types` needs any login. The role matrix is in `docs/api-contract.md`.
- `users`, `user_plots` and `audit_log` deliberately have no foreign key to `plots`, so re-seeding the plots (which truncates `plots` with CASCADE) does not wipe who owns what or the audit history.
- Frontend: a plain Login screen, a small "signed in as ... / Log out" bar, `api.ts` sends the Authorization header (token in sessionStorage), 401 returns to the login screen and 429 shows a readable message. Citizens do not see the summary strip. The visual design is still the Phase 4 look (design pass comes after Phase 8).
- Secrets: `JWT_SECRET` and `JWT_EXPIRE_MINUTES` live in `.env`. No plain password is ever stored, logged or returned, and no hash is returned by any endpoint.
