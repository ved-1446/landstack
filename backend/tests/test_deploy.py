"""Phase 14a: what makes the app deployable. A single DATABASE_URL, the real visitor address behind a proxy, and several CORS origins.
None of these touch scoring, the checks or the data."""
import pytest
from starlette.requests import Request

from backend.app import config, db, limits, security


# ---------------------------------------------------------------- DATABASE_URL
def test_database_url_is_off_when_not_set():
    assert db.database_url({}) is None
    assert db.database_url({"DATABASE_URL": "   "}) is None


def test_database_url_adds_sslmode_require_when_missing():
    assert db.database_url({"DATABASE_URL": "postgresql://u:p@host.example/neondb"}) == "postgresql://u:p@host.example/neondb?sslmode=require"
    assert db.database_url({"DATABASE_URL": "postgres://u:p@h/db?application_name=x"}) == "postgres://u:p@h/db?application_name=x&sslmode=require"


def test_database_url_keeps_an_sslmode_it_is_given():
    url = "postgresql://u:p@h/db?sslmode=verify-full"
    assert db.database_url({"DATABASE_URL": url}) == url


def test_database_url_must_be_a_postgres_address():
    with pytest.raises(RuntimeError, match="postgresql://"):
        db.database_url({"DATABASE_URL": "mysql://u:p@h/db"})


def test_connect_args_prefers_the_url_and_falls_back_to_the_local_variables():
    args, kwargs = db.connect_args({"DATABASE_URL": "postgresql://u:p@h/db", "POSTGRES_PASSWORD": "local"})
    assert args == ("postgresql://u:p@h/db?sslmode=require",) and kwargs == {}
    # the local Docker flow is unchanged: same defaults as before
    args, kwargs = db.connect_args({"POSTGRES_PASSWORD": "local"})
    assert args == ()
    assert kwargs == {"host": "localhost", "port": "5432", "user": "landstack", "password": "local", "dbname": "landstack"}
    args, kwargs = db.connect_args({"POSTGRES_PASSWORD": "x", "POSTGRES_HOST": "db", "POSTGRES_PORT": "6543", "POSTGRES_USER": "u", "POSTGRES_DB": "d"})
    assert kwargs == {"host": "db", "port": "6543", "user": "u", "password": "x", "dbname": "d"}


def test_the_seed_script_uses_the_same_rule(monkeypatch):
    import seed
    seen = {}

    def fake_connect(*args, **kwargs):
        seen.update(args=args, kwargs=kwargs)
        return object()

    import psycopg
    monkeypatch.setattr(psycopg, "connect", fake_connect)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@neon.example/db")
    seed.connect()
    assert seen["args"] == ("postgresql://u:p@neon.example/db?sslmode=require",)


# ---------------------------------------------------------------- the visitor's address behind a proxy
def _request(xff=None, peer="10.0.0.9"):
    headers = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers, "client": (peer, 5555), "query_string": b""})


def test_by_default_the_forwarded_header_is_ignored(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 0)
    assert limits.client_ip(_request("203.0.113.5")) == "10.0.0.9"        # a visitor cannot pick their own address


def test_one_proxy_the_visitor_is_the_last_entry(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 1)
    assert limits.client_ip(_request("203.0.113.5")) == "203.0.113.5"


def test_a_forged_left_hand_entry_is_never_believed(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 1)
    assert limits.client_ip(_request("1.2.3.4, 203.0.113.5")) == "203.0.113.5"
    assert limits.client_ip(_request("9.9.9.9, 8.8.8.8, 203.0.113.5")) == "203.0.113.5"


def test_two_proxies_the_visitor_is_second_from_the_right(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 2)
    assert limits.client_ip(_request("203.0.113.5, 172.16.0.3")) == "203.0.113.5"
    assert limits.client_ip(_request("6.6.6.6, 203.0.113.5, 172.16.0.3")) == "203.0.113.5"


def test_a_missing_short_or_garbled_header_falls_back_to_the_connection(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 2)
    assert limits.client_ip(_request(None)) == "10.0.0.9"
    assert limits.client_ip(_request("203.0.113.5")) == "10.0.0.9"        # fewer entries than trusted proxies: do not guess
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 1)
    assert limits.client_ip(_request("not-an-ip")) == "10.0.0.9"
    assert limits.client_ip(_request("")) == "10.0.0.9"


def test_ipv6_visitors_work(monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 1)
    assert limits.client_ip(_request("2001:db8::1")) == "2001:db8::1"


def test_trusted_proxy_hops_is_validated(monkeypatch):
    monkeypatch.setattr(db, "read_env", lambda: {"TRUSTED_PROXY_HOPS": "many"})
    with pytest.raises(RuntimeError, match="TRUSTED_PROXY_HOPS"):
        limits._read_hops()
    monkeypatch.setattr(db, "read_env", lambda: {"TRUSTED_PROXY_HOPS": "2"})
    assert limits._read_hops() == 2
    monkeypatch.setattr(db, "read_env", lambda: {})
    assert limits._read_hops() == 0


def test_visitors_behind_one_proxy_do_not_share_a_login_limit(anon_client, monkeypatch):
    """Two visitors come through the same proxy address. With the rule on, each has their own 2 tries a minute."""
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 1)
    monkeypatch.setattr(config, "RATE_LOGIN", "2/minute")

    def attempt(visitor):
        return anon_client.post("/auth/login", json={"username": "nobody", "password": "x"}, headers={"X-Forwarded-For": visitor}).status_code

    assert [attempt("203.0.113.10"), attempt("203.0.113.10"), attempt("203.0.113.10")] == [401, 401, 429]
    assert attempt("203.0.113.11") == 401                                    # a different visitor is not blocked
    # trying to dodge the limit by writing a new address on the left does not work
    assert anon_client.post("/auth/login", json={"username": "nobody", "password": "x"},
                            headers={"X-Forwarded-For": "7.7.7.7, 203.0.113.10"}).status_code == 429


def test_without_the_rule_everyone_behind_a_proxy_shares_one_limit(anon_client, monkeypatch):
    monkeypatch.setattr(limits, "TRUSTED_PROXY_HOPS", 0)
    monkeypatch.setattr(config, "RATE_LOGIN", "2/minute")
    codes = [anon_client.post("/auth/login", json={"username": "nobody", "password": "x"}, headers={"X-Forwarded-For": f"203.0.113.{i}"}).status_code for i in range(3)]
    assert codes == [401, 401, 429]                                          # the header was ignored, so the forged addresses did not help


# ---------------------------------------------------------------- CORS_ORIGINS
def test_cors_accepts_several_origins_and_tidies_them():
    env = {"CORS_ORIGINS": "https://landstack.vercel.app/, http://localhost:5173 ,https://demo.example.org"}
    assert security.cors_origins(env) == ["https://landstack.vercel.app", "http://localhost:5173", "https://demo.example.org"]


def test_cors_defaults_to_the_dev_server_and_refuses_wildcards_and_paths():
    assert security.cors_origins({}) == ["http://localhost:5173"]
    for bad in ("*", "https://*.vercel.app", "https://a.example/app", "landstack.vercel.app"):
        with pytest.raises(RuntimeError):
            security.cors_origins({"CORS_ORIGINS": bad})


def test_cors_headers_are_sent_for_an_allowed_origin_only(anon_client):
    ok = anon_client.options("/auth/login", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    other = anon_client.options("/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in other.headers
