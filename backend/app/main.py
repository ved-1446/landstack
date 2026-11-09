"""LandStack API (Phase 3). Read-only. Raw SQL, no ORM.

Run from the repo root:  uvicorn backend.app.main:app --reload
Interactive docs:        http://localhost:8000/docs
The checks and the score come from checks.py / scoring.py and are not changed here.
"""
import logging
from datetime import date
from typing import Annotated, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import config, db, scoring

log = logging.getLogger("landstack.api")

Band = Literal["green", "amber", "red"]
ConflictType = Literal[tuple(config.POINTS)]
# A ULPIN is 14 letters/digits. Anything else is rejected with 422 before touching the database.
Ulpin = Annotated[str, Path(pattern=r"^[A-Z0-9]{14}$", examples=["MH000100000001"],
                            description="14-character plot id (ULPIN), capital letters and digits")]


# ---------- Response models (these drive the /docs page) ----------

class Finding(BaseModel):
    type: ConflictType
    points: int
    evidence: str


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]]  # [ring][point][lon, lat]


class PlotProperties(BaseModel):
    ulpin: str
    village: str
    land_use: str
    survey_no: str
    score: int
    band: Band


class PlotFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: PolygonGeometry
    properties: PlotProperties


class PlotCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[PlotFeature]


class RorRecord(BaseModel):
    owner_name: str
    recorded_area_sqm: float


class RegistrationRecord(BaseModel):
    owner_name: str
    registered_on: date


class TaxRecord(BaseModel):
    paid_until: date


class Passport(BaseModel):
    ulpin: str
    village: str
    land_use: str
    survey_no: str
    area_sqm: float | None  # real area in square metres; null when the shape is invalid
    geometry: PolygonGeometry
    ror: RorRecord | None
    registration: RegistrationRecord | None
    tax: TaxRecord | None
    score: int
    band: Band
    findings: list[Finding]


class Summary(BaseModel):
    total_plots: int
    plots_per_band: dict[Band, int]
    findings_per_type: dict[ConflictType, int]


class ConflictTypeInfo(BaseModel):
    type: ConflictType
    points: int
    description: str


class Health(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]


class ErrorBody(BaseModel):
    detail: str


# ---------- App, CORS, errors ----------

app = FastAPI(
    title="LandStack API",
    version="0.3.0",
    description="Land records on a map. Plots, land passports, conflicts and risk scores "
                "(fake demo data). Read-only.",
)

# Only the Vite dev server may call this API from a browser.
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET"])


@app.exception_handler(psycopg.OperationalError)
async def database_down(request: Request, exc: psycopg.OperationalError):
    log.error("database unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)  # the stack trace stays in the log
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


def get_conn():
    """Dependency: one database connection per request, always closed afterwards."""
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


Conn = Annotated[psycopg.Connection, Depends(get_conn)]


def scored(conn):
    """Run the Phase 2 engine: {ulpin: {score, band, findings}} for every plot.

    CACHE WOULD GO HERE. This recomputes every check on every request, which is fine for
    ~100 plots. If the data grew, keep this result in memory (or a table) and refresh it only
    when plots, records or zones change, instead of recomputing per request.
    """
    return scoring.run_all(conn)


# ---------- Endpoints ----------

@app.get("/health", response_model=Health, tags=["system"],
         responses={503: {"model": ErrorBody}})
def health(conn: Conn):
    """Confirms the API is up and the database answers."""
    conn.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "ok"}


@app.get("/plots", response_model=PlotCollection, tags=["plots"],
         responses={503: {"model": ErrorBody}})
def list_plots(
    conn: Conn,
    band: Annotated[Band | None, Query(description="Only plots in this risk band")] = None,
    village: Annotated[str | None, Query(description="Only plots in this village (exact name)")] = None,
    conflict_type: Annotated[ConflictType | None, Query(
        description="Only plots with at least one finding of this type")] = None,
):
    """All plots as a GeoJSON FeatureCollection, each with its score and band."""
    results = scored(conn)
    rows = conn.execute(
        """
        SELECT ulpin, village, land_use, survey_no, ST_AsGeoJSON(geom)::json
        FROM plots
        WHERE (%(village)s::text IS NULL OR village = %(village)s)
        ORDER BY ulpin
        """,
        {"village": village},
    ).fetchall()

    features = []
    for ulpin, vill, land_use, survey_no, geometry in rows:
        result = results[ulpin]
        if band and result["band"] != band:
            continue
        if conflict_type and not any(f["type"] == conflict_type for f in result["findings"]):
            continue
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {"ulpin": ulpin, "village": vill, "land_use": land_use,
                           "survey_no": survey_no, "score": result["score"],
                           "band": result["band"]},
        })
    return {"type": "FeatureCollection", "features": features}


@app.get("/plots/{ulpin}", response_model=Passport, tags=["plots"],
         responses={404: {"model": ErrorBody}, 503: {"model": ErrorBody}})
def land_passport(ulpin: Ulpin, conn: Conn):
    """The land passport: plot facts, its three records (null if missing), score and findings."""
    plot = conn.execute(
        """
        SELECT ulpin, village, land_use, survey_no, ST_AsGeoJSON(geom)::json,
               CASE WHEN ST_IsValid(geom) THEN ST_Area(geom::geography) END AS area_sqm
        FROM plots WHERE ulpin = %s
        """,
        (ulpin,),
    ).fetchone()
    if plot is None:
        raise HTTPException(status_code=404, detail=f"No plot found with ulpin {ulpin}")

    # Latest row of each record type (a plot normally has one).
    ror = conn.execute(
        "SELECT owner_name, recorded_area_sqm FROM ror_records WHERE ulpin = %s "
        "ORDER BY id DESC LIMIT 1", (ulpin,)).fetchone()
    registration = conn.execute(
        "SELECT owner_name, registered_on FROM registrations WHERE ulpin = %s "
        "ORDER BY registered_on DESC, id DESC LIMIT 1", (ulpin,)).fetchone()
    tax = conn.execute(
        "SELECT paid_until FROM tax_records WHERE ulpin = %s "
        "ORDER BY paid_until DESC, id DESC LIMIT 1", (ulpin,)).fetchone()

    result = scored(conn)[ulpin]
    return {
        "ulpin": plot[0], "village": plot[1], "land_use": plot[2], "survey_no": plot[3],
        "geometry": plot[4], "area_sqm": plot[5],
        "ror": ror and {"owner_name": ror[0], "recorded_area_sqm": ror[1]},
        "registration": registration and {"owner_name": registration[0],
                                          "registered_on": registration[1]},
        "tax": tax and {"paid_until": tax[0]},
        "score": result["score"], "band": result["band"], "findings": result["findings"],
    }


@app.get("/summary", response_model=Summary, tags=["summary"],
         responses={503: {"model": ErrorBody}})
def summary(conn: Conn):
    """Plots per band and number of findings per conflict type."""
    results = scored(conn)
    bands = {b: 0 for b in ("green", "amber", "red")}
    per_type = {t: 0 for t in config.POINTS}
    for result in results.values():
        bands[result["band"]] += 1
        for f in result["findings"]:
            per_type[f["type"]] += 1
    return {"total_plots": len(results), "plots_per_band": bands, "findings_per_type": per_type}


@app.get("/conflict-types", response_model=list[ConflictTypeInfo], tags=["summary"])
def conflict_types():
    """The eight conflict types with their points and a plain description."""
    return [{"type": t, "points": p, "description": config.CONFLICT_DESCRIPTIONS[t]}
            for t, p in config.POINTS.items()]
