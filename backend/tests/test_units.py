"""Unit conversions, date formats and name styles used by the state adapters (no database needed)."""
from datetime import date

import pytest

from db.adapters import formats, units
from db.adapters.base import RowError


# ---------- units: each constant and each conversion ----------

def test_constants():
    assert units.SQM_PER_ARE == 100.0
    assert units.SQM_PER_HECTARE == 10_000.0
    assert units.SQM_PER_ACRE == 4046.8564224
    assert units.SQM_PER_GUNTHA == 101.17


def test_hectares_ares_to_sqm():
    assert units.hectares_ares_to_sqm(1, 50) == 15_000
    assert units.hectares_ares_to_sqm(0, 18.4565) == pytest.approx(1845.65)
    assert units.hectares_ares_to_sqm(0, 0) == 0


def test_acres_guntas_to_sqm():
    assert units.acres_guntas_to_sqm(1, 0) == pytest.approx(4046.8564224)
    assert units.acres_guntas_to_sqm(0, 10) == pytest.approx(1011.7)
    assert units.acres_guntas_to_sqm(2, 5) == pytest.approx(2 * 4046.8564224 + 5 * 101.17)


def test_hectares_to_sqm():
    assert units.hectares_to_sqm(1) == 10_000
    assert units.hectares_to_sqm(0.1846) == pytest.approx(1846.0)


@pytest.mark.parametrize("sqm", [0.5, 99.99, 1845.65, 10_000, 54_321.98])
def test_going_to_sqm_and_back(sqm):
    assert units.hectares_ares_to_sqm(*units.sqm_to_hectares_ares(sqm)) == pytest.approx(sqm)
    assert units.acres_guntas_to_sqm(*units.sqm_to_acres_guntas(sqm)) == pytest.approx(sqm)
    assert units.hectares_to_sqm(units.sqm_to_hectares(sqm)) == pytest.approx(sqm)


# ---------- numbers ----------

def test_parse_number():
    assert formats.parse_number("12.5", "x") == 12.5
    assert formats.parse_number(7, "x") == 7.0
    assert formats.parse_number("0,18457", "x", comma_decimal=True) == pytest.approx(0.18457)
    assert formats.parse_number(None, "x") is None
    assert formats.parse_number("  ", "x") is None


@pytest.mark.parametrize("bad", ["abc", "1,5", "1.2.3", "12abc", True, float("nan")])
def test_parse_number_unreadable(bad):
    with pytest.raises(RowError, match="not a number"):
        formats.parse_number(bad, "area")


def test_parse_number_comma_style_rejects_dots():
    with pytest.raises(RowError, match="not a number"):
        formats.parse_number("0.18", "area_hectare", comma_decimal=True)


def test_parse_number_negative():
    with pytest.raises(RowError, match="negative"):
        formats.parse_number("-3", "hectare")
    with pytest.raises(RowError, match="negative"):
        formats.parse_number(-3, "acres")


# ---------- the three date formats ----------

def test_dd_mm_yyyy():
    assert formats.parse_dd_mm_yyyy("22/09/2014") == date(2014, 9, 22)
    assert formats.format_dd_mm_yyyy(date(2014, 9, 2)) == "02/09/2014"


def test_iso_date():
    assert formats.parse_iso_date("2014-09-22") == date(2014, 9, 22)
    assert formats.format_iso_date(date(2014, 9, 2)) == "2014-09-02"


def test_dd_mon_yyyy():
    assert formats.parse_dd_mon_yyyy("22-Sep-2014") == date(2014, 9, 22)
    assert formats.parse_dd_mon_yyyy("06-JAN-2026") == date(2026, 1, 6)
    assert formats.parse_dd_mon_yyyy("01-dec-2020") == date(2020, 12, 1)
    assert formats.format_dd_mon_yyyy(date(2014, 9, 2)) == "02-Sep-2014"


def test_blank_dates_are_none():
    assert formats.parse_dd_mm_yyyy("") is None
    assert formats.parse_iso_date(None) is None
    assert formats.parse_dd_mon_yyyy("  ") is None


@pytest.mark.parametrize("func,bad,reason", [
    (formats.parse_dd_mm_yyyy, "31/02/2024", "not a real calendar date"),
    (formats.parse_dd_mm_yyyy, "2024-02-28", "DD/MM/YYYY"),
    (formats.parse_dd_mm_yyyy, "22/9/2014", "DD/MM/YYYY"),
    (formats.parse_iso_date, "2024-13-01", "not a real calendar date"),
    (formats.parse_iso_date, "22/09/2014", "YYYY-MM-DD"),
    (formats.parse_dd_mon_yyyy, "31-Feb-2024", "not a real calendar date"),
    (formats.parse_dd_mon_yyyy, "22-Foo-2014", "unknown month"),
    (formats.parse_dd_mon_yyyy, "22/09/2014", "DD-Mon-YYYY"),
])
def test_bad_dates(func, bad, reason):
    with pytest.raises(RowError, match=reason):
        func(bad)


# ---------- owner-name styles ----------

def test_maharashtra_name_style():
    assert formats.surname_first_to_standard("Kulkarni Ramesh") == "Ramesh Kulkarni"
    assert formats.standard_to_surname_first("Ramesh Kulkarni") == "Kulkarni Ramesh"
    assert formats.surname_first_to_standard("Kulkarni") == "Kulkarni"


def test_karnataka_name_style():
    assert formats.karnataka_to_standard("KULKARNI, RAMESH") == "Ramesh Kulkarni"
    assert formats.standard_to_karnataka("Ramesh Kulkarni") == "KULKARNI, RAMESH"
    assert formats.karnataka_to_standard("RAMESH KULKARNI") == "Ramesh Kulkarni"  # no comma: order kept


@pytest.mark.parametrize("name", ["Ramesh Kulkarni", "Kulkarni Ramesh S.", "Anita D Patil", "Vijay K. Shinde"])
def test_name_styles_round_trip(name):
    assert formats.surname_first_to_standard(formats.standard_to_surname_first(name)) == name
    assert formats.karnataka_to_standard(formats.standard_to_karnataka(name)) == name
