"""The "unusual plot" statistical note (Phase 9).

The Isolation Forest is loaded ONCE when the API starts. If there is no model file (or it does not fit this code)
the API simply works without it and the passport says `"unusual": null`.

This module only adds a note. It never touches a score, a band or a finding, and it is not part of the
tamper-evidence hash (a retrained model must not make an old printed passport say "records have changed").
It cannot break a passport: any error in here is logged and turned into `null`.

SECURITY: loading a model file runs code (joblib is pickle). Only ml/models/ (or UNUSUAL_MODEL_DIR) is read,
and you should only put a model there that you trained yourself.
"""
import logging
import os
from pathlib import Path

from shapely import wkb

from ml import explain, features, train_unusual

log = logging.getLogger("landstack.unusual")

_state = {"bundle": None, "explainer": None}


def model_dir():
    """ml/models/ unless UNUSUAL_MODEL_DIR says otherwise (the tests point it at an empty folder)."""
    return Path(os.environ.get("UNUSUAL_MODEL_DIR") or train_unusual.MODEL_DIR)


def use_bundle(bundle):
    """Install a trained bundle (or None to switch the model off). Used by load_model and by the tests."""
    _state["bundle"] = bundle
    _state["explainer"] = explain.Explainer(bundle) if bundle is not None else None


def load_model(folder=None):
    """Load the model once. Never raises: a missing or unfit model means 'no unusual field'."""
    try:
        use_bundle(train_unusual.load(folder or model_dir()))
        log.info("unusual-plot model loaded (reasons by %s)", _state["explainer"].method)
    except train_unusual.ModelProblem as exc:
        use_bundle(None)
        log.info("unusual-plot model not used: %s", exc)
    except Exception:  # noqa: BLE001  (a broken file must not stop the API from starting)
        use_bundle(None)
        log.exception("unusual-plot model could not be loaded; continuing without it")
    return _state["bundle"] is not None


def is_loaded():
    return _state["bundle"] is not None


def _inputs(conn):
    """Every plot with its three latest records, and the zones, as the plain inputs ml/features.py wants.
    Plain SELECTs only (no spatial functions): the geometry comes back as hex WKB and shapely reads it."""
    records = {
        "ror": {u: a for u, a in conn.execute(
            "SELECT DISTINCT ON (ulpin) ulpin, recorded_area_sqm FROM ror_records ORDER BY ulpin, id DESC")},
        "reg": {u: d for u, d in conn.execute(
            "SELECT DISTINCT ON (ulpin) ulpin, registered_on FROM registrations "
            "ORDER BY ulpin, registered_on DESC, id DESC")},
        "tax": {u: d for u, d in conn.execute(
            "SELECT DISTINCT ON (ulpin) ulpin, paid_until FROM tax_records ORDER BY ulpin, paid_until DESC, id DESC")},
    }
    plots = [{
        "ulpin": u, "village": v, "geom": wkb.loads(g, hex=True),
        "recorded_area_sqm": records["ror"].get(u), "registered_on": records["reg"].get(u),
        "paid_until": records["tax"].get(u),
    } for u, v, g in conn.execute("SELECT ulpin, village, geom FROM plots ORDER BY ulpin")]
    zones = [wkb.loads(g, hex=True) for (g,) in conn.execute("SELECT geom FROM zones")]
    return plots, zones


def assess(conn, ulpin):
    """{"flag": bool, "percentile": float, "reasons": [str]} for one plot, or None (no model, or anything went wrong).

    percentile = share (0 to 100) of the TRAINING plots that are less unusual than this one.
    reasons = up to 3 plain-English lines, only when flagged. A reason never names another plot."""
    bundle, explainer = _state["bundle"], _state["explainer"]
    if bundle is None:
        return None
    try:
        plots, zones = _inputs(conn)
        ulpins, rows = features.features_for_all(plots, zones)
        row = rows[ulpins.index(ulpin)]
        value = float(train_unusual.score(bundle, [row])[0])
        flag = train_unusual.is_unusual(bundle, value)
        return {"flag": flag,
                "percentile": round(train_unusual.percentile_of(bundle, value), 1),
                "reasons": explainer.reasons(row) if flag else []}
    except Exception:  # noqa: BLE001
        log.exception("unusual-plot note failed for %s; leaving it out", ulpin)
        return None
