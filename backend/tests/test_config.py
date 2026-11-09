"""REFERENCE_DATE must have exactly one copy."""
from datetime import date
from pathlib import Path

import seed
from backend.app import config


def test_reference_date_is_the_agreed_value():
    assert config.REFERENCE_DATE == date(2026, 1, 1)


def test_seed_uses_the_same_reference_date():
    assert seed.REFERENCE_DATE == config.REFERENCE_DATE
    assert seed.REFERENCE_DATE is config.REFERENCE_DATE


def test_seed_has_no_second_copy_of_the_date():
    source = Path(seed.__file__).read_text(encoding="utf-8")
    assert "REFERENCE_DATE =" not in source
    assert "date(2026, 1, 1)" not in source
