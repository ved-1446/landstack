"""Small helpers for reading messy values: numbers, dates and owner names.

Every reader raises RowError with a plain-words reason when a value is bad; the adapter
base class turns that into a "rejected row" instead of crashing.
"""
import math
import re
from datetime import date

from .base import RowError

_DOT_NUMBER = re.compile(r"^-?\d+(\.\d+)?$")
_COMMA_NUMBER = re.compile(r"^-?\d+(,\d+)?$")

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def clean_text(value):
    """Trim a value to text; blank or missing becomes None."""
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def parse_number(value, label, comma_decimal=False):
    """Read a non-negative number. None/blank -> None. Anything unreadable or negative -> RowError."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise RowError(f"{label} '{value}' is not a number")
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise RowError(f"{label} '{value}' is not a number")
    else:
        text = str(value).strip()
        if not text:
            return None
        pattern = _COMMA_NUMBER if comma_decimal else _DOT_NUMBER
        if not pattern.match(text):
            style = "comma as the decimal mark" if comma_decimal else "dot as the decimal mark"
            raise RowError(f"{label} '{text}' is not a number (expected digits with {style})")
        number = float(text.replace(",", "."))
    if number < 0:
        raise RowError(f"{label} is negative ({value})")
    return number


# ---- dates ----

def _make_date(text, y, m, d, style):
    try:
        return date(y, m, d)
    except ValueError:
        raise RowError(f"date '{text}' is not a real calendar date ({style})") from None


def parse_dd_mm_yyyy(value, label="date"):
    """Maharashtra: 22/09/2014"""
    text = clean_text(value)
    if text is None:
        return None
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", text)
    if not m:
        raise RowError(f"{label} '{text}' is not in DD/MM/YYYY form")
    return _make_date(text, int(m[3]), int(m[2]), int(m[1]), "DD/MM/YYYY")


def parse_iso_date(value, label="date"):
    """Karnataka: 2014-09-22"""
    text = clean_text(value)
    if text is None:
        return None
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if not m:
        raise RowError(f"{label} '{text}' is not in YYYY-MM-DD form")
    return _make_date(text, int(m[1]), int(m[2]), int(m[3]), "YYYY-MM-DD")


def parse_dd_mon_yyyy(value, label="date"):
    """Uttar Pradesh: 22-Sep-2014 (English month abbreviations, any capitalisation)."""
    text = clean_text(value)
    if text is None:
        return None
    m = re.match(r"^(\d{2})-([A-Za-z]{3})-(\d{4})$", text)
    if not m:
        raise RowError(f"{label} '{text}' is not in DD-Mon-YYYY form")
    month = m[2].capitalize()
    if month not in MONTHS:
        raise RowError(f"{label} '{text}' has an unknown month '{m[2]}'")
    return _make_date(text, int(m[3]), MONTHS.index(month) + 1, int(m[1]), "DD-Mon-YYYY")


def format_dd_mm_yyyy(d):
    return f"{d.day:02d}/{d.month:02d}/{d.year:04d}"


def format_iso_date(d):
    return d.isoformat()


def format_dd_mon_yyyy(d):
    return f"{d.day:02d}-{MONTHS[d.month - 1]}-{d.year:04d}"


# ---- owner names (our standard form is "Given Family", e.g. "Ramesh Kulkarni") ----

def surname_first_to_standard(text):
    """Maharashtra 'Kulkarni Ramesh' -> 'Ramesh Kulkarni' (the first word moves to the end)."""
    words = text.split()
    return " ".join(words[1:] + words[:1])


def standard_to_surname_first(text):
    words = text.split()
    return " ".join(words[-1:] + words[:-1])


def karnataka_to_standard(text):
    """Karnataka 'KULKARNI, RAMESH' -> 'Ramesh Kulkarni' (comma form, upper case)."""
    head, comma, rest = text.partition(",")
    words = (rest.split() + head.split()) if comma else text.split()
    return " ".join(words).title()


def standard_to_karnataka(text):
    words = text.split()
    if len(words) < 2:
        return text.upper()
    return f"{words[-1]}, {' '.join(words[:-1])}".upper()
