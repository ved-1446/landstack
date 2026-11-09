"""Phase 7: login, tokens, roles, citizen isolation, audit log, rate limits, and secrets handling.

Runs on the live Docker database (skipped if it is down). It creates its own throw-away users
(see conftest.py) and removes them, and every audit row they caused, at the end. It never touches
plots or records, so planted_truth.json still matches.
"""
import base64
import json
import logging
import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import jwt
import pytest

import seed
import seed_users
from backend.app import audit, auth, config, db, limits, security
from backend.app.main import app, hide_other_plots

ROOT = Path(__file__).resolve().parents[2]
UNKNOWN = "MH999999999999"
ULPIN_LIKE = re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{14}\b")
WHO = ["admin", "officer", "citizen_a", "citizen_b"]


def audit_rows(conn, username):
    return conn.execute("SELECT ulpin, action, role FROM audit_log WHERE username = %s ORDER BY id",
                        (username,)).fetchall()


def clear_audit(conn, *usernames):
    conn.execute("DELETE FROM audit_log WHERE username = ANY(%s::text[])", (list(usernames),))


def login(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


# ============================ login ============================

def test_login_success(anon_client, users):
    u = users["citizen_a"]
    r = login(anon_client, u["username"], u["password"])
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"access_token", "token_type", "expires_in", "user"}
    assert body["token_type"] == "bearer" and body["expires_in"] == 3600
    assert body["user"] == {"username": "test_citizen_a", "role": "citizen"}
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["sub"] == "test_citizen_a" and claims["role"] == "citizen"
    assert claims["exp"] - claims["iat"] == 3600          # the 60-minute lifetime
    assert "password" not in json.dumps(claims)


def test_wrong_password_and_unknown_user_look_identical(anon_client, users):
    wrong_password = login(anon_client, users["admin"]["username"], "definitely-not-the-password")
    unknown_user = login(anon_client, "no_such_user", "definitely-not-the-password")
    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json() == unknown_user.json() == {"detail": "Incorrect username or password"}
    assert wrong_password.headers["www-authenticate"] == unknown_user.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("body", [{}, {"username": "x"}, {"username": "", "password": "x"},
                                  {"username": "x", "password": "p" * 300}])
def test_login_rejects_bad_input(anon_client, body):
    assert anon_client.post("/auth/login", json=body).status_code == 422


def test_me_returns_the_logged_in_user_only(anon_client, auth):
    r = anon_client.get("/auth/me", headers=auth("officer"))
    assert r.status_code == 200 and r.json() == {"username": "test_officer", "role": "officer"}


# ============================ bad tokens ============================

def _b64(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def _tamper_payload(token, **changes):
    head, payload, signature = token.split(".")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    data.update(changes)
    return f"{head}.{_b64(data)}.{signature}"      # old signature no longer fits


def _bad_tokens(good):
    secret = security.get_settings().jwt_secret
    future = {"sub": "test_admin", "exp": 4102444800}
    return {
        "garbage": "not-a-token",
        "payload_tampered": _tamper_payload(good, role="admin", sub="test_admin"),
        "signature_flipped": good[:-1] + ("A" if good[-1] != "A" else "B"),
        "signed_with_other_secret": jwt.encode(future, "x" * 48, algorithm="HS256"),
        "expired": security.create_access_token("test_officer", "officer", lifetime=timedelta(minutes=-5)),
        "alg_none_unsigned": jwt.encode(future, None, algorithm="none"),
        "no_expiry": jwt.encode({"sub": "test_admin"}, secret, algorithm="HS256"),
        "no_subject": jwt.encode({"exp": 4102444800}, secret, algorithm="HS256"),
    }


@pytest.mark.parametrize("name", ["garbage", "payload_tampered", "signature_flipped", "signed_with_other_secret",
                                  "expired", "alg_none_unsigned", "no_expiry", "no_subject"])
@pytest.mark.parametrize("path", ["/auth/me", "/plots", "/summary"])
def test_bad_tokens_are_refused(anon_client, tokens, name, path):
    token = _bad_tokens(tokens["citizen_a"])[name]
    r = anon_client.get(path, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid or expired token"}
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic dXNlcjpwYXNz"}, {"Authorization": "Bearer"}])
def test_missing_or_wrong_kind_of_credentials(anon_client, headers):
    r = anon_client.get("/plots", headers=headers)
    assert r.status_code == 401 and r.json() == {"detail": "Not authenticated"}


def _temp_user(conn, role):
    conn.execute("DELETE FROM users WHERE username = 'test_temp'")
    password = "Temp-" + security.hash_password("x")[-12:]
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES ('test_temp', %s, %s)",
                 (security.hash_password(password), role))
    return password


def test_role_is_read_from_the_database_not_from_the_token(anon_client, conn):
    password = _temp_user(conn, "officer")
    try:
        token = login(anon_client, "test_temp", password).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        assert anon_client.get("/summary", headers=headers).status_code == 200
        conn.execute("UPDATE users SET role = 'citizen' WHERE username = 'test_temp'")   # demoted; old token still says officer
        assert anon_client.get("/summary", headers=headers).status_code == 403
        conn.execute("DELETE FROM users WHERE username = 'test_temp'")                   # deleted: token is dead at once
        assert anon_client.get("/auth/me", headers=headers).status_code == 401
    finally:
        conn.execute("DELETE FROM users WHERE username = 'test_temp'")


# ============================ role matrix ============================
# None = not logged in. Every endpoint against every role.

def _own(users):
    return users["citizen_a"]["plots"][0]


MATRIX = [
    ("/health", lambda u: "/health", {None: 200, "citizen_a": 200, "citizen_b": 200, "officer": 200, "admin": 200}),
    ("/conflict-types", lambda u: "/conflict-types",
     {None: 401, "citizen_a": 200, "citizen_b": 200, "officer": 200, "admin": 200}),
    ("/plots", lambda u: "/plots", {None: 401, "citizen_a": 200, "citizen_b": 200, "officer": 200, "admin": 200}),
    ("/plots/<A's plot>", lambda u: f"/plots/{_own(u)}",
     {None: 401, "citizen_a": 200, "citizen_b": 404, "officer": 200, "admin": 200}),
    ("/plots/<unknown>", lambda u: f"/plots/{UNKNOWN}",
     {None: 401, "citizen_a": 404, "citizen_b": 404, "officer": 404, "admin": 404}),
    ("/summary", lambda u: "/summary", {None: 401, "citizen_a": 403, "citizen_b": 403, "officer": 200, "admin": 200}),
    ("/audit", lambda u: "/audit", {None: 401, "citizen_a": 403, "citizen_b": 403, "officer": 403, "admin": 200}),
    ("/auth/me", lambda u: "/auth/me", {None: 401, "citizen_a": 200, "citizen_b": 200, "officer": 200, "admin": 200}),
]
CASES = [(name, make, who, status) for name, make, expected in MATRIX for who, status in expected.items()]


@pytest.mark.parametrize("name,make,who,status", CASES,
                         ids=[f"{n}-{w or 'anonymous'}" for n, _, w, _ in CASES])
def test_role_matrix(anon_client, auth, users, name, make, who, status):
    headers = auth(who) if who else {}
    assert anon_client.get(make(users), headers=headers).status_code == status


def test_login_is_open_to_everyone(anon_client):
    assert anon_client.post("/auth/login", json={"username": "a", "password": "b"}).status_code == 401  # not 403/404


# ============================ citizens only see their own plots ============================

def test_citizen_plot_list_is_exactly_their_plots(anon_client, auth, users):
    seen = {}
    for who in ("citizen_a", "citizen_b"):
        body = anon_client.get("/plots", headers=auth(who)).json()
        seen[who] = {f["properties"]["ulpin"] for f in body["features"]}
        assert seen[who] == set(users[who]["plots"])
    assert not seen["citizen_a"] & seen["citizen_b"]
    officer = anon_client.get("/plots", headers=auth("officer")).json()["features"]
    assert len(officer) == 100


def test_citizen_filters_stay_inside_their_own_plots(anon_client, auth, users):
    mine = set(users["citizen_a"]["plots"])
    for params in ({}, {"band": "amber"}, {"band": "green"}, {"village": "Hinjewadi"}, {"conflict_type": "boundary_overlap"}):
        feats = anon_client.get("/plots", params=params, headers=auth("citizen_a")).json()["features"]
        assert {f["properties"]["ulpin"] for f in feats} <= mine
    amber = anon_client.get("/plots", params={"band": "amber"}, headers=auth("citizen_a")).json()["features"]
    assert [f["properties"]["ulpin"] for f in amber] == [users["citizen_a"]["plots"][0]]


def test_citizen_never_gets_another_citizens_plot(anon_client, auth, users):
    unknown = anon_client.get(f"/plots/{UNKNOWN}", headers=auth("citizen_a"))
    for ulpin in users["citizen_b"]["plots"]:
        r = anon_client.get(f"/plots/{ulpin}", headers=auth("citizen_a"))
        assert r.status_code == 404                                   # not 403: does not reveal the plot exists
        assert r.json() == {"detail": f"No plot found with ulpin {ulpin}"}
        assert r.json()["detail"].replace(ulpin, "X") == unknown.json()["detail"].replace(UNKNOWN, "X")
        assert ulpin not in r.text.replace(f"ulpin {ulpin}", "")      # only the echo of what they typed


def test_citizen_cannot_learn_other_plots_ids_from_evidence(anon_client, auth, users):
    overlap_plot = users["citizen_a"]["plots"][0]
    staff = anon_client.get(f"/plots/{overlap_plot}", headers=auth("officer")).json()
    partner = ULPIN_LIKE.search(staff["findings"][0]["evidence"]).group(0)
    assert partner not in users["citizen_a"]["plots"]
    citizen = anon_client.get(f"/plots/{overlap_plot}", headers=auth("citizen_a")).json()
    assert partner not in json.dumps(citizen)
    assert "another plot" in citizen["findings"][0]["evidence"]
    assert citizen["findings"][0]["points"] == staff["findings"][0]["points"]       # scores are untouched
    assert citizen["score"] == staff["score"] and citizen["band"] == staff["band"]
    for ulpin in users["citizen_a"]["plots"]:
        text = json.dumps(anon_client.get(f"/plots/{ulpin}", headers=auth("citizen_a")).json())
        assert set(ULPIN_LIKE.findall(text)) <= set(users["citizen_a"]["plots"])


def test_hide_other_plots_keeps_own_ids():
    findings = [{"type": "boundary_overlap", "points": 40,
                 "evidence": "overlaps plot MH000100000001 by 5 sq m; also plot MH000100000002 and MH000100000003"}]
    out = hide_other_plots(findings, {"MH000100000001"})[0]["evidence"]
    assert out == "overlaps plot MH000100000001 by 5 sq m; also another plot and another plot"


# ============================ audit log ============================

def test_every_passport_view_is_audited_including_denied(anon_client, auth, users, conn):
    a, b = users["citizen_a"], users["citizen_b"]
    clear_audit(conn, "test_citizen_a", "test_officer")

    assert anon_client.get(f"/plots/{a['plots'][0]}", headers=auth("citizen_a")).status_code == 200
    assert anon_client.get(f"/plots/{a['plots'][1]}", headers=auth("citizen_a")).status_code == 200
    assert anon_client.get(f"/plots/{b['plots'][0]}", headers=auth("citizen_a")).status_code == 404    # denied
    assert anon_client.get(f"/plots/{UNKNOWN}", headers=auth("citizen_a")).status_code == 404          # looks the same
    assert audit_rows(conn, "test_citizen_a") == [
        (a["plots"][0], "view_passport", "citizen"),
        (a["plots"][1], "view_passport", "citizen"),
        (b["plots"][0], "view_passport_denied", "citizen"),
        (UNKNOWN, "view_passport_denied", "citizen"),
    ]

    assert anon_client.get(f"/plots/{b['plots'][1]}", headers=auth("officer")).status_code == 200
    assert anon_client.get(f"/plots/{UNKNOWN}", headers=auth("officer")).status_code == 404
    assert audit_rows(conn, "test_officer") == [
        (b["plots"][1], "view_passport", "officer"),
        (UNKNOWN, "view_passport_not_found", "officer"),
    ]


def test_listing_plots_and_other_calls_are_not_audited(anon_client, auth, conn):
    clear_audit(conn, "test_officer")
    for path in ("/plots", "/summary", "/conflict-types", "/auth/me", "/health"):
        anon_client.get(path, headers=auth("officer"))
    assert audit_rows(conn, "test_officer") == []


def test_audit_endpoint_newest_first_with_filters(anon_client, auth, users, conn):
    a, b = users["citizen_a"], users["citizen_b"]
    clear_audit(conn, "test_admin", "test_officer", "test_citizen_a", "test_citizen_b")
    anon_client.get(f"/plots/{a['plots'][0]}", headers=auth("citizen_a"))
    anon_client.get(f"/plots/{b['plots'][0]}", headers=auth("citizen_a"))
    anon_client.get(f"/plots/{b['plots'][0]}", headers=auth("citizen_b"))
    anon_client.get(f"/plots/{a['plots'][2]}", headers=auth("officer"))

    everything = anon_client.get("/audit", headers=auth("admin"), params={"limit": 500}).json()
    mine = [e for e in everything if e["username"].startswith("test_")]
    assert [e["id"] for e in everything] == sorted((e["id"] for e in everything), reverse=True)   # newest first
    assert [(e["username"], e["ulpin"], e["action"]) for e in mine] == [
        ("test_officer", a["plots"][2], "view_passport"),
        ("test_citizen_b", b["plots"][0], "view_passport"),
        ("test_citizen_a", b["plots"][0], "view_passport_denied"),
        ("test_citizen_a", a["plots"][0], "view_passport"),
    ]
    assert set(mine[0]) == {"id", "username", "role", "ulpin", "action", "looked_at"}

    by_user = anon_client.get("/audit", headers=auth("admin"), params={"username": "test_citizen_a"}).json()
    assert [e["username"] for e in by_user] == ["test_citizen_a"] * 2
    by_plot = anon_client.get("/audit", headers=auth("admin"), params={"ulpin": b["plots"][0]}).json()
    assert [e["username"] for e in by_plot] == ["test_citizen_b", "test_citizen_a"]
    both = anon_client.get("/audit", headers=auth("admin"),
                           params={"username": "test_citizen_a", "ulpin": a["plots"][0]}).json()
    assert len(both) == 1
    assert len(anon_client.get("/audit", headers=auth("admin"), params={"limit": 2}).json()) == 2
    assert anon_client.get("/audit", headers=auth("admin"), params={"limit": 0}).status_code == 422
    assert anon_client.get("/audit", headers=auth("admin"), params={"username": "nobody_at_all"}).json() == []


def test_a_failing_audit_write_does_not_break_the_request(anon_client, auth, users, conn, monkeypatch, caplog):
    clear_audit(conn, "test_officer")
    monkeypatch.setattr(audit, "INSERT_SQL", "INSERT INTO table_that_does_not_exist VALUES (1)")
    with caplog.at_level(logging.ERROR, logger="landstack.audit"):
        r = anon_client.get(f"/plots/{users['citizen_a']['plots'][0]}", headers=auth("officer"))
    assert r.status_code == 200 and r.json()["ulpin"] == users["citizen_a"]["plots"][0]
    assert "could not write audit row" in caplog.text          # the failure is logged...
    assert audit_rows(conn, "test_officer") == []              # ...and nothing half-written was left behind
    monkeypatch.undo()
    assert anon_client.get(f"/plots/{users['citizen_a']['plots'][0]}", headers=auth("officer")).status_code == 200
    assert len(audit_rows(conn, "test_officer")) == 1          # and the next view is logged normally


# ============================ rate limits ============================

def test_login_is_limited_per_ip(anon_client, users, monkeypatch):
    monkeypatch.setattr(config, "RATE_LOGIN", "3/minute")
    for _ in range(3):
        assert login(anon_client, "test_admin", "wrong").status_code == 401
    blocked = login(anon_client, "test_admin", "wrong")
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["retry-after"]) <= 60
    assert blocked.json()["detail"].startswith("Too many requests")
    good = users["admin"]
    assert login(anon_client, good["username"], good["password"]).status_code == 429     # even the right password waits


def test_other_requests_are_limited_per_user(anon_client, auth, monkeypatch):
    monkeypatch.setattr(config, "RATE_DEFAULT", "3/minute")
    for _ in range(3):
        assert anon_client.get("/conflict-types", headers=auth("officer")).status_code == 200
    blocked = anon_client.get("/conflict-types", headers=auth("officer"))
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) >= 1
    assert "Too many requests" in blocked.json()["detail"]
    assert anon_client.get("/conflict-types", headers=auth("citizen_a")).status_code == 200   # another user: own allowance
    assert anon_client.get("/plots", headers=auth("officer")).status_code == 429              # every endpoint shares it


def test_login_limit_does_not_use_up_a_users_allowance(anon_client, auth, monkeypatch):
    monkeypatch.setattr(config, "RATE_LOGIN", "1/minute")
    login(anon_client, "x", "y")
    assert login(anon_client, "x", "y").status_code == 429
    assert anon_client.get("/auth/me", headers=auth("officer")).status_code == 200


# ============================ secrets never leak ============================

def test_no_response_ever_contains_a_password_or_hash(anon_client, auth, users, conn):
    hashes = [h for (h,) in conn.execute("SELECT password_hash FROM users")]
    assert hashes and all(h.startswith("$argon2") for h in hashes)
    secrets_ = hashes + [u["password"] for u in users.values()] + ["password_hash", "argon2"]
    texts = [anon_client.get("/openapi.json").text]
    paths = ["/health", "/plots", f"/plots/{users['citizen_a']['plots'][0]}", "/summary", "/conflict-types",
             "/audit", "/auth/me", f"/plots/{UNKNOWN}"]
    for who in [None] + WHO:
        for path in paths:
            texts.append(anon_client.get(path, headers=auth(who) if who else {}).text)
    for who, u in users.items():
        texts.append(login(anon_client, u["username"], u["password"]).text)
        texts.append(login(anon_client, u["username"], "wrong-password").text)
    body = "\n".join(texts)
    for secret in secrets_:
        assert secret not in body


def test_plain_passwords_are_never_logged(anon_client, users, caplog):
    caplog.set_level(logging.DEBUG)
    u = users["citizen_b"]
    login(anon_client, u["username"], u["password"])
    login(anon_client, u["username"], "a-wrong-password-9f3k")
    login(anon_client, "no_such_user_zz", "another-wrong-password-4d8")
    for text in (u["password"], "a-wrong-password-9f3k", "another-wrong-password-4d8"):
        assert text not in caplog.text


def test_the_database_holds_only_hashes(conn, users):
    for u in users.values():
        (stored,) = conn.execute("SELECT password_hash FROM users WHERE username = %s", (u["username"],)).fetchone()
        assert stored != u["password"] and u["password"] not in stored and stored.startswith("$argon2id$")


# ============================ hashing, tokens, start-up (no database) ============================

def test_hashing_is_salted_one_way_and_checked():
    h1, h2 = security.hash_password("correct horse"), security.hash_password("correct horse")
    assert h1 != h2 and h1.startswith("$argon2id$") and "correct horse" not in h1      # random salt, not encryption
    assert security.verify_password(h1, "correct horse") is True
    assert security.verify_password(h1, "wrong") is False
    assert security.verify_password(None, "anything") is False                         # unknown user
    assert security.verify_password("not-a-hash", "x") is False


def test_token_round_trip_and_expiry():
    token = security.create_access_token("someone", "citizen")
    claims = security.decode_access_token(token)
    assert claims["sub"] == "someone" and claims["role"] == "citizen"
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_access_token(security.create_access_token("x", "citizen", lifetime=timedelta(seconds=-1)))


@pytest.mark.parametrize("env,message", [
    ({}, "not set"),
    ({"JWT_SECRET": ""}, "not set"),
    ({"JWT_SECRET": config.JWT_SECRET_PLACEHOLDER}, "placeholder"),
    ({"JWT_SECRET": "change-me-" + "x" * 40}, "placeholder"),
    ({"JWT_SECRET": "short"}, "too short"),
    ({"JWT_SECRET": "s" * 40, "JWT_EXPIRE_MINUTES": "soon"}, "whole number"),
    ({"JWT_SECRET": "s" * 40, "JWT_EXPIRE_MINUTES": "0"}, "more than zero"),
])
def test_settings_refuse_a_missing_or_weak_secret(env, message):
    with pytest.raises(RuntimeError, match=message):
        security.load_settings(env)


def test_settings_defaults_to_sixty_minutes():
    assert security.load_settings({"JWT_SECRET": "s" * 40}).token_minutes == 60
    assert security.load_settings({"JWT_SECRET": "s" * 40, "JWT_EXPIRE_MINUTES": "15"}).token_minutes == 15


@pytest.mark.parametrize("secret,message", [("", "JWT_SECRET is not set"),
                                            (config.JWT_SECRET_PLACEHOLDER, "placeholder")])
def test_the_app_will_not_start_without_a_real_secret(secret, message):
    import os
    env = {**os.environ, "JWT_SECRET": secret}     # an empty / placeholder value beats whatever .env says
    done = subprocess.run([sys.executable, "-c", "import backend.app.main"], cwd=ROOT, env=env,
                          capture_output=True, text=True, timeout=60)
    assert done.returncode != 0
    assert message in done.stderr


# ============================ CORS for the login page ============================

def test_cors_preflight_for_login_and_authorization_header(anon_client):
    r = anon_client.options("/auth/login", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization,content-type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in r.headers["access-control-allow-methods"]
    assert "authorization" in r.headers["access-control-allow-headers"].lower()
    bad = anon_client.options("/auth/login", headers={"Origin": "http://evil.example",
                                                       "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_retry_after_is_readable_by_the_browser(anon_client):
    r = anon_client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "retry-after" in r.headers["access-control-expose-headers"].lower()


# ============================ demo users script ============================

@pytest.fixture(scope="module")
def demo():
    data = seed.generate()
    ulpins = [p["ulpin"] for p in data["rows"]["plots"]]
    return data["truth"], seed_users.build_demo_users(ulpins, data["truth"])


def test_demo_users_shape(demo):
    truth, built = demo
    assert sorted((u["username"], u["role"]) for u in built) == [
        ("admin", "admin"), ("citizen1", "citizen"), ("citizen2", "citizen"), ("officer", "officer")]
    citizens = [u for u in built if u["role"] == "citizen"]
    assert all(len(c["plots"]) == 3 and len(set(c["plots"])) == 3 for c in citizens)
    assert not set(citizens[0]["plots"]) & set(citizens[1]["plots"])
    for c in citizens:
        assert any(p in truth["conflicts"] for p in c["plots"])       # at least one problem plot each
    assert [u["plots"] for u in built if u["role"] != "citizen"] == [[], []]


def test_demo_users_are_stored_as_hashes_only(demo):
    _, built = demo
    passwords = {name: pw for name, _, pw in seed_users.DEMO_USERS}
    for u in built:
        assert u["password_hash"].startswith("$argon2id$")
        assert security.verify_password(u["password_hash"], passwords[u["username"]])
        assert passwords[u["username"]] not in json.dumps(u)


def test_demo_users_load_is_repeatable_and_leaves_nothing_behind(demo, conn):
    _, built = demo
    names = [u["username"] for u in built]
    snap = lambda c: (c.execute("SELECT username, role FROM users WHERE username = ANY(%s::text[]) ORDER BY 1",  # noqa: E731
                                (names,)).fetchall(),
                      c.execute("SELECT username, ulpin FROM user_plots WHERE username = ANY(%s::text[]) ORDER BY 1, 2",
                                (names,)).fetchall())
    before = snap(conn)
    tx = db.connect()
    try:
        seed_users.load_users(tx, built)
        once = snap(tx)
        seed_users.load_users(tx, built)             # run it twice
        assert snap(tx) == once
        assert [r[0] for r in once[0]] == sorted(names) and len(once[1]) == 6
    finally:
        tx.rollback()
        tx.close()
    assert snap(conn) == before
