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

## Run the frontend (Phase 4)

Needs Node 20+. The API must be running first (see "Start the API" above).
```
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 (the port is fixed, because the API only allows requests from it).
The API address defaults to `http://localhost:8000`. To change it, create `frontend/.env` containing `VITE_API_URL=http://localhost:8000`.

Other commands (run inside `frontend/`):
```
npm run typecheck    # TypeScript check
npm run build        # typecheck + production build into frontend/dist
npm run preview      # serve the production build on port 5173
```

## State adapters (Phase 6)

Every state keeps land records in its own format. An **adapter** turns one state's raw file into our one standard format (square metres, `YYYY-MM-DD` dates, "Given Family" names), so the checks never need to know where a record came from. Adapters live in `db/adapters/`: `maharashtra` (CSV), `karnataka` (JSON), `uttar_pradesh` (nested JSON).

Run from the repo root with the virtual environment active and the database running:

**Make the demo files** (the first 20 plots in the database, shown in the three state styles).
This is a *format demo*: the same 20 plots in three made-up styles, so you can compare them. It is deterministic: the same database always gives identical files. The files are in `db/adapters/samples/`.
```
python -m db.adapters.make_samples
```

**Load a raw file.** Always look first with `--dry-run`, which changes nothing:
```
python -m db.adapters.ingest --state maharashtra --file db/adapters/samples/maharashtra_sample.csv --dry-run
python -m db.adapters.ingest --state maharashtra --file db/adapters/samples/maharashtra_sample.csv
```
States: `maharashtra`, `karnataka`, `uttar_pradesh`. Only ulpins that already exist in `plots` are loaded. Rejected rows and unknown ulpins are listed, and the good rows still load. Running it twice changes nothing. A record the file does not mention is never deleted.

**Tests** (adapter tests change the database only inside a transaction that is rolled back):
```
python -m pytest backend/tests -q
```
