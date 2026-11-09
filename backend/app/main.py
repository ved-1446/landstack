"""LandStack API. Raw SQL, no ORM.

Run from the repo root:  uvicorn backend.app.main:app --reload
Interactive docs:        http://localhost:8000/docs
The checks and the score come from checks.py / scoring.py and are not changed here.

Needs JWT_SECRET in .env or the environment (the app will not start without it).
Who may do what is in the role matrix in docs/api-contract.md.
"""
import hmac
import logging
from datetime import date, datetime
from typing import Annotated, Literal

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Path, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from slowapi.errors import RateLimitExceeded

from . import audit, auth, config, limits, passport, pdf
from .auth import ErrorBody, User, current_user, require_roles
from .db import get_conn
from .passport import fetch_for_user, hide_other_plots, owned_ulpins, scored  # noqa: F401  (hide_other_plots is re-exported)

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


class AuditEntry(BaseModel):
    id: int
    username: str
    role: Literal["admin", "officer", "citizen"]
    ulpin: str | None
    action: Literal["view_passport", "view_passport_denied", "view_passport_not_found",
                    "download_passport_pdf", "download_passport_pdf_denied", "download_passport_pdf_not_found"]
    looked_at: datetime


CHANGED = "records have changed since this was issued"


class Verification(BaseModel):
    valid: bool = Field(description="true only if the records still match what was printed")
    ulpin: str
    issued_at: datetime
    status: Literal["matches", "records have changed since this was issued"]


# ---------- App, CORS, errors ----------

app = FastAPI(
    title="LandStack API",
    version="0.8.0",
    description="Land records on a map. Plots, land passports, conflicts and risk scores "
                "(fake demo data). Log in at POST /auth/login first; what you may see depends on your role.",
)

# Only the Vite dev server may call this API from a browser. Retry-After is exposed so the page can read it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Retry-After"],
)
app.state.limiter = limits.limiter
PUBLIC_BASE_URL = pdf.get_public_base_url()   # checked at start-up; the QR codes point here
app.include_router(auth.router)


@app.exception_handler(RateLimitExceeded)
async def rate_limited(request: Request, exc: RateLimitExceeded):
    return limits.too_many_requests(request, exc)


@app.exception_handler(psycopg.OperationalError)
async def database_down(request: Request, exc: psycopg.OperationalError):
    log.error("database unavailable: %s", exc)
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)  # the stack trace stays in the log
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


Conn = Annotated[psycopg.Connection, Depends(get_conn)]
AnyUser = Annotated[User, Depends(current_user)]
Staff = Annotated[User, Depends(require_roles(*config.STAFF_ROLES))]
Admin = Annotated[User, Depends(require_roles("admin"))]


# ---------- Endpoints ----------

@app.get("/health", response_model=Health, tags=["system"],
         responses={503: {"model": ErrorBody}, 429: {"model": ErrorBody}})
@limits.per_user
def health(request: Request, conn: Conn):
    """Open to everyone. Confirms the API is up and the database answers."""
    conn.execute("SELECT 1").fetchone()
    return {"status": "ok", "database": "ok"}


@app.get("/plots", response_model=PlotCollection, tags=["plots"],
         responses={401: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def list_plots(
    request: Request,
    conn: Conn,
    user: AnyUser,
    band: Annotated[Band | None, Query(description="Only plots in this risk band")] = None,
    village: Annotated[str | None, Query(description="Only plots in this village (exact name)")] = None,
    conflict_type: Annotated[ConflictType | None, Query(
        description="Only plots with at least one finding of this type")] = None,
):
    """Plots as a GeoJSON FeatureCollection, each with its score and band.
    Citizens get only their own plots; officers and admins get all of them."""
    results = scored(conn)
    owned = owned_ulpins(conn, user.username) if user.role == "citizen" else None
    rows = conn.execute(
        """
        SELECT ulpin, village, land_use, survey_no, ST_AsGeoJSON(geom)::json
        FROM plots
        WHERE (%(village)s::text IS NULL OR village = %(village)s)
          AND (%(owned)s::text[] IS NULL OR ulpin = ANY(%(owned)s::text[]))
        ORDER BY ulpin
        """,
        {"village": village, "owned": owned},
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
         responses={401: {"model": ErrorBody}, 404: {"model": ErrorBody},
                    429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def land_passport(request: Request, ulpin: Ulpin, conn: Conn, user: AnyUser):
    """The land passport: plot facts, its three records (null if missing), score and findings.
    Every view is written to the audit log, including denied ones. A citizen who asks for a plot
    that is not theirs gets exactly the same 404 as for a plot that does not exist."""
    shown, _full = fetch_for_user(conn, user, ulpin, audit.JSON_VIEW)
    return shown


@app.get("/plots/{ulpin}/passport.pdf", tags=["plots"],
         responses={200: {"content": {"application/pdf": {}}, "description": "The printable passport (one A4 page)"},
                    401: {"model": ErrorBody}, 404: {"model": ErrorBody}, 429: {"model": ErrorBody},
                    503: {"model": ErrorBody}})
@limits.per_user
def passport_pdf(request: Request, ulpin: Ulpin, conn: Conn, user: AnyUser):
    """The land passport as a one-page A4 PDF. Same role rules as the JSON passport (a citizen gets only their
    own plots, anything else is a 404, and other plots' ids are hidden). Each download writes an audit row
    and a passport_issues row; the QR code on the page points at GET /verify/{doc_id}."""
    shown, full = fetch_for_user(conn, user, ulpin, audit.PDF_DOWNLOAD)
    doc_id, issued_at = passport.record_issue(conn, ulpin, user.username, passport.content_hash(full))
    content = pdf.build_passport_pdf(
        shown, doc_id=doc_id, issued_at=issued_at, issued_to=user.username, issued_role=user.role,
        url=pdf.verify_url(PUBLIC_BASE_URL, doc_id))
    conn.commit()    # only now is the issue row kept: no PDF, no row
    return Response(content=content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="landpassport_{ulpin}.pdf"',
        "Cache-Control": "no-store"})


@app.get("/verify/{doc_id}", response_model=Verification, tags=["verify"],
         responses={404: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_ip_verify
def verify_document(
    request: Request,
    doc_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9-]{4,40}$", examples=["7KQ2-M9XD-4TPA"],
                                description="the document id printed on the passport (also in its QR code)")],
    conn: Conn,
):
    """Public (no login), strictly rate limited. Does this printed passport still match the records?
    Says only: valid or not, the ulpin, when it was issued, and whether the records still match.
    No names, no evidence, no score."""
    row = conn.execute("SELECT ulpin, issued_at, content_hash FROM passport_issues WHERE doc_id = %s",
                       (doc_id.upper(),)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No document found with that id")
    ulpin, issued_at, printed_hash = row
    now = passport.load_passport(conn, ulpin)
    matches = now is not None and hmac.compare_digest(passport.content_hash(now), printed_hash)
    return {"valid": matches, "ulpin": ulpin, "issued_at": issued_at,
            "status": "matches" if matches else CHANGED}


@app.get("/summary", response_model=Summary, tags=["summary"],
         responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody},
                    429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def summary(request: Request, conn: Conn, user: Staff):
    """Plots per band and number of findings per conflict type. Officers and admins only."""
    results = scored(conn)
    bands = {b: 0 for b in ("green", "amber", "red")}
    per_type = {t: 0 for t in config.POINTS}
    for result in results.values():
        bands[result["band"]] += 1
        for f in result["findings"]:
            per_type[f["type"]] += 1
    return {"total_plots": len(results), "plots_per_band": bands, "findings_per_type": per_type}


@app.get("/conflict-types", response_model=list[ConflictTypeInfo], tags=["summary"],
         responses={401: {"model": ErrorBody}, 429: {"model": ErrorBody}})
@limits.per_user
def conflict_types(request: Request, user: AnyUser):
    """The eight conflict types with their points and a plain description. Any logged-in user."""
    return [{"type": t, "points": p, "description": config.CONFLICT_DESCRIPTIONS[t]}
            for t, p in config.POINTS.items()]


@app.get("/audit", response_model=list[AuditEntry], tags=["audit"],
         responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody},
                    429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def audit_log(
    request: Request,
    conn: Conn,
    user: Admin,
    username: Annotated[str | None, Query(max_length=64, description="Only this user's views")] = None,
    ulpin: Annotated[str | None, Query(max_length=40, description="Only views of this plot")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="How many rows (newest first)")] = 100,
):
    """The audit log, newest first. Admins only."""
    rows = conn.execute(
        """
        SELECT id, username, role, ulpin, action, looked_at
        FROM audit_log
        WHERE (%(username)s::text IS NULL OR username = %(username)s)
          AND (%(ulpin)s::text IS NULL OR ulpin = %(ulpin)s)
        ORDER BY looked_at DESC, id DESC
        LIMIT %(limit)s
        """,
        {"username": username, "ulpin": ulpin, "limit": limit},
    ).fetchall()
    return [{"id": r[0], "username": r[1], "role": r[2], "ulpin": r[3], "action": r[4], "looked_at": r[5]}
            for r in rows]
