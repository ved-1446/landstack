"""Shared test setup: import paths and a seeded live database (skips if it is down)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

import seed  # noqa: E402

TRUTH_FILE = ROOT / "db" / "planted_truth.json"


@pytest.fixture(scope="session")
def truth():
    """db/planted_truth.json, checked to be the genuine output of the seed script."""
    t = json.loads(TRUTH_FILE.read_text(encoding="utf-8"))
    regenerated = seed.generate(t["plots"], t["problem_rate"], t["seed"])
    assert regenerated["truth"] == t, "planted_truth.json is stale: re-run python db/seed.py"
    return t


@pytest.fixture(scope="session")
def conn(truth):
    """A connection to the live database, loaded with exactly the data the truth file describes."""
    from backend.app import db
    try:
        connection = db.connect()
        # autocommit: no transaction stays open holding locks (other tests TRUNCATE the tables)
        connection.autocommit = True
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"database not reachable: {exc}")
    seed.load(seed.generate(truth["plots"], truth["problem_rate"], truth["seed"]))
    yield connection
    connection.close()
