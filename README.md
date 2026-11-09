# LandStack

Land records on a map (fake data, demo project). Work in progress.

See `docs/PROJECT_BRIEF.md` for the plan and `docs/HANDOFF.md` for current status.

## Setup (Phase 0-1)

Needs Docker and Python 3.11+. Copy `.env.example` to `.env` and set `POSTGRES_PASSWORD`.

**1. Start the database**
```
docker compose up -d
```

**2. Python environment** (Windows; on Mac/Linux use `source .venv/bin/activate`)
```
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

**3. Create the schema** (safe to re-run; it drops and recreates the tables)

Git Bash / Mac / Linux:
```
docker exec -i landstack-db psql -U landstack -d landstack -v ON_ERROR_STOP=1 < db/schema.sql
```
PowerShell:
```
Get-Content db/schema.sql | docker exec -i landstack-db psql -U landstack -d landstack -v ON_ERROR_STOP=1
```

**4. Seed the fake data** (same flags = same data; also writes `db/planted_truth.json`)
```
python db/seed.py
python db/seed.py --plots 100 --problem-rate 0.4 --seed 42
```

**5. Run the tests** (the last test needs the database running and seeded schema)
```
python -m pytest backend/tests -q
```

## Run the checks (Phase 2)

Run from the repo root with the virtual environment active and the database seeded:
```
python -m backend.app.checks
```
This prints flagged vs planted counts per conflict type, the band counts and the top 3 plots.

## Start the API (Phase 3)

Run from the repo root with the virtual environment active and the database seeded:
```
uvicorn backend.app.main:app --reload
```
Then open http://localhost:8000/docs for the interactive docs. The full contract is in `docs/api-contract.md`.
