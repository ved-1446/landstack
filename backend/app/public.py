"""Two public, read-only endpoints for the front page (Phase 13a). No login, no AI, no personal data.

  GET /public/stats           how many plots there are and how many are in each risk band (counts only)
  GET /public/plot/{ulpin}    ONLY {ulpin, village, band}: no names, evidence, survey numbers, scores or ids

They are limited per IP address (see config.RATE_PUBLIC_*), so they cannot be used to scrape the data in bulk.
They never read the login token: a citizen's or officer's token changes nothing here.
Auditing: audit_log needs a username (and the schema is not changed in this phase), so anonymous calls are only COUNTED
in memory and written to the log as numbers, never with the ids that were asked for.
"""
import logging
import re
import threading
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from slowapi.util import get_remote_address

from . import config, limits
from .auth import ErrorBody
from .db import get_conn
from .passport import scored

log = logging.getLogger("landstack.public")
router = APIRouter(prefix="/public", tags=["public"])

ULPIN = re.compile(r"^[A-Z0-9]{14}$")
NOT_FOUND = "No plot found"                  # the ONE answer for a wrong, malformed or unknown id
STATS_TTL_SECONDS = 60

per_ip_stats = limits.limiter.limit(lambda: config.RATE_PUBLIC_STATS, key_func=get_remote_address)
per_ip_plot = limits.limiter.limit(lambda: config.RATE_PUBLIC_PLOT, key_func=get_remote_address)


class PublicStats(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_plots: int
    plots_per_band: dict[Literal["green", "amber", "red"], int]


class PublicPlot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ulpin: str
    village: str
    band: Literal["green", "amber", "red"]


# ---- the 60 second cache for the counts, and the anonymous counters ----
_lock = threading.Lock()
_cache: dict = {"at": 0.0, "value": None}
COUNTS = {"stats": 0, "plot_found": 0, "plot_not_found": 0}


def clear_cache() -> None:
    with _lock:
        _cache.update(at=0.0, value=None)


def count(kind: str) -> None:
    with _lock:
        COUNTS[kind] += 1
        total = COUNTS[kind]
    if total % 100 == 1:
        log.info("public endpoint calls so far: %s", dict(COUNTS))


@router.get("/stats", response_model=PublicStats,
            responses={429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@per_ip_stats
def public_stats(request: Request, conn=Depends(get_conn)):
    """Aggregate counts only: total plots and plots per risk band. Cached for about 60 seconds. No login."""
    count("stats")
    with _lock:
        if _cache["value"] is not None and time.monotonic() - _cache["at"] < STATS_TTL_SECONDS:
            return _cache["value"]
    bands = {"green": 0, "amber": 0, "red": 0}
    results = scored(conn)
    for result in results.values():
        bands[result["band"]] += 1
    value = {"total_plots": len(results), "plots_per_band": bands}
    with _lock:
        _cache.update(at=time.monotonic(), value=value)
    return value


@router.get("/plot/{ulpin}", response_model=PublicPlot,
            responses={404: {"model": ErrorBody}, 429: {"model": ErrorBody}, 503: {"model": ErrorBody}})
@per_ip_plot
def public_plot(request: Request, ulpin: str, conn=Depends(get_conn)):
    """Does this plot id exist, and in which village and risk band? Nothing else is ever returned. No login.
    A malformed id and an unknown id get the same 404, so the answer reveals nothing about which ids exist except
    by asking one id at a time, within the strict per-IP limit."""
    if not ULPIN.fullmatch(ulpin):
        count("plot_not_found")
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    row = conn.execute("SELECT village FROM plots WHERE ulpin = %s", (ulpin,)).fetchone()
    if row is None:
        count("plot_not_found")
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    count("plot_found")
    return {"ulpin": ulpin, "village": row[0], "band": scored(conn)[ulpin]["band"]}
