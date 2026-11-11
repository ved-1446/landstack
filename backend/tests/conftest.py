"""Shared test setup: import paths and a seeded live database (skips if it is down)."""
import json
import os
import secrets
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "db"))

# The API refuses to start without a real JWT secret. Tests use a throw-away random one that exists
# only for this run (never written anywhere); it beats whatever is in .env.
os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
os.environ["JWT_EXPIRE_MINUTES"] = "60"
# Phase 9: the tests never load a real ml/models file. An empty folder = "no model" = `"unusual": null`.
# The model tests switch a small throw-away model on and off themselves (unusual.use_bundle).
# Phase 11: the AI is OFF in tests whatever .env says (an empty value beats .env), and no test may reach the network:
# tests that need an answer switch the AI on with a fake (see backend/tests/test_explain.py).
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["OPENROUTER_MODEL"] = ""
# ...and the Land Guide never reads a real scraped corpus in tests (an empty folder = no chunks); tests build tiny corpora themselves.
os.environ["CHATBOT_DATA_DIR"] = str(Path(__import__("tempfile").gettempdir()) / "landstack-no-chatbot-data-here")
os.environ["UNUSUAL_MODEL_DIR"] = str(Path(__import__("tempfile").gettempdir()) / "landstack-no-model-here")

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


# ---------------------------------------------------------------------------------------------
# Login fixtures (Phase 7). Four throw-away test users are created with random passwords and
# removed again at the end, together with every audit row they caused.
# ---------------------------------------------------------------------------------------------

TEST_USERS = {                      # key -> (username, role)
    "admin": ("test_admin", "admin"),
    "officer": ("test_officer", "officer"),
    "citizen_a": ("test_citizen_a", "citizen"),
    "citizen_b": ("test_citizen_b", "citizen"),
}


def _remove_test_users(connection):
    names = [name for name, _ in TEST_USERS.values()] + ["test_temp"]
    connection.execute("DELETE FROM audit_log WHERE username = ANY(%s::text[])", (names,))
    connection.execute("DELETE FROM passport_issues WHERE issued_to = ANY(%s::text[])", (names,))
    connection.execute("DELETE FROM users WHERE username = ANY(%s::text[])", (names,))   # user_plots cascades


@pytest.fixture(autouse=True)
def no_network_for_the_ai(monkeypatch):
    """The ONE function that talks to the AI service is blocked in every test, so nothing can reach the network by accident."""
    from backend.app import llm

    def blocked(*args, **kwargs):
        raise AssertionError("a test tried to call the AI service over the network; mock llm.complete instead")
    monkeypatch.setattr(llm, "_post", blocked)

    from chatbot import guide, scrape

    def blocked_scrape(*args, **kwargs):
        raise AssertionError("a test tried to fetch a web page over the network; pass a fake `get` to scrape() instead")
    monkeypatch.setattr(scrape, "_http_get", blocked_scrape)
    guide.set_index(None)                                  # every test starts without a cached Land Guide index
    yield
    guide.set_index(None)


@pytest.fixture(scope="session", autouse=True)
def relaxed_rate_limits():
    """Normal tests make far more than 60 requests a minute. Rate-limit tests lower these again."""
    from backend.app import config
    config.RATE_LOGIN = config.RATE_DEFAULT = config.RATE_VERIFY = "100000/minute"
    config.RATE_PUBLIC_STATS = config.RATE_PUBLIC_PLOT = "100000/minute"


@pytest.fixture(autouse=True)
def fresh_rate_limiter():
    """Every test starts (and ends) with empty rate-limit counters."""
    from backend.app import limits
    limits.limiter.reset()
    yield
    limits.limiter.reset()


@pytest.fixture(scope="session")
def users(conn, truth):
    """{key: {username, role, password, plots}}. Citizen A owns an overlap plot, a missing-record plot and a clean plot;
    citizen B owns a zone-clash plot and two clean plots. Nobody owns the other plots."""
    from backend.app import security
    conflicts = truth["conflicts"]
    decoys = {d["ulpin"] for d in truth["decoys"]}
    only = lambda ctype: sorted(u for u, t in conflicts.items() if t == [ctype])  # noqa: E731
    every_plot = [u for (u,) in conn.execute("SELECT ulpin FROM plots ORDER BY ulpin")]
    clean = [u for u in every_plot if u not in conflicts and u not in decoys]
    # a plot that only partly overlaps another one (not the "one plot inside another" pair), so its evidence reads
    # "overlaps plot X by N sq m" whatever the seed layout
    partial_overlap = [u for u in only("boundary_overlap") if truth["details"][u]["overlap_relation"] == "overlaps"]
    plots = {
        "citizen_a": [partial_overlap[0], only("missing_record")[0], clean[0]],
        "citizen_b": [only("restricted_zone_clash")[0], clean[1], clean[2]],
    }
    _remove_test_users(conn)
    made = {}
    for key, (username, role) in TEST_USERS.items():
        password = secrets.token_urlsafe(16)
        conn.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                     (username, security.hash_password(password), role))
        for ulpin in plots.get(key, []):
            conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (username, ulpin))
        made[key] = {"username": username, "role": role, "password": password, "plots": plots.get(key, [])}
    yield made
    _remove_test_users(conn)


@pytest.fixture(scope="session")
def anon_client(users):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    return TestClient(app)


@pytest.fixture(scope="session")
def tokens(users, anon_client, relaxed_rate_limits):
    """Log in through the real /auth/login for each test user. {key: token}."""
    out = {}
    for key, u in users.items():
        r = anon_client.post("/auth/login", json={"username": u["username"], "password": u["password"]})
        assert r.status_code == 200, r.text
        out[key] = r.json()["access_token"]
    return out


@pytest.fixture(scope="session")
def auth(tokens):
    """auth("officer") -> {"Authorization": "Bearer ..."}"""
    return lambda key: {"Authorization": f"Bearer {tokens[key]}"}
