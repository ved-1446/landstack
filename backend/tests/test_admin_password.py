"""Phase 14b: the admin password can come from ADMIN_PASSWORD (so a public deployment keeps it private)."""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "db"))
import seed_users  # noqa: E402


def _admin_password():
    return {name: pw for name, _, pw in seed_users.DEMO_USERS}["admin"]


def test_env_var_sets_the_admin_password_only(monkeypatch):
    before = {n: p for n, _, p in seed_users.DEMO_USERS if n != "admin"}
    monkeypatch.setenv("ADMIN_PASSWORD", "a-private-test-value-1")
    try:
        importlib.reload(seed_users)
        assert _admin_password() == "a-private-test-value-1"
        assert {n: p for n, _, p in seed_users.DEMO_USERS if n != "admin"} == before
    finally:
        monkeypatch.delenv("ADMIN_PASSWORD")
        importlib.reload(seed_users)


def test_without_the_env_var_the_local_default_is_unchanged(monkeypatch):
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    importlib.reload(seed_users)
    assert _admin_password() == "AdminDemo#2026"


def test_an_empty_env_var_falls_back_to_the_local_default(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    try:
        importlib.reload(seed_users)
        assert _admin_password() == "AdminDemo#2026"
    finally:
        monkeypatch.delenv("ADMIN_PASSWORD")
        importlib.reload(seed_users)


# ---- db/set_admin_password.py -------------------------------------------------------------------------------------------
import pytest  # noqa: E402
import set_admin_password  # noqa: E402
from backend.app import db, security  # noqa: E402


def test_set_admin_password_refuses_a_missing_or_short_password():
    with db.connect() as conn:
        for bad in (None, "", "short"):
            with pytest.raises(ValueError):
                set_admin_password.set_admin_password(conn, bad)
        conn.rollback()


def test_set_admin_password_changes_only_the_admin_hash():
    with db.connect() as conn:
        before = dict(conn.execute("SELECT username, password_hash FROM users"))
        assert set_admin_password.set_admin_password(conn, "a-long-private-test-password") is True
        after = dict(conn.execute("SELECT username, password_hash FROM users"))
        assert security.verify_password(after["admin"], "a-long-private-test-password")
        assert not security.verify_password(after["admin"], "AdminDemo#2026")
        assert {u: h for u, h in after.items() if u != "admin"} == {u: h for u, h in before.items() if u != "admin"}
        conn.rollback()
