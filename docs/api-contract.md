# LandStack API contract (Phases 3 and 7)

JSON API over the seeded fake data. Build against this file; it is checked against the code by `backend/tests/test_api.py` and `backend/tests/test_auth.py`. Every endpoint except `/health` and `POST /auth/login` needs a login (see below).

- **Run:** `uvicorn backend.app.main:app --reload` (from the repo root, venv active). Base URL `http://localhost:8000`.
- **Live docs:** `http://localhost:8000/docs` (Swagger UI), `http://localhost:8000/redoc`, raw spec at `/openapi.json`.
- **CORS:** only `http://localhost:5173` (the Vite dev server) may call it from a browser. GET and POST are allowed, with the `Authorization` and `Content-Type` headers. The `Retry-After` header is readable by the page.
- **Start-up:** the server refuses to start unless `JWT_SECRET` (a long random value, not the placeholder) is set in `.env` or the environment.
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
| `GET /plots/{ulpin}` | 401 | 200 for their own plot; **404 for any other plot** | 200 (404 only if it does not exist) | 200 (404 only if it does not exist) |
| `GET /summary` | 401 | **403** | 200 | 200 |
| `GET /audit` | 401 | **403** | **403** | 200 |

**Citizens never learn which other plots exist.** A plot that is not theirs returns exactly the same `404` as a plot that does not exist (not `403`). In a citizen's findings, any other plot's ULPIN in the evidence text is replaced by "another plot" (so "overlaps plot MH000400000070 by 656 sq m" becomes "overlaps another plot by 656 sq m"). Scores, points and bands are never changed.

**Audit log.** Every `GET /plots/{ulpin}` writes one audit row: who, their role, which ulpin, when, and what happened: `view_passport` (shown), `view_passport_denied` (a citizen asked for a plot that is not theirs, or one that does not exist) or `view_passport_not_found` (an officer or admin asked for a plot that does not exist). Listing plots and other calls are not logged. If writing the row fails, the request still works and the failure goes to the server log.

**Rate limits.** `POST /auth/login`: 5 per minute per IP address. Everything else: 60 per minute per logged-in user, as one allowance shared by all endpoints (per IP address if the request has no valid token). A blocked request gets `429` with a `Retry-After` header (whole seconds) and `{"detail": "Too many requests. Please wait 31 seconds and try again."}`. The limits live in `backend/app/config.py`.

**Secrets.** Passwords are stored only as argon2 hashes. No endpoint ever returns a password or a hash, and passwords are never logged.

## Shared values

| Name | Values |
|---|---|
| `band` | `green` (score 0-24), `amber` (25-59), `red` (60-100) |
| `conflict type` | `boundary_overlap`, `restricted_zone_clash`, `area_mismatch`, `owner_mismatch`, `duplicate_survey_no`, `invalid_boundary`, `tax_overdue`, `missing_record` (get points and descriptions from `/conflict-types`) |
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

Example `GET /plots?band=amber&conflict_type=boundary_overlap` (geometry shortened, 8 features in the real response):

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
        "ulpin": "MH000100000012",
        "village": "Hinjewadi",
        "land_use": "agricultural",
        "survey_no": "111/9",
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

Fields: plot facts (`ulpin`, `village`, `land_use`, `survey_no`, `geometry`, `area_sqm`), the three records (`ror`, `registration`, `tax`; each is `null` when that record is missing), `score`, `band`, and `findings`. `area_sqm` is the real area in square metres, or `null` when the boundary shape is invalid. If a plot has several rows of a record type, the latest one is shown.

Example `GET /plots/MH000100000001` (a plot with no RoR record; geometry shortened):

```json
{
  "ulpin": "MH000100000001",
  "village": "Hinjewadi",
  "land_use": "residential",
  "survey_no": "100/4",
  "area_sqm": 1376.7031198441982,
  "geometry": {"type": "Polygon", "coordinates": [[[73.80054491, 18.55010454], "..."]]},
  "ror": null,
  "registration": {"owner_name": "Ganesh Bhosale", "registered_on": "2014-09-22"},
  "tax": {"paid_until": "2026-01-06"},
  "score": 10,
  "band": "green",
  "findings": [
    {
      "type": "missing_record",
      "points": 10,
      "evidence": "no RoR record found for this plot (ror_records is empty)"
    }
  ]
}
```

A present `ror` looks like `{"owner_name": "Kavita Mane", "recorded_area_sqm": 1845.65}`. A clean plot has `"score": 0, "band": "green", "findings": []`.
An overlap plot's finding looks like `{"type": "boundary_overlap", "points": 40, "evidence": "overlaps plot MH000400000070 by 656 sq m (35% of this plot)"}`.

For a citizen, the evidence text never contains another plot's ULPIN (it says "another plot"), for example `{"type": "boundary_overlap", "points": 40, "evidence": "overlaps another plot by 656 sq m (35% of this plot)"}`.

Errors: 401, 404 (unknown ulpin, or a citizen asking for a plot that is not theirs), 422 (malformed ulpin; nothing is audited), 429, 503.

## GET /summary

**Who:** officer and admin only (citizens get 403). Counts for the whole data set.

- Parameters: none
- 200:

```json
{
  "total_plots": 100,
  "plots_per_band": {"green": 80, "amber": 20, "red": 0},
  "findings_per_type": {
    "boundary_overlap": 8,
    "restricted_zone_clash": 4,
    "area_mismatch": 4,
    "owner_mismatch": 4,
    "duplicate_survey_no": 8,
    "invalid_boundary": 4,
    "tax_overdue": 4,
    "missing_record": 4
  }
}
```

`findings_per_type` counts findings, not plots. They are the same for every type except `missing_record`, which counts one finding per missing record. All three bands and all eight types are always present, with `0` when empty. (Numbers shown are for the default seed: 100 plots, seed 42.) Errors: 401, 403, 429, 503.

## GET /conflict-types

**Who:** any logged-in user. The eight conflict types in a fixed order (highest points first), so the frontend never hard-codes them.

- Parameters: none
- 200: a list of `{"type", "points", "description"}`, for example:

```json
[
  {"type": "boundary_overlap", "points": 40, "description": "This plot's boundary overlaps another plot's boundary."},
  {"type": "restricted_zone_clash", "points": 30, "description": "More than 20% of the plot lies inside a restricted zone."},
  {"type": "area_mismatch", "points": 25, "description": "The recorded area differs from the mapped area by more than 10%."}
]
```

The real response has all eight entries (the rest: `owner_mismatch` 25, `duplicate_survey_no` 20, `invalid_boundary` 15, `tax_overdue` 15, `missing_record` 10 per missing record). The score caps at 100. Errors: 401, 429.

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

`action` is `view_passport`, `view_passport_denied` or `view_passport_not_found`. `looked_at` is an ISO 8601 time (UTC). Errors: 401, 403, 422 (bad `limit`), 429, 503.
