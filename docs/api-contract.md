# LandStack API contract (Phase 3)

Read-only JSON API over the seeded fake data. Build against this file; it is checked against the code by `backend/tests/test_api.py`.

- **Run:** `uvicorn backend.app.main:app --reload` (from the repo root, venv active). Base URL `http://localhost:8000`.
- **Live docs:** `http://localhost:8000/docs` (Swagger UI), `http://localhost:8000/redoc`, raw spec at `/openapi.json`.
- **CORS:** only `http://localhost:5173` (the Vite dev server) may call it from a browser. Only GET is allowed.
- **Auth / rate limits:** none yet (Phase 7).
- **Scores** are computed fresh on every request by the Phase 2 engine. Do not compute scores in the frontend.
- **Coordinates** are GeoJSON `[longitude, latitude]` (SRID 4326), around lon 73.80, lat 18.55 (Pune).

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
| 404 | unknown ulpin | `{"detail": "No plot found with ulpin MH999999999999"}` |
| 422 | bad path/query value (malformed ulpin, unknown `band` or `conflict_type`) | `{"detail": [{"type": "string_pattern_mismatch", "loc": ["path", "ulpin"], "msg": "String should match pattern '^[A-Z0-9]{14}$'", "input": "bad", "ctx": {...}}]}` (FastAPI's standard list of problems) |
| 503 | database is not reachable | `{"detail": "Database unavailable"}` |
| 500 | anything unexpected | `{"detail": "Internal server error"}` |

---

## GET /health

Confirms the API is up and the database answers.

- Parameters: none
- 200: `{"status": "ok", "database": "ok"}`
- Errors: 503

## GET /plots

All plots as a GeoJSON FeatureCollection, ordered by ulpin. Filters combine with AND.

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

Notes: features have no top-level `id`; with MapLibre use `promoteId: "ulpin"`. Plots with an `invalid_boundary` finding have a self-intersecting (bow-tie) polygon; it is still a valid GeoJSON Polygon and can be drawn. Errors: 422 (bad `band` or `conflict_type`), 503.

## GET /plots/{ulpin}

The land passport for one plot.

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

Errors: 404 (unknown ulpin), 422 (malformed ulpin), 503.

## GET /summary

Counts for the whole data set.

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

`findings_per_type` counts findings, not plots. They are the same for every type except `missing_record`, which counts one finding per missing record. All three bands and all eight types are always present, with `0` when empty. (Numbers shown are for the default seed: 100 plots, seed 42.) Errors: 503.

## GET /conflict-types

The eight conflict types in a fixed order (highest points first), so the frontend never hard-codes them.

- Parameters: none
- 200: a list of `{"type", "points", "description"}`, for example:

```json
[
  {"type": "boundary_overlap", "points": 40, "description": "This plot's boundary overlaps another plot's boundary."},
  {"type": "restricted_zone_clash", "points": 30, "description": "More than 20% of the plot lies inside a restricted zone."},
  {"type": "area_mismatch", "points": 25, "description": "The recorded area differs from the mapped area by more than 10%."}
]
```

The real response has all eight entries (the rest: `owner_mismatch` 25, `duplicate_survey_no` 20, `invalid_boundary` 15, `tax_overdue` 15, `missing_record` 10 per missing record). The score caps at 100.
