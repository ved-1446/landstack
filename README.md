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
python db/seed.py --plots 100 --problem-rate 0.48 --seed 42
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

## Login, roles and rate limits (Phase 7)

**1. Add the secrets to `.env`.** The API will not start without a real `JWT_SECRET` (it refuses the placeholder). Generate a value and add these lines to your `.env` (and, as a template without the real value, to `.env.example`):
```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
```
JWT_SECRET=paste-the-generated-value-here
JWT_EXPIRE_MINUTES=60
```
In `.env.example` use `JWT_SECRET=change-me-generate-a-long-random-string`. Never commit the real value (`.env` is git-ignored).

**2. Recreate the tables and seed.** Phase 7 changed `db/schema.sql` (`users`, new `user_plots`, new `audit_log` columns). Re-running the schema drops and recreates every table, so seed again afterwards:
```
docker exec -i landstack-db psql -U landstack -d landstack -v ON_ERROR_STOP=1 < db/schema.sql
python db/seed.py
python db/seed_users.py
```
(PowerShell: `Get-Content db/schema.sql | docker exec -i landstack-db psql -U landstack -d landstack -v ON_ERROR_STOP=1`.) `db/seed_users.py` is safe to run again. Only argon2 hashes go into the database.

**3. Start the API and the frontend** as before, then open http://localhost:5173 and log in.

**Demo logins. DEMO ONLY: these passwords are public, never use them anywhere real.**

| Username | Password | Role | What it sees |
|---|---|---|---|
| `admin` | `AdminDemo#2026` | admin | everything an officer sees, plus the audit log (`GET /audit`) |
| `officer` | `OfficerDemo#2026` | officer | all plots, all passports, the summary |
| `citizen1` | `Citizen1Demo#2026` | citizen | only its 3 plots (a RED plot that overlaps another plot, a missing-record plot, a clean plot) |
| `citizen2` | `Citizen2Demo#2026` | citizen | only its 3 plots (a restricted-zone plot and 2 clean plots) |

A citizen who asks for someone else's plot gets "not found" (404), the same answer as for a plot that does not exist. The full role table is in `docs/api-contract.md`.

**Limits.** Logins: 5 per minute per IP address. Everything else: 60 per minute per user. Both are in `backend/app/config.py`. Too many requests gives a `429` with a `Retry-After` header.

**Tests** create their own `test_*` users with random passwords and delete them (and their audit rows) at the end. They use a throw-away JWT secret, so they work even before you set up `.env`:
```
python -m pytest backend/tests -q
```

## Printable land passport (Phase 8)

A one-page A4 PDF of a plot's passport: header with a clear "DEMO DATA, NOT AN OFFICIAL RECORD" notice, plot facts, the boundary drawn as vector lines, the risk score as a coloured badge **with the band written in words** (so it works in black and white), the findings table, the three records ("Missing" if absent), a QR code, a short document id, who generated it and when.

**Samples** (made with the demo admin account, demo data only; open them to see the layout):
- [docs/samples/passport_clean.pdf](docs/samples/passport_clean.pdf): a clean plot, "No conflicts found".
- [docs/samples/passport_red.pdf](docs/samples/passport_red.pdf): a red plot with four problems (overlap, area mismatch, owner mismatch, duplicate survey number: the points add up to 110 and the score is capped at 100).

Their QR codes point at `http://localhost:8000/verify/<document id>` and work on a machine whose database still holds those two issue rows (a re-run of `db/schema.sql` removes them).

**Download one.** In the app, open a plot and press **Download PDF**. Or with the API (replace the token; see "Login" above):
```
curl -H "Authorization: Bearer <token>" -o passport.pdf http://localhost:8000/plots/MH000100000012/passport.pdf
```
The same role rules as the JSON passport apply: a citizen can download only their own plots (anything else is a 404), and other plots' ids are hidden in their copy. Every download is written to the audit log and to the `passport_issues` table.

**Verify one.** Anyone can open `http://localhost:8000/verify/<document id>` (no login). It says only whether the records still match what was printed, the ulpin and the issue time. No names, no evidence, no score. It is limited to 10 requests per minute per IP address.

**Setup.** The schema changed again (new `passport_issues` table), so re-run it and re-seed (see "Login, roles and rate limits" above: `schema.sql`, then `db/seed.py`, then `db/seed_users.py`). The QR code needs to know the public web address of your API. Add this line to `.env` (the default is already `http://localhost:8000`, so it is optional locally):
```
PUBLIC_BASE_URL=http://localhost:8000
```
and the same line to `.env.example`. New packages (`reportlab`, `qrcode`, `pypdf`) are in `backend/requirements.txt`: run `pip install -r backend/requirements.txt`.

The PDF uses the built-in Helvetica and Courier fonts, which cover English. Hindi or Marathi names would need a Unicode font added in `backend/app/pdf.py` first.

## The demo data (Phase 8b)

`python db/seed.py` (defaults: 100 plots, problem rate 0.48, seed 42) always makes the same data:

| | Count |
|---|---|
| Plots with no planted problem | 52 (6 of them are the "same person, different spelling" decoys; 2 touch each other along an edge and must stay clean) |
| Plots with 1 / 2 / 3 / 4 planted problems | 33 / 6 / 7 / 2 |
| **Risk bands** | **60 green, 28 amber, 12 red** (two red plots reach the cap: their points add up to 110 and the score stops at 100) |
| Plots per problem type | overlap 14, zone 12, area 12, owner 14, duplicate survey number 8, invalid boundary 4, tax overdue 6, missing record 4 |

A single problem scores at most 40, so every red plot (60 or more) carries several problems. `db/planted_truth.json` lists every problem on every plot. The boundary-overlap check now finds a partial overlap, one plot inside another, and two identical plots, but not two plots that only touch along an edge (they must share at least `MIN_OVERLAP_SQM`, 5 square metres, set in `backend/app/config.py`).

After changing the seed, load it and rebuild what depends on it:
```
python db/seed.py
python db/seed_users.py
python -m db.adapters.make_samples
```

## Frontend settings (Phase 5)
Optional variables in `frontend/.env`: `VITE_API_URL` (default `http://localhost:8000`), `VITE_DEMO_ACCOUNTS` (default `true`; shows the demo-login row, set `false` for any real deployment), `VITE_CARTO_KEY` and `VITE_ESRI_KEY` (optional basemap keys). `npm run check:design` checks the design rules. Design notes: `docs/DESIGN_SYSTEM.md`; screenshots: `docs/design/screens/`.
