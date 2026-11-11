# LandStack API contract (Phases 3, 7 and 8)

JSON API over the seeded fake data. Build against this file; it is checked against the code by `backend/tests/test_api.py` and `backend/tests/test_auth.py`. Every endpoint except `/health` and `POST /auth/login` needs a login (see below).

- **Run:** `uvicorn backend.app.main:app --reload` (from the repo root, venv active). Base URL `http://localhost:8000`.
- **Live docs:** `http://localhost:8000/docs` (Swagger UI), `http://localhost:8000/redoc`, raw spec at `/openapi.json`.
- **CORS:** only `http://localhost:5173` (the Vite dev server) may call it from a browser. GET and POST are allowed, with the `Authorization` and `Content-Type` headers. The `Retry-After` header is readable by the page.
- **Start-up:** the server refuses to start unless `JWT_SECRET` (a long random value, not the placeholder) is set in `.env` or the environment. `PUBLIC_BASE_URL` (default `http://localhost:8000`) is the web address put into the QR code of printed passports.
- **Scores** are computed fresh on every request by the Phase 2 engine. Do not compute scores in the frontend.
- **Coordinates** are GeoJSON `[longitude, latitude]` (SRID 4326), around lon 73.80, lat 18.55 (Pune).

## Authentication, roles and limits (Phase 7)

**Logging in.** `POST /auth/login` with a username and password returns an `access_token`. Send it on every other request as `Authorization: Bearer <access_token>`. A token lasts 60 minutes (`expires_in` says how many seconds; the length comes from `JWT_EXPIRE_MINUTES` in `.env`). The token is signed, not secret: it holds the username, role and expiry. The server still looks the user up on every request and uses the role stored in the database, so a changed role or a deleted user takes effect at once.

**Roles and what each may do** (a dash means "not allowed"; "401" is for someone who is not logged in at all):

| Endpoint | Not logged in | citizen | officer | admin |
|---|---|---|---|---|
| `GET /health` | 200 | 200 | 200 | 200 |
| `POST /auth/login` | open | open | open | open |
| `GET /auth/me` | 401 | 200 | 200 | 200 |
| `GET /conflict-types` | 401 | 200 | 200 | 200 |
| `GET /plots` | 401 | 200, **only their own plots** | 200, all plots | 200, all plots |
| `GET /construction-alerts` (SIMULATED) | 401 | 200, **only their own plots** | 200, all plots | 200, all plots |
| `POST /plots/{ulpin}/explain` (Phase 11) | 401 | 200 for their own plot; **404 for any other plot** | 200 (404 only if it does not exist) | 200 (404 only if it does not exist) |
| `POST /guide/ask` (Phase 11) | 401 | 200 | 200 | 200 |
| `GET /plots/{ulpin}` | 401 | 200 for their own plot; **404 for any other plot** | 200 (404 only if it does not exist) | 200 (404 only if it does not exist) |
| `GET /plots/{ulpin}/passport.pdf` | 401 | 200 for their own plot; **404 for any other plot** | 200 (404 only if it does not exist) | 200 (404 only if it does not exist) |
| `GET /verify/{doc_id}` | 200 (public, strict limit) | 200 | 200 | 200 |
| `GET /summary` | 401 | **403** | 200 | 200 |
| `GET /audit` | 401 | **403** | **403** | 200 |

**Citizens never learn which other plots exist.** A plot that is not theirs returns exactly the same `404` as a plot that does not exist (not `403`). In a citizen's findings, any other plot's ULPIN in the evidence text is replaced by "another plot" (so "overlaps plot MH000400000070 by 656 sq m" becomes "overlaps another plot by 656 sq m"). Scores, points and bands are never changed.

**Audit log.** Every `GET /plots/{ulpin}` writes one audit row: who, their role, which ulpin, when, and what happened: `view_passport` (shown), `view_passport_denied` (a citizen asked for a plot that is not theirs, or one that does not exist) or `view_passport_not_found` (an officer or admin asked for a plot that does not exist). A PDF download is logged the same way, with `download_passport_pdf`, `download_passport_pdf_denied` and `download_passport_pdf_not_found`. `POST /plots/{ulpin}/explain` is logged the same way too (`explain_passport`, `explain_passport_denied`, `explain_passport_not_found`), and every `POST /guide/ask` writes one `guide_ask` row with no ulpin and **no question text** (the audit log never stores what was asked). Listing plots and other calls are not logged. If writing the row fails, the request still works and the failure goes to the server log.

**Rate limits.** `POST /auth/login`: 5 per minute per IP address. Everything else: 60 per minute per logged-in user, as one allowance shared by all endpoints (per IP address if the request has no valid token). A blocked request gets `429` with a `Retry-After` header (whole seconds) and `{"detail": "Too many requests. Please wait 31 seconds and try again."}`. `GET /verify/{doc_id}` (public, so strict): 10 per minute per IP address, with its own counter. Counters are per endpoint, not per URL, so trying many different document ids is limited too. The limits live in `backend/app/config.py`.

**Secrets.** Passwords are stored only as argon2 hashes. No endpoint ever returns a password or a hash, and passwords are never logged.

## Shared values

| Name | Values |
|---|---|
| `band` | `green` (score 0-24), `amber` (25-59), `red` (60-100) |
| `conflict type` | `boundary_overlap`, `restricted_zone_clash`, `area_mismatch`, `owner_mismatch`, `duplicate_survey_no`, `invalid_boundary`, `tax_overdue`, `missing_record`, `unrecorded_construction` (**SIMULATED**, Phase 10) (get points, descriptions and the `simulated` marker from `/conflict-types`) |
| `ulpin` | 14 capital letters/digits, e.g. `MH000100000001` |

Finding object: `{"type": <conflict type>, "points": <int>, "evidence": <plain-text facts with real numbers>}`.

## Error format (all endpoints)

Every error is JSON with a `detail` field. Stack traces are never returned (they go to the server log).

| Status | When | Body |
|---|---|---|
| 401 | no token, or a bad / expired / tampered token | `{"detail": "Not authenticated"}` or `{"detail": "Invalid or expired token"}` (with a `WWW-Authenticate: Bearer` header). A failed login: `{"detail": "Incorrect username or password"}`, the same text for a wrong password and an unknown user |
| 403 | logged in, but the role is not allowed | `{"detail": "You do not have permission to do this."}` |
| 404 | unknown ulpin, **or a citizen asking for a plot that is not theirs** (the two look identical) | `{"detail": "No plot found with ulpin MH999999999999"}` |
| 429 | rate limit hit | `{"detail": "Too many requests. Please wait 31 seconds and try again."}` plus a `Retry-After` header |
| 422 | bad path/query value (malformed ulpin, unknown `band` or `conflict_type`) | `{"detail": [{"type": "string_pattern_mismatch", "loc": ["path", "ulpin"], "msg": "String should match pattern '^[A-Z0-9]{14}$'", "input": "bad", "ctx": {...}}]}` (FastAPI's standard list of problems) |
| 503 | database is not reachable | `{"detail": "Database unavailable"}` |
| 500 | anything unexpected | `{"detail": "Internal server error"}` |

---

## GET /health

**Who:** everyone, no login. Confirms the API is up and the database answers.

- Parameters: none
- 200: `{"status": "ok", "database": "ok"}`
- Errors: 429, 503

## GET /plots

**Who:** any logged-in user. Plots as a GeoJSON FeatureCollection, ordered by ulpin. A **citizen gets only the plots they own** (the filters below work inside that set; a citizen with no plots gets an empty list); officers and admins get all plots. Filters combine with AND.

| Query param | Type | Meaning |
|---|---|---|
| `band` | `green` / `amber` / `red` | only plots in this band |
| `village` | text | only plots in this village (exact, case-sensitive; unknown village gives an empty list) |
| `conflict_type` | a conflict type | only plots with at least one finding of this type |

Example `GET /plots?band=amber&conflict_type=boundary_overlap` (geometry shortened, 6 features in the real response):

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[73.80177771, 18.55120423], "... 4 more points, first point repeated last"]]
      },
      "properties": {
        "ulpin": "MH000100000015",
        "village": "Hinjewadi",
        "land_use": "residential",
        "survey_no": "114/7",
        "score": 40,
        "band": "amber"
      }
    }
  ]
}
```

Notes: features have no top-level `id`; with MapLibre use `promoteId: "ulpin"`. Plots with an `invalid_boundary` finding have a self-intersecting (bow-tie) polygon; it is still a valid GeoJSON Polygon and can be drawn. Errors: 401, 422 (bad `band` or `conflict_type`), 429, 503.

## GET /plots/{ulpin}

**Who:** any logged-in user; a citizen only for their own plots. The land passport for one plot. Each call is written to the audit log (see above).

| Path param | Type | Meaning |
|---|---|---|
| `ulpin` | 14 capital letters/digits | the plot id |

Fields: plot facts (`ulpin`, `village`, `land_use`, `survey_no`, `geometry`, `area_sqm`), the three records (`ror`, `registration`, `tax`; each is `null` when that record is missing), `score`, `band`, `findings`, and `unusual` (Phase 9, see below). `area_sqm` is the real area in square metres, or `null` when the boundary shape is invalid. If a plot has several rows of a record type, the latest one is shown.

Example `GET /plots/MH000100000006` (a red plot with four problems; geometry shortened):

```json
{
  "ulpin": "MH000100000006",
  "village": "Hinjewadi",
  "land_use": "industrial",
  "survey_no": "105/8",
  "area_sqm": 1848.6587559729815,
  "geometry": {"type": "Polygon", "coordinates": [[[73.8061975, 18.55022193], "..."]]},
  "ror": {"owner_name": "Amit More", "recorded_area_sqm": 1447.1},
  "registration": {"owner_name": "Swati Thorat", "registered_on": "2014-01-26"},
  "tax": {"paid_until": "2026-12-10"},
  "score": 100,
  "band": "red",
  "findings": [
    {"type": "boundary_overlap", "points": 40, "evidence": "overlaps plot MH000200000025 by 647 sq m (35% of this plot)"},
    {"type": "area_mismatch", "points": 25, "evidence": "record says 1,447 sq m but the mapped plot is 1,849 sq m (-22%); limit is 10%"},
    {"type": "owner_mismatch", "points": 25, "evidence": "record owner 'Amit More' vs registration owner 'Swati Thorat'; name similarity 0.05 (needs 0.60)"},
    {"type": "duplicate_survey_no", "points": 20, "evidence": "survey number 105/8 in Hinjewadi is also used by plot MH000400000063"}
  ]
}
```

A plot can have findings of several different types (up to four in the demo data). The points of all findings are added and the score stops at 100: here 40 + 25 + 25 + 20 = 110, shown as 100. A plot has at most one finding per type. A missing record shows as `"ror": null` (or `registration`, or `tax`) plus a `missing_record` finding. A clean plot has `"score": 0, "band": "green", "findings": []`.

The `boundary_overlap` evidence is worded by what kind of overlap it is: `overlaps plot X by 647 sq m (35% of this plot)` (a partial overlap), `lies completely inside plot X (470 sq m, all of this plot)`, `plot X lies completely inside this plot (470 sq m, 25% of this plot)`, or `has exactly the same boundary as plot X (1,850 sq m)`. Two plots count as overlapping only if they share at least 5 square metres of ground; plots that only touch along an edge or at a corner are not flagged.

For a citizen, the evidence text never contains another plot's ULPIN (it says "another plot"), for example `{"type": "boundary_overlap", "points": 40, "evidence": "overlaps another plot by 656 sq m (35% of this plot)"}`.

### The `unusual` field (Phase 9)

A statistical hint from an Isolation Forest, **not a conflict**. It adds **no points**, never changes `score`, `band` or `findings`, and is **not part of the tamper-evidence hash** (so retraining or removing the model never makes an old printed passport say "records have changed").

| Value | Meaning |
|---|---|
| `null` | no model file is installed (or it could not be loaded, or the note failed). The API works exactly as before. |
| `{"flag": false, "percentile": 19.9, "reasons": []}` | not unusual |
| `{"flag": true, "percentile": 100.0, "reasons": ["It overlaps or touches 1 other plot (typical 0)", "..."]}` | unusual: its score is in the top 5% (`config.UNUSUAL_PERCENTILE`) of the model's training plots |

- `flag`: true when the plot is unusual compared with other plots.
- `percentile`: 0 to 100, the share of the model's **training** plots that are *less* unusual than this one (100 = more unusual than every training plot). Not a probability, and not a chance of a conflict.
- `reasons`: up to 3 plain-English lines (from SHAP, or z-scores if `shap` is not installed), **only when `flag` is true**. They describe numbers (area, shape, neighbours, tax age...) and never name another plot, so a citizen's copy is safe.
- The PDF shows one extra footer line, "Statistical note: unusual compared with other plots; not a conflict; adds no points.", **only** when `flag` is true.
- Training data is generated demo data, so this is a hint for a human to look at, never a verdict.

Example (a red plot that is also unusual; geometry left out):

```json
{"ulpin": "MH000100000001", "score": 75, "band": "red", "area_sqm": 977.3369431346655,
 "unusual": {"flag": true, "percentile": 100.0, "reasons": [
   "It overlaps or touches 1 other plot (typical 0)",
   "Tax is paid only up to 4.6 years before the reference date (typical 0.0)",
   "The boundary is 125 m long, lower than typical (160 m)"]}}
```

Errors: 401, 404 (unknown ulpin, or a citizen asking for a plot that is not theirs), 422 (malformed ulpin; nothing is audited), 429, 503.

## GET /summary

**Who:** officer and admin only (citizens get 403). Counts for the whole data set.

- Parameters: none
- 200:

```json
{
  "total_plots": 100,
  "plots_per_band": {"green": 58, "amber": 29, "red": 13},
  "findings_per_type": {
    "boundary_overlap": 14,
    "restricted_zone_clash": 12,
    "area_mismatch": 12,
    "owner_mismatch": 14,
    "duplicate_survey_no": 8,
    "invalid_boundary": 4,
    "tax_overdue": 6,
    "missing_record": 4,
    "unrecorded_construction": 10
  }
}
```

`findings_per_type` counts findings, not plots. Because a plot has at most one finding per type, each number is also the number of plots with that problem (a plot with several problems is counted once under each). All three bands and all nine types are always present, with `0` when empty. (Numbers shown are for the default seed: 100 plots, seed 42.) Errors: 401, 403, 429, 503.

## GET /conflict-types

**Who:** any logged-in user. The nine conflict types in a fixed order (highest points first, the newest last), so the frontend never hard-codes them.

- Parameters: none
- 200: a list of `{"type", "points", "description", "simulated"}`, for example:

```json
[
  {"type": "boundary_overlap", "points": 40, "description": "This plot overlaps another plot, or lies inside it, or has another plot inside it.", "simulated": false},
  {"type": "restricted_zone_clash", "points": 30, "description": "More than 20% of the plot lies inside a restricted zone.", "simulated": false},
  {"type": "unrecorded_construction", "points": 15, "description": "SIMULATED: at least 30 sq m of building appears in the later survey snapshot (T1) that is not in the earlier one (T0). There is no real satellite or imagery data behind this.", "simulated": true}
]
```

The real response has all nine entries (the rest: `area_mismatch` 25, `owner_mismatch` 25, `duplicate_survey_no` 20, `invalid_boundary` 15, `tax_overdue` 15, `missing_record` 10 per missing record). `simulated` is `true` only for `unrecorded_construction`: **the data behind that check is generated, not real**. The score caps at 100. Errors: 401, 429.

## The unrecorded-construction alert (Phase 10, SIMULATED)

**Everything about this feature is simulated.** There is no real satellite or aerial imagery anywhere in the project. `db/seed.py` generates two snapshots of building outlines for every plot, `T0` (earlier) and `T1` (later), in the table `building_snapshots`. It plants about 10 plots with a new building in T1 (the alerts) and about 8 plots whose buildings only shifted a little between the snapshots (survey jitter, which must NOT be flagged).

- **The check** (`check_unrecorded_construction`, raw PostGIS in `backend/app/checks.py`): per plot, the T1 footprints minus the T0 footprints (`ST_Difference`), measured in square metres through a geography cast. A plot is flagged when that new built area is **at least `MIN_NEW_BUILT_SQM` = 30 sq m**. Plots with an invalid shape are skipped. A building in both snapshots, or one removed in T1, is not new.
- **Points:** `CONSTRUCTION_ALERT_POINTS` = **15**, fixed, added like every other finding (the cap at 100 still holds). No model or LLM changes it.
- **Finding:** type `unrecorded_construction`, evidence like `"SIMULATED: about 61 sq m of new building appeared between T0 and T1 that is not in the records; limit is 30 sq m (no real imagery is used)"`. It appears in the passport, the PDF findings table, `/summary` (`findings_per_type`) and the `conflict_type` filter of `GET /plots` like any other type. The evidence never names another plot, so citizens see it unchanged.

### GET /construction-alerts

**Who:** any logged-in user. A **citizen gets only the footprints on their own plots**; officers and admins get all of them. Not audited (it is a list, like `/plots`). The outlines of the new buildings behind the alerts, as a GeoJSON FeatureCollection for the map. Only plots that have an alert appear, so the jitter plots never do.

```json
{
  "type": "FeatureCollection",
  "features": [
    {"type": "Feature",
     "geometry": {"type": "Polygon", "coordinates": [[[73.80213, 18.55105], "... 3 more points, first point repeated last"]]},
     "properties": {"ulpin": "MH000100000008", "new_sqm": 60.6, "piece_sqm": 60.6, "simulated": true}}
  ]
}
```

`new_sqm` is the new built area on the whole plot (the number in the evidence); `piece_sqm` is the area of this one outline (a plot with two new buildings has two features). `simulated` is always `true`. Errors: 401, 429, 503.

## POST /plots/{ulpin}/explain (Phase 11)

**Who:** the same as the passport: any logged-in user, a citizen only for their own plots (any other plot is the same `404` as a plot that does not exist). Same audit log and the same shared 60 per minute allowance. No request body (send `{}` or nothing).

"Explain in plain words": it rewrites the findings the plot **already has** into plain words. **It never changes, adds or removes a finding and never touches the score or the band**: it only reads the passport. Only finding types, points, a few numbers and the band go to the AI, **never owner names, ULPINs, survey numbers or villages** (evidence text is not sent; per-type patterns pull out the numbers only). If the AI is off, busy or fails, or if its text contains a number we did not send, a link or a ULPIN-looking id, a **template written in code** is returned instead.

```json
{"text": "This plot has a high risk rating: score 100 out of 100, red band.\n4 findings explain the score:\n- ...",
 "source": "template", "ai_status": "off",
 "label": "Plain-words summary of the findings above (written by code, not by AI)",
 "notice": "AI is off, so this summary was written by code."}
```

| Field | Values |
|---|---|
| `source` | `ai` (the AI wrote it) or `template` (written in code) |
| `ai_status` | `on`, `off` (no `OPENROUTER_API_KEY` or `OPENROUTER_MODEL`), `busy` (429, a server error or a timeout, even after one retry) or `failed` (any other problem, or its text was rejected) |
| `label` | `AI-written summary of the findings above` when `source` is `ai`, otherwise the honest code-written label; the UI shows it |
| `notice` | a friendly sentence when the AI was not used, else `null` |

Errors: 401, 404, 422 (malformed ulpin or an unknown `lang`; nothing is audited), 429, 503. The AI being down is never an error: you get the template with `200`.

### Hindi and Marathi (Phase 11b)
An optional request body `{"lang": "hi"}` (`en` is the default and the same as sending nothing; also `mr`). It is chosen by the user, never guessed. The **English** explanation is built and validated first, exactly as before (only the same allowlisted facts go to the AI); only that validated text is then translated, and the translation must keep every number and the same lines and bullet points. The code-written template stays English. For `hi` or `mr` the response has three extra fields (English requests are unchanged): `language`, `translation` (`machine` or `unavailable`) and `translation_note` (`null`, `ai_off`, `ai_busy` or `check_failed`). `label` stays the English sentence; the UI shows its own Hindi or Marathi label for `source`. The score, band and findings are never touched, in any language.

## POST /guide/ask (Phase 11)

**Who:** any logged-in user (401 otherwise). Shares the 60 per minute per-user allowance. Each call writes one `guide_ask` audit row with no ulpin and no question text.

The Land Guide answers a **general** question about land records ONLY from a small set of public pages (Vikaspedia, C-DAC) and the original LandStack glossary. **It never sees any plot or personal data**: the only input is the question; plot ids, e-mail addresses and long digit runs are removed from it before anything is sent; do not type personal details. Request: `{"question": "What is a ULPIN?", "language": "en"}` (1 to 500 characters, else `422`). `language` is `en` (default), `hi` or `mr`: the language the question is written in and the answer should come back in. **It is chosen by the user and never guessed** (Hindi and Marathi share a script); anything else is `422`.

```json
{"answer": "A ULPIN is a 14-character alphanumeric code that identifies one land parcel [1].",
 "status": "answered", "ai_status": "on",
 "sources": [{"n": 1, "title": "Bhu-Aadhaar | Vikaspedia - English - Digital Governance",
              "url": "https://en.vikaspedia.in/viewcontent/e-governance/online-citizen-services/government-to-citizen-services-g2c/all-about-aadhaar/bhu-aadhaar?lgn=en",
              "retrieved": "2026-11-11"}],
 "disclaimer": "This is general information from the sources listed, not legal advice. ..."}
```

| `status` | Meaning |
|---|---|
| `answered` | an AI answer written only from the sources, each claim tied to `[n]`; `sources` lists the pages it cited |
| `no_sources` | **"I don't know from my sources."** Nothing covers the question (the AI is not even called), or its answer was not grounded (no valid `[n]`, a number that is in no source, or an obeyed injected instruction) |
| `ai_off`, `ai_busy`, `ai_failed` | the AI could not write an answer. A friendly sentence is returned and `sources` lists the related pages (title and link only) |

Source text is treated as **data, never instructions** (it is stripped of anything that could close a block, the prompt says to ignore instructions inside it, and the answer is checked afterwards); links are removed from the answer (the sources are listed separately). `url` is `null` for the "LandStack glossary", which has no web page. Every answer carries a `disclaimer`: general information, not legal advice. Errors: 401, 422, 429.

### Hindi and Marathi (Phase 11b)
Retrieval stays **English-only**: the corpus is not translated. For `hi` or `mr` the flow is: question translated to English (translate-only prompt, through the same LLM client) -> the usual retrieval and grounded answer **with all the checks run on the English answer** -> the checked answer is translated back. The translation must keep **every `[n]` marker (same order) and every number** (Devanagari digits ०-९ are read as 0-9 for the comparison) and be mostly in the target language; otherwise the English answer is returned with a note. The `disclaimer` and "I don't know from my sources." are sentences written by a person (`chatbot/strings.json`), not machine-translated.

For `hi` or `mr` the response has three extra fields (English requests are unchanged):

| Field | Values |
|---|---|
| `language` | `hi` or `mr` |
| `translation` | `machine` (machine-translated: the UI shows "machine-translated, may contain errors"), `fixed` (a person-written sentence), `unavailable` (the English text is shown), `none` |
| `translation_note` | `null`, or why English is shown: `ai_off`, `ai_busy` or `check_failed` (a marker, a number or the language changed). The UI turns the code into a sentence in the user's language |

If the **question itself** cannot be translated (the AI is off or busy, or the translation fails its checks) there is nothing to retrieve with, so the answer is the English message (`status` `ai_off`, `ai_busy` or `ai_failed`), `sources` is empty and `translation` is `unavailable`. Sources are never translated (their titles are English). The audit row is the same `guide_ask` (no question, no language).

## POST /auth/login

**Who:** everyone (no token needed). Limited to 5 requests per minute per IP address.

Request body (JSON): `{"username": "citizen1", "password": "..."}` (1 to 64 characters for the username, 1 to 256 for the password).

- 200:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {"username": "citizen1", "role": "citizen"}
}
```

- Errors: 401 `{"detail": "Incorrect username or password"}` (identical for a wrong password and an unknown username), 422 (missing or too long fields), 429.

## GET /auth/me

**Who:** any logged-in user. Who does the server think I am?

- 200: `{"username": "citizen1", "role": "citizen"}` (`role` is `admin`, `officer` or `citizen`)
- Errors: 401, 429

## GET /audit

**Who:** admin only (officers and citizens get 403). The audit log, newest first.

| Query param | Type | Meaning |
|---|---|---|
| `username` | text | only this user's views |
| `ulpin` | text | only views of this plot |
| `limit` | 1 to 500 (default 100) | how many rows |

- 200: a list, for example:

```json
[
  {"id": 12, "username": "citizen1", "role": "citizen", "ulpin": "MH000100000003",
   "action": "view_passport_denied", "looked_at": "2026-11-10T21:48:22.514213Z"},
  {"id": 11, "username": "officer", "role": "officer", "ulpin": "MH000100000012",
   "action": "view_passport", "looked_at": "2026-11-10T21:48:20.101877Z"}
]
```

`action` is one of `view_passport`, `view_passport_denied`, `view_passport_not_found`, `download_passport_pdf`, `download_passport_pdf_denied`, `download_passport_pdf_not_found`, `explain_passport`, `explain_passport_denied`, `explain_passport_not_found`, `guide_ask`. `looked_at` is an ISO 8601 time (UTC). Errors: 401, 403, 422 (bad `limit`), 429, 503.

## GET /plots/{ulpin}/passport.pdf

**Who:** any logged-in user, with the same rules as `GET /plots/{ulpin}`: a citizen only for their own plots (any other plot is the same 404 as an unknown one, and other plots' ids are replaced by "another plot" in the printed evidence); officers and admins for any plot. Limited like every other endpoint (60 per minute per user).

The printable land passport: one A4 page. It shows the demo-data notice, plot facts, the boundary as vector lines (drawn even for an invalid shape, labelled "INVALID BOUNDARY"), the score badge with the band written in words, the findings table (or "No conflicts found"), the three records ("Missing" when absent), a QR code, the document id, the generated time (UTC) and the user who generated it.

- 200: `Content-Type: application/pdf`, `Content-Disposition: attachment; filename="landpassport_<ulpin>.pdf"`, `Cache-Control: no-store`. The body starts with `%PDF`.
- Each successful download inserts one `passport_issues` row (document id, ulpin, username, time, SHA-256 of the passport data) and writes one audit row. The hash covers the real, un-hidden data (sorted JSON, no timestamps of ours), even when a citizen downloads, so `/verify` can recompute it. If the PDF cannot be built, no issue row is kept (the attempt is still audited).
- The QR code holds `{PUBLIC_BASE_URL}/verify/{doc_id}`.
- Errors: 401, 404 (unknown plot, or a citizen asking for a plot that is not theirs), 422 (malformed ulpin), 429, 500 (`{"detail": "Internal server error"}`), 503.
- A PDF cannot show more than about 6 findings once the rows are long; extra findings are replaced by a line "+ N more finding(s) not shown. See the digital passport." (seeded data has at most one finding per plot).

## GET /verify/{doc_id}

**Who:** everyone, **no login**. Limited to **10 per minute per IP address**. Does a printed passport still match the records?

| Path param | Type | Meaning |
|---|---|---|
| `doc_id` | 4 to 40 letters, digits or `-` (not case sensitive) | the document id printed on the passport, e.g. `7KQ2-M9XD-4TPA` |

- 200 (the records still match):

```json
{"valid": true, "ulpin": "MH000100000012", "issued_at": "2026-11-09T22:22:23.154685Z", "status": "matches"}
```

- 200 (something changed since it was printed): `{"valid": false, "ulpin": "...", "issued_at": "...", "status": "records have changed since this was issued"}`

`valid` is true only when `status` is `"matches"`. The answer deliberately contains nothing else: no owner names, no evidence, no score, no band. Anyone holding the paper (or finding the id) learns only that the document is genuine and whether it is still current.

- Errors: 404 `{"detail": "No document found with that id"}` (an id that was never issued), 422 (not shaped like an id), 429 `Retry-After` header, 503.

## Phase 12 (checkpoint 1) changes
- `GET /verify/{doc_id}`: same URL. Programs (no `Accept`, `*/*`, `application/json`) still get the JSON. A browser (`Accept: text/html`) gets a small page: MATCHES / HAS CHANGED / NOT FOUND, the plot id, issue time and document id only. No scripts, strict `Content-Security-Policy`, `nosniff`, `no-store`. A browser asking for an unknown id gets the page with status 404.
- `GET /plots/{ulpin}` (and the explain/passport data): new field `capped` (bool): the findings' points add up to more than 100, so the score is held at 100. It is NOT part of the tamper-evidence hash.
- `GET /plots/{ulpin}/passport.pdf`: new response header `X-Document-Id` (the id printed on the page and in its QR code). Exposed to browsers through CORS. The PDF shows "Capped at 100: findings add up to N" when `capped` is true.
- CORS: allowed origins come from `CORS_ORIGINS` (comma separated, default `http://localhost:5173`). A wildcard or malformed value stops the server from starting.

## Phase 13a: two public endpoints (no login, no AI)

> **Note: these two endpoints are open to everyone.** Even with the rate limits they confirm that a plot id exists and show its village and risk band (never anything else). That is deliberate: it powers the "Check a plot" card on the public home page.

Both are read-only, limited **per IP address** (so a bulk scrape is cut off), never read the login token (a citizen's or officer's token changes nothing) and never call the AI. They are not written to `audit_log` (its `username` column is required, and the schema did not change); the server only counts the calls in memory and logs the totals, never the ids that were asked for.

### GET /public/stats
Counts only. Cached for about 60 seconds. Limit `RATE_PUBLIC_STATS` = 30 per minute per IP.
```json
{"total_plots": 100, "plots_per_band": {"green": 58, "amber": 29, "red": 13}}
```
The fields are exactly those two (no extras are ever added: the response model forbids them). Errors: 429, 503.

### GET /public/plot/{ulpin}
Returns **only** `ulpin`, `village` and `band`: no names, evidence, survey numbers, scores, areas, geometry or ids.
```json
{"ulpin": "MH000100000006", "village": "Hinjewadi", "band": "red"}
```
- The id must be 14 capital letters or digits. A malformed id and an unknown id get the **same** answer, `404 {"detail": "No plot found"}` (there is no 422 here, so the answer reveals nothing).
- Limit `RATE_PUBLIC_PLOT` = 20 per minute per IP, one counter for the whole endpoint (not one per id). Over the limit: 429 with `Retry-After`.
- `band` is the same band `GET /plots` shows for staff.

### Other changes in 13a
- The app has real URLs now: `/`, `/login`, `/how-it-works`, `/about`, `/verify` (a friendly page that calls `GET /verify/{doc_id}` asking for JSON), and the protected `/app/*`. The API is unchanged apart from the two endpoints above.
- `GET /verify/{doc_id}` is called by the web app with `Accept: application/json`, so it always gets JSON even though the same URL returns a web page to a browser.
- API title version is now 0.13.1.
