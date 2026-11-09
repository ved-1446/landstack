"""Shared constants. Every number the checks and the score use lives here."""
from datetime import date

# The fixed "today" for the tax rule (db/seed.py imports this too).
REFERENCE_DATE = date(2026, 1, 1)

# Points per conflict type (missing_record is per missing record).
POINTS = {
    "boundary_overlap": 40,
    "restricted_zone_clash": 30,
    "area_mismatch": 25,
    "owner_mismatch": 25,
    "duplicate_survey_no": 20,
    "invalid_boundary": 15,
    "tax_overdue": 15,
    "missing_record": 10,
}
SCORE_CAP = 100

# Risk bands: green 0-24, amber 25-59, red 60+.
AMBER_FROM = 25
RED_FROM = 60

# Check thresholds.
# Two plots only count as overlapping if the shared ground is at least this many square metres. Plots that just
# touch along an edge share a line (0 sq m), and survey noise of a few centimetres along a 40 m edge adds up to a few
# sq m; 5 sq m keeps both out while still catching any real overlap. Too low: edge noise gets flagged. Too high: a small
# real overlap is missed.
MIN_OVERLAP_SQM = 5.0
ZONE_SHARE_LIMIT = 0.20        # more than 20% of the plot inside a zone
AREA_MISMATCH_LIMIT = 0.10     # recorded area more than 10% away from the real area
TAX_OVERDUE_YEARS = 2          # paid-until more than 2 years before REFERENCE_DATE

# Owner-name match: cosine similarity at or above this means "same person".
# Chosen from the data (see names.py and the Phase 2 report).
NAME_MATCH_THRESHOLD = 0.60

# One-line plain descriptions, served by the API so the frontend never hard-codes them.
CONFLICT_DESCRIPTIONS = {
    "boundary_overlap": "This plot overlaps another plot, or lies inside it, or has another plot inside it.",
    "restricted_zone_clash": (
        f"More than {ZONE_SHARE_LIMIT:.0%} of the plot lies inside a restricted zone."),
    "area_mismatch": (
        f"The recorded area differs from the mapped area by more than {AREA_MISMATCH_LIMIT:.0%}."),
    "owner_mismatch": (
        "The owner in the land record and the owner in the registration are different people."),
    "duplicate_survey_no": "Another plot in the same village has the same survey number.",
    "invalid_boundary": "The boundary shape is invalid, for example it crosses itself.",
    "tax_overdue": (
        f"Property tax was last paid more than {TAX_OVERDUE_YEARS} years before "
        f"{REFERENCE_DATE:%d %b %Y}."),
    "missing_record": "The plot has no land record, registration or tax record (10 points each).",
}

# ---- Phase 7: login, roles, rate limits ----
ROLES = ("admin", "officer", "citizen")
STAFF_ROLES = ("officer", "admin")        # may see every plot and /summary

JWT_ALGORITHM = "HS256"
JWT_DEFAULT_EXPIRE_MINUTES = 60           # overridden by JWT_EXPIRE_MINUTES in .env
JWT_SECRET_PLACEHOLDER = "change-me-generate-a-long-random-string"   # the .env.example value; never accepted
JWT_SECRET_MIN_LENGTH = 32

# Rate limits (read on every request, so tests can lower them).
RATE_LOGIN = "5/minute"                   # per IP address
RATE_DEFAULT = "60/minute"                # per logged-in user (per IP when nobody is logged in)

# ---- Phase 8: printable passport ----
RATE_VERIFY = "10/minute"                 # GET /verify/{doc_id}: public, so strictly limited, per IP address
DEFAULT_PUBLIC_BASE_URL = "http://localhost:8000"   # PUBLIC_BASE_URL in .env overrides; used inside the QR code
