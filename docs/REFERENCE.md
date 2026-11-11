# LandStack reference (phase by phase)

The long, detailed notes written while building each phase. For the short version (what it is, quick start, honest limits) read the
[README](../README.md). Commands are run from the repo root with the virtual environment active, unless said otherwise.
Where this file shows `docker exec -i <db-container> psql -U <POSTGRES_USER> -d <POSTGRES_DB>`, use the container name from `docker compose ps`
and the database user and name from your `.env`.

## Manual setup (Phase 0-1; `scripts/setup.ps1` / `scripts/setup.sh` do all of this for you)

Needs Docker and Python 3.11+ (3.14 is what the tests were run on). Copy `.env.example` to `.env` and fill it in (see the README).

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
docker exec -i <db-container> psql -U <POSTGRES_USER> -d <POSTGRES_DB> -v ON_ERROR_STOP=1 < db/schema.sql
```
PowerShell:
```
Get-Content db/schema.sql | docker exec -i <db-container> psql -U <POSTGRES_USER> -d <POSTGRES_DB> -v ON_ERROR_STOP=1
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
docker exec -i <db-container> psql -U <POSTGRES_USER> -d <POSTGRES_DB> -v ON_ERROR_STOP=1 < db/schema.sql
python db/seed.py
python db/seed_users.py
```
(PowerShell: `Get-Content db/schema.sql | docker exec -i <db-container> psql -U <POSTGRES_USER> -d <POSTGRES_DB> -v ON_ERROR_STOP=1`.) `db/seed_users.py` is safe to run again. Only argon2 hashes go into the database.

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
- [docs/samples/passport_construction.pdf](docs/samples/passport_construction.pdf) (Phase 10): a plot with an overlap, a missing record and the **SIMULATED** unrecorded-construction finding (50 + 15 = 65, red).

Their QR codes point at `http://localhost:8000/verify/<document id>` and work on a machine whose database still holds those three issue rows (a re-run of `db/schema.sql` removes them).

**Download one.** In the app, open a plot and press **Download PDF**. Or with the API (replace the token; see "Login" above):
```
curl -H "Authorization: Bearer <token>" -o passport.pdf http://localhost:8000/plots/MH000100000012/passport.pdf
```
The same role rules as the JSON passport apply: a citizen can download only their own plots (anything else is a 404), and other plots' ids are hidden in their copy. Every download is written to the audit log and to the `passport_issues` table.

**Verify one.** Anyone can open `http://localhost:8000/verify/<document id>` (no login). A browser gets a small friendly page (MATCHES / HAS CHANGED / NOT FOUND); a program asking for JSON gets JSON. It says only whether the records still match what was printed, the ulpin and the issue time. No names, no evidence, no score. It is limited to 10 requests per minute per IP address.

**Setup.** The schema changed again (new `passport_issues` table), so re-run it and re-seed (see "Login, roles and rate limits" above: `schema.sql`, then `db/seed.py`, then `db/seed_users.py`). The QR code needs to know the public web address of your API. Add this line to `.env` (the default is already `http://localhost:8000`, so it is optional locally):
```
PUBLIC_BASE_URL=http://localhost:8000
```
and the same line to `.env.example`. New packages (`reportlab`, `qrcode`, `pypdf`) are in `backend/requirements.txt`: run `pip install -r backend/requirements.txt`.

The PDF uses the built-in Helvetica and Courier fonts for English. Hindi and Marathi text is drawn with Noto Sans Devanagari (Phase 11b, below).

## The demo data (Phase 8b)

`python db/seed.py` (defaults: 100 plots, problem rate 0.48, seed 42) always makes the same data:

| | Count |
|---|---|
| Plots with no planted problem | **47** (was 52 before Phase 10; 6 of them are the "same person, different spelling" decoys; 2 touch each other along an edge and must stay clean) |
| Plots with 1 / 2 / 3 / 4 planted problems | **36 / 6 / 8 / 3** (was 33 / 6 / 7 / 2) |
| **Risk bands** | **58 green, 29 amber, 13 red** (was 60 / 28 / 12: the +15 alert tips two plots from green to amber and one from amber to red; two red plots reach the cap at 100) |
| Plots per problem type | overlap 14, zone 12, area 12, owner 14, duplicate survey number 8, invalid boundary 4, tax overdue 6, missing record 4, **unrecorded construction 10 (SIMULATED)** |

A single problem scores at most 40, so every red plot (60 or more) carries several problems. `db/planted_truth.json` lists every problem on every plot. The boundary-overlap check now finds a partial overlap, one plot inside another, and two identical plots, but not two plots that only touch along an edge (they must share at least `MIN_OVERLAP_SQM`, 5 square metres, set in `backend/app/config.py`).

After changing the seed, load it and rebuild what depends on it:
```
python db/seed.py
python db/seed_users.py
python -m db.adapters.make_samples
```

## Unrecorded-construction alert (Phase 10) — SIMULATED

**Everything about this feature is simulated.** There is no real satellite or aerial imagery in this project. `db/seed.py` *generates* two snapshots of building outlines for every plot, **T0** (earlier) and **T1** (later), in the table `building_snapshots` (with `ulpin`, `snapshot`, `footprint`; no foreign key to `plots`). The words "SIMULATED" appear in the passport evidence text, the filter label, the PDF, the map labels and the API docs, on purpose.

- **How it works (change detection with two snapshots):** per plot, take the T1 buildings and subtract the T0 buildings (`ST_Difference`, raw SQL visible in `backend/app/checks.py`). What is left is new building that is not in the records. It is measured in square metres (geography cast).
- **Threshold:** a plot is flagged when the new area is at least `MIN_NEW_BUILT_SQM` = **30 sq m** (`backend/app/config.py`). Small survey noise (a building shifted 1 to 2 m, or wobbly edges) leaves only a sliver of up to about 20 sq m, so it is not flagged.
- **Points:** `CONSTRUCTION_ALERT_POINTS` = **15**, fixed, added to the score like every other finding (the cap at 100 still holds). No model or LLM changes it.
- **Demo data:** 10 planted alerts (5 on plots that had no other problem, 5 on plots that already had problems, chosen so the +15 visibly moves some plots up a band) and 8 jitter plots that must NOT be flagged. Invalid-shape plots, the decoy-owner plots and the touching pair never get an alert. The earlier eight problem types are unchanged. `db/planted_truth.json` lists the alerts (under `conflicts`, with `details[ulpin].new_built_sqm`) and the jitter plots (`construction_decoys`).
- **In the app:** Map layers, switch **Unrecorded construction (simulated)** draws the new-building outlines in a light blue (the `sim` colour, used only for simulated data) with a dashed edge, labelled "SIMULATED · 61 sq m" from zoom 16, and a "Simulated new buildings" chip in the dock. The Filters popover lists the type with its count, and the passport drawer shows the finding with a "Simulated" chip. The map gets the outlines from `GET /construction-alerts` (see `docs/api-contract.md`).
- **PDF:** the finding is in the findings table with "SIMULATED" in its evidence text.

To load the new data (the schema changed: `building_snapshots` has a `ulpin` column, so re-run it, which also drops the users table):
```
docker exec -i <db-container> psql -U <POSTGRES_USER> -d <POSTGRES_DB> -v ON_ERROR_STOP=1 < db/schema.sql
python db/seed.py
python db/seed_users.py
```
`python -m backend.app.checks` prints flagged against planted per type (all equal, 10 and 10 for the new one) and the band counts.

## Frontend settings (Phase 5)
Optional variables in `frontend/.env`: `VITE_API_URL` (default `http://localhost:8000`), `VITE_DEMO_ACCOUNTS` (default off since Phase 12: the demo-login row shows only when it is exactly `true`; never set it in a real deployment), `VITE_CARTO_KEY` and `VITE_ESRI_KEY` (optional basemap keys). `npm run check:design` checks the design rules. Design notes: `docs/DESIGN_SYSTEM.md`; screenshots: `docs/screenshots/` (README) and `docs/design/screens/` (phase 9 to 11b).

## Machine learning (Phase 9)

Two things, both **advice for a human, never part of the risk score**. The score comes only from the nine checks in `backend/app/checks.py`. Models never add or remove points, change a band or change which conflicts are flagged.

### An honest caveat first
Everything here is trained and measured on **generated** data (`db/seed.py`). A model trained on generated data mostly relearns the generator: the problems are planted by simple rules, so the rules show up as odd numbers, and a model finds odd numbers easily. Good numbers below do **not** show it would work on real land records. That needs real records and a person checking the answers.

### Part A: the "unusual plot" note (unsupervised)
Commands (from the repo root, venv active; `pip install -r backend/requirements.txt`, and `pip install -r ml/requirements.txt` for the notebook):
```
python -m ml.make_dataset        # 5,000 generated plots, ~8% with a planted problem -> ml/data/ (git-ignored)
python -m ml.train_unusual       # Isolation Forest, no labels -> ml/models/unusual.joblib + unusual.json (git-ignored)
python -m ml.evaluate            # honest report on 2,000 NEW plots (labels used only here)
python -m nbconvert --to notebook --execute ml/explore.ipynb --output-dir ml/data   # or just open ml/explore.ipynb
```
- `ml/features.py` has ONE function, `plot_features`, that turns a plot into 12 numbers (area, perimeter, compactness, aspect ratio, corners, recorded/mapped area, years since tax paid, years since registration, how many plots overlap or touch it, distance to the nearest zone, area compared with its village median, an invalid-shape flag). Training and the API both use it, so they cannot drift apart. Invalid or empty shapes get safe fallback numbers plus a flag.
- The "unusual" badge goes to the top 5% of training scores (`UNUSUAL_PERCENTILE = 95` in `backend/app/config.py`). `python -m ml.evaluate` shows what other cut-offs would do.
- The API loads the model once at start-up. **No model file = `"unusual": null` and everything else works as before.** Field description: `docs/api-contract.md`. The field is not part of the tamper-evidence hash. The PDF gets one footer line only when a plot is flagged. The passport drawer shows a quiet "Unusual" chip with a tooltip.
- Reasons ("why unusual") come from SHAP (`TreeExplainer`) when `shap` is installed, otherwise from z-scores against the training median. They name numbers, never other plots.
- **Only load model files you trained yourself.** `.joblib` is Python's pickle format; loading a file runs code. Model files are git-ignored and only read from `ml/models/` (or the folder in `UNUSUAL_MODEL_DIR`). The tests set that variable to an empty folder, so no test ever loads a real model.
- Cost: each passport request builds the features for all plots (neighbours, village medians), like the scoring engine already recomputes every check per request. Fine for 100 plots; cache it if the data grows.

Results on 2,000 new generated plots (160 with a planted problem = 8.0%). The model was trained on 5,000 others (different seed):

| Cut-off | Flagged | Problem plots flagged | Clean plots flagged | Precision | vs luck |
|---|---|---|---|---|---|
| p90 | 194 | 71 of 160 (44.4%) | 123 (6.7%) | 36.6% | 4.6x |
| **p95 (used)** | 104 | 51 of 160 (31.9%) | 53 (2.9%) | 49.0% | 6.1x |
| p97 | 63 | 41 of 160 (25.6%) | 22 (1.2%) | 65.1% | 8.1x |
| p99 | 22 | 22 of 160 (13.8%) | 0 (0.0%) | 100% | 12.5x |

What it catches at p95 (plots where it is the **only** planted problem): overlap 28 of 28, tax overdue 3 of 11, area mismatch 5 of 18, invalid boundary 4 of 15, restricted zone 1 of 18, **owner mismatch 0 of 18, duplicate survey number 0 of 25, missing record 0 of 12**. The overlap result is flattering: in the generated map no two plots touch unless an overlap was planted, so "number of neighbours" gives it away. The model cannot see names, survey numbers or missing records at all.

### Part B: tuning the name matcher
```
python -m ml.make_name_pairs     # 600 labelled pairs -> ml/data/name_pairs.csv (committed: a small test asset)
python -m ml.tune_names          # train/test split, baselines, mistakes, and a decision
```
The 600 pairs (300 same person, 300 different, fixed seed) come from rules, not from real records: reordered names, initials, dropped middle names, spelling variants (Kulkarni/Kulkarny), case and punctuation noise, honorifics (Shri, Smt), and hard negatives (same surname, similar-looking names such as Patil/Patel or Anita/Sunita, different middle names). **Real-world names will behave differently.** Thresholds are picked on the 360 train pairs (best F1; ties: the middle of the tied range) and every number is measured on the 240 test pairs.

| Method (test pairs) | Threshold | Precision | Recall | F1 | TP FP FN TN |
|---|---|---|---|---|---|
| **current matcher, as shipped** | 0.60 | 0.851 | 0.858 | 0.855 | 103 18 17 102 |
| current matcher, tuned on train | 0.57 | 0.836 | 0.892 | 0.863 | 107 21 13 99 |
| exact match | n/a | 1.000 | 0.067 | 0.125 | 8 0 112 120 |
| difflib ratio | 0.37 | 0.545 | 1.000 | 0.706 | 120 100 0 20 |
| token-sorted difflib ratio | 0.73 | 0.738 | 0.917 | 0.818 | 110 39 10 81 |

Decision: **`NAME_MATCH_THRESHOLD` stays at 0.60.** Tuning gains only +0.008 F1 on the test pairs (the rule asks for at least +0.02, plus all 6 decoy pairs still matching and none of the 14 genuinely different demo pairs matching). The current matcher misses names written as only an initial plus a spelling variant plus an honorific (`Anita Joshi` vs `Mrs Joshee A.`, score 0.20) and wrongly matches near-identical different names (`Vijay Lokhande` vs `Vinay Lokhande`, 0.70).

Tests: `backend/tests/test_ml_features.py`, `test_ml_model.py`, `test_unusual_api.py`, `test_ml_names.py`.

## AI features: "Explain in plain words" and the Land Guide (Phase 11)

Two optional AI features. **The server starts and works without them** (the AI shows a friendly "AI is off" message); the risk score never depends on them.

**Turn the AI on.** Put these in `.env` (never commit it; `.env.example` has the names without values):
```
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=the-model-id-you-chose        # a free model is fine
# OPENROUTER_BASE_URL=https://openrouter.ai/api/v1   (optional)
```
Free models often answer 429 (busy) or time out. That is treated as a normal case: one retry after a short wait, then a friendly "AI is busy, try again". Whatever you send goes to a third-party service, so the app sends as little as it can (below).

### "Explain in plain words" (passport drawer, `POST /plots/{ulpin}/explain`)
It rewrites the findings a plot **already has** into plain words. It never changes, adds or removes a finding and never touches the score or the band. Only finding types, points, a few numbers and the band are sent to the AI: **no owner names, no ULPINs, no survey numbers, no villages**. If the AI is off, busy or wrong (for example it mentions a number we did not send), a template written in code is shown instead, honestly labelled "written by code, not by AI". Same role rules, 404 behaviour, audit log and rate limit as the passport.

### The Land Guide (chat panel, `POST /guide/ask`)
A chatbot that answers general questions about land records **only from a small set of public pages and the LandStack glossary**, with the source links. It uses plain word-matching search (BM25), then asks the AI to answer only from the best passages and cite them. If nothing matches it says "I don't know from my sources." (without calling the AI). It never sees plot or personal data, treats page text as data (never as instructions), and adds a "not legal advice" note. It can be wrong.

**Build its corpus (a fresh clone has none; one command):**
```
python -m chatbot.build                # scrape the listed pages (politely, cached), then rebuild the chunks
python -m chatbot.build --index-only   # no network: rebuild the chunks from what is already saved
```
Until you run it, the Guide still works from the original glossary alone (`chatbot/glossary.md`, written for LandStack, safe to commit). `pip install -r backend/requirements.txt` adds `rank_bm25` and `beautifulsoup4`. To start from scratch, delete `chatbot/raw/` and `chatbot/chunks.jsonl`.

**Sources and what they allow (checked 11 November 2026):**

| Site | robots.txt | Terms | Used? |
|---|---|---|---|
| en.vikaspedia.in (C-DAC, MeitY) | allows everything except a few named bots | reproduction allowed with clear credit to the source; third-party material excluded; the agriculture subdomain asks for permission | **Yes**, 6 `en.` land-record pages only, every answer links the page |
| dolr.gov.in (Dept. of Land Resources) | allows everything | terms could not be read (a JavaScript site) | **No, on hold.** A future source if its terms or permission are confirmed |
| igrmaharashtra.gov.in | no real rules | copyright policy: no reproduction without the department's permission | **No** |
| bhulekh.mahabhumi.gov.in | no robots.txt | no terms page found; a transactional portal with personal land records | **No** |

**Credit:** the Land Guide's answers draw on pages from **Vikaspedia (C-DAC Hyderabad, Ministry of Electronics and Information Technology, Government of India)**. The pages used are listed, with the date each was read, in `chatbot/sources.json` (committed). The raw pages and the chunks are other people's text, so they stay on your machine (`chatbot/raw/`, `chatbot/chunks.jsonl`, both git-ignored).

**The scraper is polite:** it reads only the URLs in `sources.json` (it never crawls), sends a descriptive User-Agent, waits at least 4 seconds between requests (or the site's Crawl-delay if larger), checks robots.txt, caches every page (a re-run fetches nothing new), reads at most 30 pages per run, and **stops at once on any 403 or 429**.

**Limits:** the corpus is small (6 pages and the glossary), so many questions get "I don't know from my sources". The pages are a snapshot (the DILRMP page says it is several years old). Answers can be wrong or out of date, and nothing here is legal advice. English only for now: the language step is one swappable pair of functions (`translate_to_english` and `translate_from_english` in `chatbot/guide.py`); Hindi and Marathi, with a Unicode font for the UI and the PDF, come in a later step.

## Hindi and Marathi (Phase 11b)

The Land Guide and "Explain in plain words" also work in **हिन्दी** and **मराठी**, and the printable passport can show Devanagari text correctly. English is still the default.

- **How:** you pick the language in the Land Guide panel (EN / हिन्दी / मराठी; it is never guessed, because Hindi and Marathi share a script). A Hindi or Marathi question is translated to English by the same AI, answered from the English sources with all the usual checks, and the checked answer is translated back. **Retrieval stays English-only: the corpus is not translated.** Translation is told to translate only (never answer or add anything) and must keep every `[n]` source marker and every number; if it does not, you get the English answer with a short note. Explanations work the same way (only the validated English explanation is translated; the code-written fallback stays English). The score and findings never change.
- **Quality depends on the free model you choose.** Free models can be weak at Hindi and especially Marathi, and can be busy. Translated AI text is always labelled "machine-translated, may contain errors" in the user's language. If the AI is off or busy you get the English text and a note in your language.
- **Fixed sentences are not machine-translated.** Every fixed Hindi and Marathi sentence (the panel's labels, notes, the "not legal advice" note and "I don't know from my sources") is in one file, `chatbot/strings.json`, written by a person (not by an AI each time). **It has not been reviewed by a native speaker yet: please have it reviewed before real use.**
- **Scope:** only the Land Guide panel and the Explain section are translated. **Full-app translation is out of scope**; the rest of LandStack stays English.
- **Fonts (all SIL Open Font License 1.1):** *Noto Sans Devanagari*, Copyright The Noto Project Authors. In the web app it is self-hosted from the `@fontsource/noto-sans-devanagari` npm package (Devanagari subset only, no CDN). In the PDF, `backend/app/fonts/` holds two small static files (Regular and Bold, about 170 KB each, cut from the upstream variable font) with `OFL.txt` and a README on how they were made.
- **The PDF stays English otherwise.** Plain ReportLab cannot shape Devanagari (it would print हिन्दी as हन्िदी), so `backend/app/devanagari.py` shapes with HarfBuzz (`uharfbuzz`, plus `fonttools`) and draws each letter's outline as a vector path with the non-zero fill rule. Used for any text that contains Devanagari: an owner name, a village, evidence that quotes a name. If the font or the shaper is missing, or the font lacks a letter, the Devanagari part is replaced by "(Devanagari text: see the digital passport)": never an empty box. Sample: [docs/samples/passport_marathi_owner.pdf](docs/samples/passport_marathi_owner.pdf) (Marathi owner names and village on a real plot's layout). It is a layout sample made from the code, not through the API, so its QR code will not verify.
- **Setup:** `pip install -r backend/requirements.txt` (adds `uharfbuzz` and `fonttools`) and `cd frontend && npm install` (adds the font package).

## Phase 12 (hardening, naming, README, demo)
- **Naming:** LandStack everywhere a reader sees it.
- **Hardening:** CORS only for `CORS_ORIGINS` (default `http://localhost:5173`; a wildcard or malformed value stops the server); exact version pins in `backend/requirements.txt` and `ml/requirements.txt` (tested on Python 3.14.7); the demo login row only when `VITE_DEMO_ACCOUNTS` is exactly `true`; a test that walks every endpoint as a citizen and a visitor; tests that error responses leak no stack trace, SQL or host details. `pip-audit` and `npm audit` were clean.
- **Three small features:** a friendly HTML page at `GET /verify/{doc_id}` (browsers get HTML, programs get JSON; see `backend/app/verify_page.py`); a `capped` flag (API, drawer, PDF note, not part of the tamper-evidence hash); an `X-Document-Id` header on the PDF response.
- **Repo polish:** `LICENSE` (MIT), `THIRD_PARTY.md`, `.github/workflows/ci.yml`, `scripts/setup.ps1` and `scripts/setup.sh`, `docs/DEMO.md`, curated `docs/screenshots/`, regenerated `docs/samples/`.
