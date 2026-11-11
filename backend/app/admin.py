"""Read-only endpoints for the admin's Control Room (Phase 13c). Admin only. No writes, no AI calls, no secrets.

  GET /admin/users      who has an account: username, role, linked plots (a number), last activity. Never a password or hash.
  GET /admin/system     is everything running, and which versions. Never a key, a URL with a secret or a file path.
  GET /admin/insights   what the "unusual plot" model says overall, in plain words. Explanation only: it never changes a score.

(The audit log is GET /audit in main.py, which gained filters and pagination in this phase.)
"""
import importlib.metadata as metadata
import platform
import threading
import time
from datetime import datetime, timezone
from typing import Annotated, Literal

import numpy as np
import psycopg
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict

from . import limits, llm, unusual
from .auth import ErrorBody, User, require_roles
from .db import get_conn
from .passport import scored

router = APIRouter(prefix="/admin", tags=["admin"])

Conn = Annotated[psycopg.Connection, Depends(get_conn)]
Admin = Annotated[User, Depends(require_roles("admin"))]
STARTED = datetime.now(timezone.utc)


# ---------------------------------------------------------------- users

class UserRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    role: Literal["admin", "officer", "citizen"]
    plots: int
    last_active: datetime | None
    actions_30d: int


@router.get("/users", response_model=list[UserRow],
            responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def users(request: Request, conn: Conn, user: Admin):
    """Every account with its role, how many plots are linked to it, when it last did anything and how many actions it took in the
    last 30 days. The password hash is never selected."""
    rows = conn.execute(
        """
        SELECT u.username, u.role,
               (SELECT count(*) FROM user_plots up WHERE up.username = u.username),
               (SELECT max(a.looked_at) FROM audit_log a WHERE a.username = u.username),
               (SELECT count(*) FROM audit_log a WHERE a.username = u.username AND a.looked_at > now() - interval '30 days')
        FROM users u
        ORDER BY CASE u.role WHEN 'admin' THEN 0 WHEN 'officer' THEN 1 ELSE 2 END, u.username
        """
    ).fetchall()
    return [{"username": n, "role": r, "plots": p, "last_active": last, "actions_30d": c} for n, r, p, last, c in rows]


# ---------------------------------------------------------------- system

class Status(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["ok", "off", "not_loaded"]
    detail: str


class ModelInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loaded: bool
    kind: str
    trained_on_plots: int | None
    trained_on: str | None
    explanation_method: str | None
    flag_percentile: float | None


class SystemInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checked_at: datetime
    api: Status
    api_started_at: datetime
    api_version: str
    database: Status
    postgis: Status
    ai_explainer: Status
    model: ModelInfo
    counts: dict[str, int]
    versions: dict[str, str]


def _version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "not installed"


@router.get("/system", response_model=SystemInfo,
            responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def system(request: Request, conn: Conn, user: Admin):
    """Is everything running, and what are the versions. The database answers for itself (we just used it); the AI explainer is only
    reported as switched on or off from the settings (no live call, so this never costs anything); nothing secret is included."""
    from .main import app            # imported here: main imports this module

    (pg,) = conn.execute("SELECT split_part(version(), ' ', 2)").fetchone()
    postgis = conn.execute("SELECT postgis_version()").fetchone()
    bundle, explainer = unusual.current()
    meta = unusual.metadata() if bundle is not None else {}
    counts = {
        "plots": conn.execute("SELECT count(*) FROM plots").fetchone()[0],
        "users": conn.execute("SELECT count(*) FROM users").fetchone()[0],
        "audit_rows": conn.execute("SELECT count(*) FROM audit_log").fetchone()[0],
        "passports_issued": conn.execute("SELECT count(*) FROM passport_issues").fetchone()[0],
    }
    ai_on = llm.is_on()
    return {
        "checked_at": datetime.now(timezone.utc),
        "api": {"state": "ok", "detail": "The API is answering this request."},
        "api_started_at": STARTED,
        "api_version": app.version,
        "database": {"state": "ok", "detail": f"PostgreSQL {pg} answered a query."},
        "postgis": {"state": "ok" if postgis else "off", "detail": f"PostGIS {postgis[0]}" if postgis else "PostGIS is not installed."},
        "ai_explainer": {"state": "ok" if ai_on else "off",
                         "detail": "Switched on: it can rewrite findings in plain words and translate them. It never changes a score."
                         if ai_on else "Switched off (no key is set). Explanations are written by code instead."},
        "model": {
            "loaded": bundle is not None,
            "kind": "Isolation Forest (a statistical hint, not a conflict)",
            "trained_on_plots": bundle["n_train"] if bundle is not None else None,
            "trained_on": meta.get("training_date"),
            "explanation_method": explainer.method if explainer is not None else None,
            "flag_percentile": bundle["percentile"] if bundle is not None else None,
        },
        "counts": counts,
        "versions": {"python": platform.python_version(), "fastapi": _version("fastapi"), "psycopg": _version("psycopg"),
                     "scikit-learn": _version("scikit-learn"), "shap": _version("shap"), "shapely": _version("shapely"),
                     "postgresql": pg, "postgis": postgis[0].split(" ")[0] if postgis else "none"},
    }


# ---------------------------------------------------------------- insights

# Plain-words names for the 12 numbers the model looks at (the same list as ml/features.py).
FEATURE_WORDS = {
    "area_sqm": "How big the plot is",
    "perimeter_m": "How long its boundary is",
    "compactness": "How round or stretched its shape is",
    "aspect_ratio": "How much longer than wide it is",
    "vertex_count": "How many corners its outline has",
    "recorded_over_mapped": "How the recorded area compares with the mapped area",
    "years_since_tax_paid": "How long ago tax was last paid",
    "years_since_registration": "How long ago it was registered",
    "neighbour_count": "How many other plots it overlaps or touches",
    "zone_distance_m": "How close it is to a restricted zone",
    "area_vs_village_median": "How its size compares with other plots in its village",
    "invalid_shape": "Whether its outline is a broken shape",
}


class FeatureInsight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    label: str
    share: float
    top_reason_for: int


class Insights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    available: bool
    note: str
    method: str | None
    plots_checked: int
    flagged: int
    flagged_also_amber_or_red: int
    trained_on_plots: int | None
    flag_percentile: float | None
    features: list[FeatureInsight]


NOTE = ("Explanation only. A statistical model learned from made-up data and points out plots that look unusual. It adds no points and never "
        "changes a score or a band: scores are added up by code from the nine checks.")
_cache: dict = {"at": 0.0, "key": None, "value": None}
_lock = threading.Lock()
TTL_SECONDS = 300


def clear_cache() -> None:
    with _lock:
        _cache.update(at=0.0, key=None, value=None)


def _compute(conn, bundle, explainer) -> dict:
    from ml import features, train_unusual
    plots, zones = unusual._inputs(conn)
    ulpins, rows = features.features_for_all(plots, zones)
    values = train_unusual.score(bundle, rows)
    flags = np.array([train_unusual.is_unusual(bundle, float(v)) for v in values])
    contributions = np.clip(np.asarray(explainer.contributions(rows)), 0, None)     # how hard each number pushed towards "unusual"
    mean = contributions.mean(axis=0)
    total = float(mean.sum()) or 1.0
    top = np.argmax(contributions, axis=1)
    bands = {u: r["band"] for u, r in scored(conn).items()}
    items = [{"name": n, "label": FEATURE_WORDS[n], "share": round(float(mean[i]) / total, 4),
              "top_reason_for": int(sum(1 for k, f in enumerate(flags) if f and top[k] == i))}
             for i, n in enumerate(features.FEATURE_NAMES)]
    items.sort(key=lambda x: (-x["share"], x["name"]))
    return {
        "available": True, "note": NOTE, "method": explainer.method, "plots_checked": len(ulpins), "flagged": int(flags.sum()),
        "flagged_also_amber_or_red": int(sum(1 for k, u in enumerate(ulpins) if flags[k] and bands[u] != "green")),
        "trained_on_plots": int(bundle["n_train"]), "flag_percentile": float(bundle["percentile"]), "features": items,
    }


@router.get("/insights", response_model=Insights,
            responses={401: {"model": ErrorBody}, 403: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@limits.per_user
def insights(request: Request, conn: Conn, user: Admin):
    """What the unusual-plot model says over ALL plots, in plain words: which of its 12 signals matter most (the average push towards
    "unusual", as a share), how many plots it flags, and how many of those the checks also put in amber or red. Computed from the
    saved model on the demo data (SHAP when installed) and cached for 5 minutes. Explanation only: no score or band is touched."""
    bundle, explainer = unusual.current()
    if bundle is None:
        return {"available": False, "note": NOTE, "method": None, "plots_checked": 0, "flagged": 0, "flagged_also_amber_or_red": 0,
                "trained_on_plots": None, "flag_percentile": None, "features": []}
    key = (id(bundle), conn.execute("SELECT count(*) FROM plots").fetchone()[0])
    with _lock:
        if _cache["value"] is not None and _cache["key"] == key and time.monotonic() - _cache["at"] < TTL_SECONDS:
            return _cache["value"]
    value = _compute(conn, bundle, explainer)
    with _lock:
        _cache.update(at=time.monotonic(), key=key, value=value)
    return value

