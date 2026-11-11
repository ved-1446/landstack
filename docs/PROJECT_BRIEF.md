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
| Boundary overlap | 40 | Shared ground of at least 5 sq m: a partial overlap, one plot inside another, or identical plots. Plots that only touch along an edge do not count |
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
- 100 plots near Pune, 48 with planted problems (since Phase 8b; one problem scores at most 40, so the 12 red plots each carry several). Demo mix: 60 green, 28 amber, 12 red, two plots at the 100 cap; 33 plots have one problem, 6 have two, 7 have three, 2 have four.
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

## Status update after Phase 8
- Phase 8 is built: the printable land passport. `backend/app/pdf.py` draws a one-page A4 PDF with ReportLab (vector drawing, a vector QR code, no map tiles, no internet). `backend/app/passport.py` now holds the code shared by the JSON passport, the PDF and `/verify`: loading a passport, the role/404/audit flow (`fetch_for_user`), hiding other plots from citizens (`hide_other_plots`), and the SHA-256 tamper-evidence hash.
- `GET /plots/{ulpin}/passport.pdf` follows the Phase 7 rules (a citizen gets only their own plots, anything else is 404, other plots' ids are hidden, every request is audited with `download_passport_pdf`, `..._denied`, `..._not_found`). Each download records a `passport_issues` row (no foreign keys, like the audit log). `GET /verify/{doc_id}` is public, limited to 10 per minute per IP, and says only valid or not, the ulpin, the issue time, and "matches" or "records have changed since this was issued".
- The QR code holds `{PUBLIC_BASE_URL}/verify/{doc_id}` (`PUBLIC_BASE_URL` in `.env`, default `http://localhost:8000`).
- Rate limits are now counted per endpoint, not per URL (a slowapi default that would have let someone guess document ids without limit).
- Frontend: a plain "Download PDF" button in the passport panel (through `api.ts`). Sample PDFs: `docs/samples/`.
- Next in the agreed order: the design pass (Phase 5), then Phase 9.

## Status update after Phase 8b (a mini-phase between 8 and the design pass)
- Data upgrade, no change to points, bands or scoring. `db/seed.py` now builds designed groups of plots instead of one problem per plot: multi-problem plots, 4 pairs sharing a survey number, 6 partial-overlap pairs, one pair where one plot lies inside the other, and one pair of clean plots that only touch along an edge. Default `--problem-rate` is now 0.48. The result is 60 green, 28 amber, 12 red (two red plots are capped at 100), every one of the eight problem types on at least 4 plots. `planted_truth.json` lists every problem per plot, and `details` now uses `overlap_partner` / `overlap_relation` / `dup_partner` instead of `partner`; it also has `touching_pairs`.
- The overlap check (`checks.py`) now uses `ST_Intersects` plus a minimum shared area (`MIN_OVERLAP_SQM = 5.0` in `config.py`), measured in square metres, instead of `ST_Overlaps`, so it finds a plot inside another and identical plots, and ignores edge-touching. Its evidence says "overlaps plot X by N sq m", "lies completely inside plot X", "plot X lies completely inside this plot" or "has exactly the same boundary as plot X".
- Demo users: citizen1 now owns a red plot that overlaps another plot (so the hidden-partner privacy demo is real), a missing-record plot and a clean plot; citizen2 a restricted-zone plot and two clean plots.
- Sample PDFs are `docs/samples/passport_clean.pdf` and `docs/samples/passport_red.pdf` (the capped 100 plot, four findings).

## Status update after Phase 5 (design pass)
- The frontend is now called LandStack and was rebuilt with a written design system (`docs/DESIGN_SYSTEM.md`: navy/cream/coral, tokens, self-hosted fonts, 12 UI components). Screens: login with an animated Flow Field background, map with rail, search pill, Layers (Light/Dark/Satellite) and Filters popovers, dock, passport drawer (bottom sheet on phones), Passports list for officers and admins, My plots for citizens. No backend or database change; `src/api.ts` is still the only file that talks to the API.
- Checked in a real browser at 1440, 768 and 390 px with all four demo logins. API gaps and deployment risks (basemap terms, `VITE_DEMO_ACCOUNTS=false`, Flow Field licence) are in `docs/HANDOFF.md`.
- Next: Phase 9, then 10, 11, 12.

## Status update after Phase 9 (ML)
- Two ML pieces, both advice only: the score is still computed by code alone. (1) An unsupervised Isolation Forest (`ml/`) adds an `unusual` field ({flag, percentile, reasons}, or null when no model file exists) to the passport, a footer line on flagged PDFs and a quiet "Unusual" chip in the drawer. It adds no points, never changes a band or a finding, and is not part of the tamper-evidence hash. (2) The name matcher was measured against 600 rule-made pairs; its threshold stays at 0.60 because tuning gained less than the agreed margin.
- Honest limit: trained and tested on generated data, so it mostly relearns the generator (it is blind to owner mismatches, duplicate survey numbers and missing records; its overlap result is an artefact of the generated map). Numbers and the caveat are in `README.md`.
- 348 backend tests pass. Next: Phase 10 (simulated construction alert), then 11 and 12.

## Status update after Phase 10 (simulated change detection)
- A ninth conflict check, `unrecorded_construction` (+15 points, fixed in `config.py`), compares two **generated** building snapshots (T0 earlier, T1 later) per plot: T1 minus T0 with `ST_Difference`, measured in square metres, flagged at 30 sq m or more (`MIN_NEW_BUILT_SQM`). **It is SIMULATED: there is no real satellite or imagery data**, and the word appears in the evidence text, the filter label, the PDF, the map labels, the API docs and the README. The score is still computed by code with fixed points; no model or LLM changes it.
- The demo data changed: 10 planted alerts and 8 jitter decoys that must not be flagged. Plots with no planted problem: 47 (was 52). Bands: **58 green, 29 amber, 13 red** (was 60/28/12). All earlier planted problems are unchanged.
- New: `GET /construction-alerts` (outlines for the map; citizens only their own plots), a `simulated` marker on `/conflict-types`, the map layer switch, a "Simulated" chip in the passport drawer, a third sample PDF. 388 backend tests pass. Next: Phase 11, then 12.

## Status update after Phase 11 (AI explainer and Land Guide, English first)
- Two optional AI features through OpenRouter (key and model in `.env`; the server starts and works without them and shows "AI is off"). (1) "Explain in plain words" (`POST /plots/{ulpin}/explain`) rewrites a plot's EXISTING findings: it never changes a finding, the score or the band, sends only finding types, numbers and the band (no names or ids), and falls back to a template written in code if the AI is off, busy or wrong. (2) The Land Guide (`POST /guide/ask`) answers general land-record questions only from a few public Vikaspedia pages (credit: Vikaspedia / C-DAC, listed with dates in `chatbot/sources.json`) and an original LandStack glossary, using BM25 search, citing its sources, saying "I don't know from my sources" when nothing matches, treating page text as data, never seeing plot or personal data, and never giving legal advice. One command rebuilds its corpus: `python -m chatbot.build`.
- The chat opens from a rail icon and a floating button; the drawer has an "Explain in plain words" button. Both are labelled as AI and as possibly wrong. Audit: four new actions, with no question text stored.
- Sources checked: Vikaspedia used; DOLR on hold; IGR Maharashtra and Bhulekh not used. 511 backend tests pass. Next: Hindi and Marathi for the Guide, UI and PDF (after approval), then Phase 12.

## Status update after Phase 11b (Hindi and Marathi, Devanagari text)
- The Land Guide and "Explain in plain words" work in हिन्दी and मराठी, chosen by the user in the panel (never guessed). Retrieval stays English-only (the corpus is not translated): a question is translated to English, answered from the English sources with all the existing checks run on the English answer, and the checked answer is translated back; translations must keep every `[n]` marker and every number or the English text is shown with a note. Translated AI text is labelled "machine-translated, may contain errors". The score and findings never change.
- Every fixed Hindi and Marathi sentence is in one file, `chatbot/strings.json`, **not yet reviewed by a native speaker**. Only the Guide panel and the Explain section are translated; the rest of the app stays English.
- Devanagari renders correctly in the UI (self-hosted Noto Sans Devanagari) and in the printable passport (HarfBuzz shaping, vector glyphs, never boxes; the PDF stays English otherwise). A sample with Marathi names: `docs/samples/passport_marathi_owner.pdf`. Font licences (SIL OFL 1.1) are credited in the README and `backend/app/fonts/`.
- 605 backend tests pass (the earlier 511 untouched). Next: Phase 12.

## Status update after Phase 12 (hardening, naming, README, demo)
- **Naming:** LandStack everywhere a reader sees it; the origin credit is the SIH 2026 land-records problem statement. The Docker container, database and database user keep their original infrastructure names until Phase 13c.
- **Hardening:** CORS from `CORS_ORIGINS` (no wildcards), exact version pins (tested on Python 3.14.7), the demo login row only when `VITE_DEMO_ACCOUNTS=true`, a test that walks every endpoint as a citizen and as a visitor, error responses that leak nothing. `pip-audit` and `npm audit` were clean. Scoring, bands, checks and planted data were not changed.
- **Small features:** friendly HTML `/verify` page (JSON still available), a `capped` flag (API, drawer, PDF; not in the tamper-evidence hash), an `X-Document-Id` header on the PDF.
- **Repo polish:** MIT `LICENSE`, `THIRD_PARTY.md` (Flow Field MIT notice, OFL fonts, GSAP's non-open licence noted), GitHub Actions CI (PostGIS service, pytest, `check:design`, build; Python 3.14; no secrets; AI mocked), `scripts/setup.ps1` and `scripts/setup.sh`, `docs/DEMO.md`, curated `docs/screenshots/`, regenerated `docs/samples/`, the final README (the long phase-by-phase notes moved to `docs/REFERENCE.md`).
- 659 backend tests pass. The project is feature-complete for the portfolio goal; what is left is in the README's Future work.

## Status update after Phase 13a-1 (new design foundation, shell and public endpoints)
- **Frontend overhaul has started (13a, 13b, 13c).** 13a-1 is done: new design tokens (60% navy, 30% glass and cream, 10% coral; role glows; lavender only for simulated data), the shared components, real URL routes (`react-router`) and a new app shell. The old flat navy look, the side icon rail and the floating Land Guide button are gone. See `docs/DESIGN_SYSTEM.md` (it has the role identity table).
- **Routes:** `/`, `/login`, `/how-it-works`, `/about`, `/verify` are public; `/app/*` needs a login and each role gets its own tabs (citizen, officer, admin with a second "Work desk" strip). The map lives inside the shell as a framed card at `/app/map`; the Land Guide is the `/app/guide` tab. Dashboard, plots, activity, conflicts, construction, audit, users, system and insights are placeholders until 13b (citizen, officer) and 13c (admin).
- **Backend:** two public, read-only, per-IP-limited endpoints, `GET /public/stats` (counts) and `GET /public/plot/{ulpin}` (only ulpin, village, band). No AI, no personal data, no schema change. Scoring, checks, planted data and `ml/` are untouched.
- **Dependencies:** added `react-router`, and `vitest`, `@testing-library/react`, `@testing-library/dom`, `jsdom` for tests; removed `gsap` (the gauge uses CSS and a small count-up hook).
- **Names:** the old product name and personal names were removed from the docs, LICENSE and code comments; the origin credit is "the SIH 2026 land-records problem statement". The Docker container, database and database user keep their original names until 13c.
- **Still to do in 13a-2:** the full landing page, How it works, About, browser checks and screenshots.

## Status update after Phase 13a-2 (the public pages)
- The public site is complete: a landing page (live Flow Field hero, public "Check a plot" card that shows only village and band, preview cards, four steps, three role cards), a "How it works" page (steps, the 9 checks with points, the bands, what is simulated) and an About page (what it is and is not, scoring, limits, credits). All live numbers come from `/public/stats`; the example passport is labelled "Sample data".
- Measured in a browser at 1440 and 390 px: no sideways scroll, no overlapping controls, reduced motion respected, text contrast at least 4.69:1 on the rendered pages. 36 frontend tests and 681 backend tests pass. Next: 13b (citizen and officer pages), then 13c (admin pages, final README, infra renames).
