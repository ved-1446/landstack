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
ZONE_SHARE_LIMIT = 0.20        # more than 20% of the plot inside a zone
AREA_MISMATCH_LIMIT = 0.10     # recorded area more than 10% away from the real area
TAX_OVERDUE_YEARS = 2          # paid-until more than 2 years before REFERENCE_DATE

# Owner-name match: cosine similarity at or above this means "same person".
# Chosen from the data (see names.py and the Phase 2 report).
NAME_MATCH_THRESHOLD = 0.60
