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
5. Design pass
6. State adapters
7. Roles, audit log and rate limits
8. Printable passport
9. ML (unusual-plot model, tuned name matcher)
10. Simulated change detection
11. LLM explainer and Land Guide chatbot in English, Hindi and Marathi
12. Hardening and demo

## Tools and sharing
Claude Code and Antigravity are both used, one at a time, in this same folder. This brief and `docs/HANDOFF.md` are how they share what has been done.
