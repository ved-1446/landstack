"""Phase 13c: the admin's read endpoints (/admin/users, /admin/system, /admin/insights) and the audit-log filters and pages."""
import re
from datetime import datetime, timedelta, timezone

import pytest

from backend.app import admin, llm, unusual
from ml import make_dataset, train_unusual

ADMIN_PATHS = ("/admin/users", "/admin/system", "/admin/insights")


@pytest.fixture(scope="module")
def small_bundle():
    _ids, matrix, _labels = make_dataset.build(plots=400, rate=0.08, seed_value=4)
    return train_unusual.fit(matrix, seed=1)


@pytest.fixture
def model_on(small_bundle):
    unusual.use_bundle(dict(small_bundle))
    admin.clear_cache()
    yield
    unusual.use_bundle(None)
    admin.clear_cache()


@pytest.fixture(autouse=True)
def model_off_and_fresh_cache():
    unusual.use_bundle(None)
    admin.clear_cache()
    yield
    unusual.use_bundle(None)
    admin.clear_cache()


def clear(conn, *names):
    conn.execute("DELETE FROM audit_log WHERE username = ANY(%s::text[])", (list(names),))


# ---------------------------------------------------------------- who may call them

@pytest.mark.parametrize("path", ADMIN_PATHS)
def test_only_an_admin_may_open_the_admin_endpoints(anon_client, auth, path):
    assert anon_client.get(path).status_code == 401
    assert anon_client.get(path, headers={"Authorization": "Bearer not.a.token"}).status_code == 401
    assert anon_client.get(path, headers=auth("citizen_a")).status_code == 403
    assert anon_client.get(path, headers=auth("officer")).status_code == 403
    assert anon_client.get(path, headers=auth("admin")).status_code == 200


# ---------------------------------------------------------------- /admin/users

def test_users_list_roles_plots_and_activity_and_never_a_password(anon_client, auth, users, conn):
    clear(conn, "test_citizen_a", "test_officer")
    anon_client.get(f"/plots/{users['citizen_a']['plots'][0]}", headers=auth("citizen_a"))
    anon_client.get(f"/plots/{users['citizen_a']['plots'][1]}", headers=auth("citizen_a"))
    r = anon_client.get("/admin/users", headers=auth("admin"))
    rows = {u["username"]: u for u in r.json()}
    assert all(set(u) == {"username", "role", "plots", "last_active", "actions_30d"} for u in rows.values())
    assert (rows["test_citizen_a"]["role"], rows["test_citizen_a"]["plots"], rows["test_citizen_a"]["actions_30d"]) == ("citizen", 3, 2)
    assert rows["test_citizen_a"]["last_active"] is not None
    assert rows["test_officer"]["actions_30d"] == 0 and rows["test_officer"]["last_active"] is None
    assert rows["test_admin"]["role"] == "admin" and rows["test_admin"]["plots"] == 0
    text = r.text.lower()
    for word in ("password", "hash", "argon", "$argon2", "secret", "token"):
        assert word not in text
    for password in (u["password"] for u in users.values()):
        assert password not in r.text
    assert not re.search(r"\b[A-Z]{2}\d{12}\b", r.text)                           # no plot ids either: only a count


def test_users_are_sorted_admins_first_then_officers_then_citizens(anon_client, auth):
    order = [u["role"] for u in anon_client.get("/admin/users", headers=auth("admin")).json()]
    rank = {"admin": 0, "officer": 1, "citizen": 2}
    assert [rank[r] for r in order] == sorted(rank[r] for r in order)


# ---------------------------------------------------------------- /admin/system

def test_system_reports_the_parts_and_versions_and_nothing_secret(anon_client, auth, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-LEAK-ME-12345")
    r = anon_client.get("/admin/system", headers=auth("admin"))
    body = r.json()
    assert set(body) == {"checked_at", "api", "api_started_at", "api_version", "database", "postgis", "ai_explainer", "model", "counts", "versions"}
    assert body["api"]["state"] == "ok" and body["database"]["state"] == "ok" and body["postgis"]["state"] == "ok"
    assert "PostGIS" in body["postgis"]["detail"] and re.match(r"\d+", body["versions"]["postgresql"])
    assert body["counts"]["plots"] == 100 and body["counts"]["users"] >= 4
    for secret in ("sk-LEAK-ME", "JWT", "password", "postgres://", "postgresql://", "C:\\", "/Users/", "OneDrive"):
        assert secret not in r.text


def test_the_ai_explainer_is_reported_from_the_settings_without_calling_it(anon_client, auth, monkeypatch):
    assert anon_client.get("/admin/system", headers=auth("admin")).json()["ai_explainer"]["state"] == "off"   # the tests switch the AI off
    monkeypatch.setattr(llm, "is_on", lambda: True)
    monkeypatch.setattr(llm, "_post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("the status page must not call the AI")))
    assert anon_client.get("/admin/system", headers=auth("admin")).json()["ai_explainer"]["state"] == "ok"


def test_the_model_block_says_whether_a_model_is_loaded(anon_client, auth, model_on, small_bundle):
    model = anon_client.get("/admin/system", headers=auth("admin")).json()["model"]
    assert model["loaded"] is True and model["trained_on_plots"] == small_bundle["n_train"]
    assert model["explanation_method"] in ("shap", "z-score") and model["flag_percentile"] == small_bundle["percentile"]
    unusual.use_bundle(None)
    off = anon_client.get("/admin/system", headers=auth("admin")).json()["model"]
    assert off["loaded"] is False and off["trained_on_plots"] is None and off["explanation_method"] is None


# ---------------------------------------------------------------- /admin/insights

def test_insights_without_a_model_say_so_and_return_no_numbers(anon_client, auth):
    body = anon_client.get("/admin/insights", headers=auth("admin")).json()
    assert body["available"] is False and body["features"] == [] and body["flagged"] == 0
    assert "never changes a score" in body["note"]


def test_insights_explain_the_model_in_plain_words(anon_client, auth, model_on, small_bundle):
    body = anon_client.get("/admin/insights", headers=auth("admin")).json()
    assert body["available"] is True and body["plots_checked"] == 100 and body["trained_on_plots"] == small_bundle["n_train"]
    assert 0 <= body["flagged_also_amber_or_red"] <= body["flagged"] <= 100
    feats = body["features"]
    assert len(feats) == 12 and all(set(f) == {"name", "label", "share", "top_reason_for"} for f in feats)
    assert sum(f["share"] for f in feats) == pytest.approx(1.0, abs=0.01)
    assert [f["share"] for f in feats] == sorted((f["share"] for f in feats), reverse=True)
    assert all(f["label"] and f["label"] != f["name"] and "_" not in f["label"] for f in feats)      # words, not column names
    assert sum(f["top_reason_for"] for f in feats) <= body["flagged"]
    assert "Explanation only" in body["note"] and "adds no points" in body["note"]


def test_insights_change_no_score_and_no_band(anon_client, auth, model_on):
    before = anon_client.get("/plots", headers=auth("officer")).json()
    anon_client.get("/admin/insights", headers=auth("admin"))
    after = anon_client.get("/plots", headers=auth("officer")).json()
    assert before == after


def test_everything_flagged_and_nothing_flagged(anon_client, auth, small_bundle):
    unusual.use_bundle({**small_bundle, "threshold": -1.0})
    assert anon_client.get("/admin/insights", headers=auth("admin")).json()["flagged"] == 100
    admin.clear_cache()
    unusual.use_bundle({**small_bundle, "threshold": 99.0})
    body = anon_client.get("/admin/insights", headers=auth("admin")).json()
    assert body["flagged"] == 0 and body["flagged_also_amber_or_red"] == 0 and all(f["top_reason_for"] == 0 for f in body["features"])


def test_the_insights_are_cached_for_a_few_minutes(anon_client, auth, model_on, monkeypatch):
    calls = []
    real = admin._compute
    monkeypatch.setattr(admin, "_compute", lambda *a: calls.append(1) or real(*a))
    first = anon_client.get("/admin/insights", headers=auth("admin")).json()
    second = anon_client.get("/admin/insights", headers=auth("admin")).json()
    assert first == second and len(calls) == 1
    admin.clear_cache()
    anon_client.get("/admin/insights", headers=auth("admin"))
    assert len(calls) == 2


# ---------------------------------------------------------------- GET /audit: filters and pages

def seed_rows(anon_client, auth, users, conn):
    clear(conn, "test_citizen_a", "test_citizen_b", "test_officer")
    a, b = users["citizen_a"]["plots"], users["citizen_b"]["plots"]
    anon_client.get(f"/plots/{a[0]}", headers=auth("citizen_a"))                    # view_passport
    anon_client.get(f"/plots/{a[1]}", headers=auth("citizen_a"))                    # view_passport
    anon_client.get(f"/plots/{b[0]}", headers=auth("citizen_a"))                    # view_passport_denied
    anon_client.get(f"/plots/{b[0]}", headers=auth("citizen_b"))                    # view_passport
    anon_client.post("/guide/ask", headers=auth("officer"), json={"question": "What is a ULPIN?"})   # guide_ask


def test_audit_can_filter_by_action_and_reports_the_total_in_a_header(anon_client, auth, users, conn):
    seed_rows(anon_client, auth, users, conn)
    r = anon_client.get("/audit", headers=auth("admin"), params={"action": "view_passport", "username": "test_citizen_a"})
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "2" and {e["action"] for e in r.json()} == {"view_passport"}
    r = anon_client.get("/audit", headers=auth("admin"), params={"action": "view_passport_denied"})
    assert [e["username"] for e in r.json() if e["username"].startswith("test_")] == ["test_citizen_a"]
    assert anon_client.get("/audit", headers=auth("admin"), params={"action": "guide_ask", "username": "test_officer"}).headers["X-Total-Count"] == "1"
    assert anon_client.get("/audit", headers=auth("admin"), params={"action": "no_such_action"}).json() == []


def test_audit_pages_do_not_overlap_and_add_up(anon_client, auth, users, conn):
    seed_rows(anon_client, auth, users, conn)
    params = {"username": "test_citizen_a"}
    full = anon_client.get("/audit", headers=auth("admin"), params={**params, "limit": 500}).json()
    p1 = anon_client.get("/audit", headers=auth("admin"), params={**params, "limit": 2, "offset": 0})
    p2 = anon_client.get("/audit", headers=auth("admin"), params={**params, "limit": 2, "offset": 2})
    assert p1.headers["X-Total-Count"] == p2.headers["X-Total-Count"] == str(len(full)) == "3"
    assert [e["id"] for e in p1.json() + p2.json()] == [e["id"] for e in full]
    assert anon_client.get("/audit", headers=auth("admin"), params={**params, "offset": 99}).json() == []
    assert anon_client.get("/audit", headers=auth("admin"), params={"offset": -1}).status_code == 422
    assert anon_client.get("/audit", headers=auth("admin"), params={"offset": 1_000_001}).status_code == 422


def test_audit_can_filter_by_a_time_range(anon_client, auth, users, conn):
    seed_rows(anon_client, auth, users, conn)
    now = datetime.now(timezone.utc)
    iso = lambda d: d.isoformat()  # noqa: E731
    day = anon_client.get("/audit", headers=auth("admin"), params={"since": iso(now - timedelta(hours=24)), "username": "test_citizen_a"})
    assert day.headers["X-Total-Count"] == "3"
    future = anon_client.get("/audit", headers=auth("admin"), params={"since": iso(now + timedelta(hours=1)), "username": "test_citizen_a"})
    assert future.json() == [] and future.headers["X-Total-Count"] == "0"
    old = anon_client.get("/audit", headers=auth("admin"), params={"until": iso(now - timedelta(days=1)), "username": "test_citizen_a"})
    assert old.json() == []
    inside = anon_client.get("/audit", headers=auth("admin"), params={"since": iso(now - timedelta(hours=1)), "until": iso(now + timedelta(hours=1)), "username": "test_citizen_a"})
    assert inside.headers["X-Total-Count"] == "3"
    assert anon_client.get("/audit", headers=auth("admin"), params={"since": "not a date"}).status_code == 422


def test_the_audit_log_is_still_admin_only_and_the_total_header_is_exposed_to_browsers(anon_client, auth):
    assert anon_client.get("/audit", headers=auth("officer")).status_code == 403
    assert anon_client.get("/audit", headers=auth("citizen_a")).status_code == 403
    r = anon_client.options("/audit", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.status_code == 200
    got = anon_client.get("/audit", headers={**auth("admin"), "Origin": "http://localhost:5173"})
    assert "x-total-count" in got.headers["access-control-expose-headers"].lower()
