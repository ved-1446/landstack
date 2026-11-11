"""Read-only endpoints for the role pages (Phase 13b). No writes, no AI, no personal data.

  GET /me/activity   my OWN recent audit rows (any logged-in user)
  GET /conflicts     every plot that has findings: ulpin, village, score, band and the finding TYPES with points (staff only)
  GET /zones         the restricted zones: type, area, how many plots touch them, and a simple outline (staff only)

/conflicts and /zones never carry evidence text, owner names, survey numbers or document ids: the evidence text can name another
plot or a person, so only the type and the points are copied from a finding. The score is never recomputed here; it is the one
scoring.run_all() produced.
"""
from typing import Annotated, Literal

import psycopg
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from . import audit, config, limits
from .auth import ErrorBody, User, current_user, require_roles
from .db import get_conn
from .passport import scored

router = APIRouter(tags=["overview"])

Conn = Annotated[psycopg.Connection, Depends(get_conn)]
AnyUser = Annotated[User, Depends(current_user)]
Staff = Annotated[User, Depends(require_roles(*config.STAFF_ROLES))]
Band = Literal["green", "amber", "red"]


class ActivityEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    action: str
    ulpin: str | None
    looked_at: str


class ConflictFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str
    points: int
    simulated: bool


class ConflictRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ulpin: str
    village: str
    score: int
    band: Band
    findings: list[ConflictFinding]


class ZoneRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: int
    zone_type: str
    area_sqm: float
    plots_touching: int
    geometry: dict


# An action that was refused or found nothing: the plot id in such a row is only what was typed, so it is never shown back.
_HIDE_ULPIN = (audit.DENIED, audit.NOT_FOUND, audit.PDF_DENIED, audit.PDF_NOT_FOUND, audit.EXPLAIN_DENIED, audit.EXPLAIN_NOT_FOUND)


@router.get("/me/activity", response_model=list[ActivityEntry],
            responses={401: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def my_activity(request: Request, conn: Conn, user: AnyUser,
                limit: Annotated[int, Query(ge=1, le=200, description="how many rows, newest first")] = 50):
    """The signed-in user's own recent actions (passport views, PDF downloads, explanations, Land Guide questions), newest first.
    Nobody else's rows are ever returned. The username and role are not repeated in each row."""
    rows = conn.execute(
        "SELECT id, action, ulpin, looked_at FROM audit_log WHERE username = %s ORDER BY looked_at DESC, id DESC LIMIT %s",
        (user.username, limit)).fetchall()
    return [{"id": i, "action": action, "ulpin": None if action in _HIDE_ULPIN else ulpin, "looked_at": looked_at.isoformat()}
            for i, action, ulpin, looked_at in rows]


@router.get("/conflicts", response_model=list[ConflictRow],
            responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def conflicts(request: Request, conn: Conn, user: Staff):
    """Officers and admins. Every plot with at least one finding, highest score first: the plot, its village, its score and band,
    and each finding's TYPE and POINTS (no evidence text). Used for the priority queue and the Conflicts and Construction pages."""
    results = scored(conn)
    villages = dict(conn.execute("SELECT ulpin, village FROM plots").fetchall())
    rows = [{"ulpin": u, "village": villages[u], "score": r["score"], "band": r["band"],
             "findings": [{"type": f["type"], "points": f["points"], "simulated": f["type"] in config.SIMULATED_TYPES}
                          for f in r["findings"]]}
            for u, r in results.items() if r["findings"]]
    rows.sort(key=lambda row: (-row["score"], row["ulpin"]))
    return rows


@router.get("/zones", response_model=list[ZoneRow],
            responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def zones(request: Request, conn: Conn, user: Staff):
    """Officers and admins. The restricted zones (flood plain, river buffer, ...): type, area in square metres (geography cast),
    how many valid plots touch each zone, and a simplified outline for a small preview. No plot ids or names."""
    rows = conn.execute(
        """
        SELECT z.id, z.zone_type, ST_Area(z.geom::geography) AS area_sqm,
               (SELECT count(*) FROM plots p WHERE ST_IsValid(p.geom) AND ST_Intersects(p.geom, z.geom)) AS plots_touching,
               ST_AsGeoJSON(ST_SimplifyPreserveTopology(z.geom, 0.00005))::json AS geometry
        FROM zones z
        ORDER BY z.zone_type, z.id
        """
    ).fetchall()
    return [{"id": i, "zone_type": t, "area_sqm": a, "plots_touching": n, "geometry": g} for i, t, a, n, g in rows]
