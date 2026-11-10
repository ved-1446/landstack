"""Everything about ONE land passport that the JSON endpoint, the PDF and /verify share.

One place for: loading a passport, the role/404/audit rules, hiding other plots from citizens,
and the tamper-evidence hash. Nothing in here is copied elsewhere.
"""
import hashlib
import json
import re
import secrets
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

from . import audit, scoring, unusual

NOT_FOUND = "No plot found with ulpin {}"


def scored(conn):
    """Run the Phase 2 engine: {ulpin: {score, band, findings}} for every plot.

    CACHE WOULD GO HERE. This recomputes every check on every request, which is fine for
    ~100 plots. If the data grew, keep this result in memory (or a table) and refresh it only
    when plots, records or zones change, instead of recomputing per request.
    """
    return scoring.run_all(conn)


def owned_ulpins(conn, username):
    return [u for (u,) in conn.execute(
        "SELECT ulpin FROM user_plots WHERE username = %s ORDER BY ulpin", (username,))]


# A ULPIN written inside evidence text (with the word "plot" in front, if there is one).
_ULPIN_IN_TEXT = re.compile(r"(?:\bplot )?\b(?=[A-Z0-9]*\d)([A-Z0-9]{14})\b")


def hide_other_plots(findings, owned):
    """For citizens: evidence such as "overlaps plot MH0004... by 656 sq m" would reveal that another
    plot exists. Replace every ULPIN that is not the citizen's own with "another plot"."""
    def swap(match):
        return match.group(0) if match.group(1) in owned else "another plot"
    return [{**f, "evidence": _ULPIN_IN_TEXT.sub(swap, f["evidence"])} for f in findings]


def load_passport(conn, ulpin):
    """The full passport as a dict, exactly as stored (nothing hidden), or None if there is no such plot."""
    plot = conn.execute(
        """
        SELECT ulpin, village, land_use, survey_no, ST_AsGeoJSON(geom)::json,
               CASE WHEN ST_IsValid(geom) THEN ST_Area(geom::geography) END AS area_sqm
        FROM plots WHERE ulpin = %s
        """,
        (ulpin,),
    ).fetchone()
    if plot is None:
        return None

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
        "registration": registration and {"owner_name": registration[0], "registered_on": registration[1]},
        "tax": tax and {"paid_until": tax[0]},
        "score": result["score"], "band": result["band"], "findings": result["findings"],
    }


def fetch_for_user(conn, user, ulpin, actions):
    """The role rules, in one place. Returns (shown, full):
    `shown` is what this user may see (citizens get other plots' ids hidden), `full` is the untouched data.

    A citizen asking for a plot that is not theirs gets exactly the same 404 as for a plot that does not
    exist. Every request is written to the audit log first, denied ones too.
    `actions` = (shown, denied, not_found) audit action names, e.g. audit.JSON_VIEW or audit.PDF_DOWNLOAD."""
    shown_action, denied_action, not_found_action = actions
    owned = None
    if user.role == "citizen":
        owned = owned_ulpins(conn, user.username)
        if ulpin not in owned:
            audit.write(conn, user, ulpin, denied_action)
            raise HTTPException(status_code=404, detail=NOT_FOUND.format(ulpin))

    full = load_passport(conn, ulpin)
    if full is None:
        audit.write(conn, user, ulpin, not_found_action)
        raise HTTPException(status_code=404, detail=NOT_FOUND.format(ulpin))
    audit.write(conn, user, ulpin, shown_action)

    shown = full if owned is None else {**full, "findings": hide_other_plots(full["findings"], set(owned))}
    # The statistical note is added to what is SHOWN only. `full` (what gets hashed for tamper evidence) never has it,
    # so retraining or removing the model cannot make an old printed passport say "records have changed".
    shown = {**shown, "unusual": unusual.assess(conn, ulpin)}
    return shown, full


# ---------- tamper evidence ----------

def _json_default(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    raise TypeError(f"cannot hash a {type(value).__name__}")


def canonical_json(full):
    """The passport data as one exact piece of text: keys sorted, no spaces, no timestamps of ours in it
    (only the record dates that belong to the data). Same data in, same text out, always."""
    return json.dumps(full, sort_keys=True, separators=(",", ":"), default=_json_default, ensure_ascii=True)


def content_hash(full):
    """SHA-256 fingerprint (64 hex characters) of the canonical passport data."""
    return hashlib.sha256(canonical_json(full).encode("ascii")).hexdigest()


# Letters and digits that cannot be mixed up on paper (no 0/O, 1/I).
_DOC_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_doc_id():
    """A short random document id like 7KQ2-M9XD-4TPA (60 random bits: cannot be guessed)."""
    chars = "".join(secrets.choice(_DOC_ALPHABET) for _ in range(12))
    return f"{chars[:4]}-{chars[4:8]}-{chars[8:]}"


def record_issue(conn, ulpin, issued_to, hash_hex):
    """Insert the passport_issues row (not committed here). Returns (doc_id, issued_at)."""
    for _ in range(5):
        doc_id = new_doc_id()
        row = conn.execute(
            "INSERT INTO passport_issues (doc_id, ulpin, issued_to, content_hash) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (doc_id) DO NOTHING RETURNING issued_at",
            (doc_id, ulpin, issued_to, hash_hex)).fetchone()
        if row:
            return doc_id, row[0]
    raise RuntimeError("could not create a unique document id")
