"""Phase 12 (checkpoint 1): hardening, the friendly /verify page, the "capped at 100" flag and the X-Document-Id header.
No test here changes any score, band, check or planted data."""
import io
import re
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.app import config, db, main, passport, security, verify_page

DOC_ID = re.compile(r"\b[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}\b")
ULPIN = re.compile(r"\bMH\d{12}\b")            # the demo plot ids (a bare 14-digit run inside a number is not one)
BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
PLOT = "MH000100000006"            # a red plot with four findings (the points add up to 110: capped)


def pdf_text(content):
    reader = PdfReader(io.BytesIO(content))
    return len(reader.pages), " ".join(reader.pages[0].extract_text().split())


def issue_pdf(client, auth, who="officer", ulpin=PLOT):
    r = client.get(f"/plots/{ulpin}/passport.pdf", headers=auth(who))
    assert r.status_code == 200, r.text
    return r


# ====================================================================== B. CORS comes from CORS_ORIGINS, never a wildcard

def test_cors_defaults_to_the_vite_dev_server_only():
    assert security.cors_origins({}) == ["http://localhost:5173"]
    assert security.cors_origins({"CORS_ORIGINS": "  "}) == ["http://localhost:5173"]


def test_cors_origins_can_be_configured_as_a_comma_separated_list():
    env = {"CORS_ORIGINS": "https://landstack.example.org, http://localhost:3000/ ,https://app.example.org:8443"}
    assert security.cors_origins(env) == ["https://landstack.example.org", "http://localhost:3000", "https://app.example.org:8443"]


@pytest.mark.parametrize("bad", ["*", "https://*.example.org", "localhost:5173", "http://localhost:5173/app", "http://a b.example",
                                 "ftp://example.org", "http://localhost:5173,*", "javascript:alert(1)", "http://"])
def test_a_wildcard_or_a_malformed_origin_stops_the_server_from_starting(bad):
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        security.cors_origins({"CORS_ORIGINS": bad})


def test_the_running_app_allows_only_the_configured_origin_and_exposes_the_document_id_header(anon_client):
    ok = anon_client.options("/plots", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET",
                                                "Access-Control-Request-Headers": "authorization"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    bad = anon_client.options("/plots", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
    shown = anon_client.get("/health", headers={"Origin": "http://localhost:5173"})
    exposed = shown.headers["access-control-expose-headers"]
    assert "X-Document-Id" in exposed and "Retry-After" in exposed


# ====================================================================== B. error responses leak no stack trace, SQL or internals

@pytest.fixture
def quiet_client():
    """A client that gets the real 500 response instead of re-raising the server's exception."""
    return TestClient(main.app, raise_server_exceptions=False)


FORBIDDEN_IN_ERRORS = ("Traceback", "File \"", "SELECT", "FROM plots", "psycopg", "RuntimeError", "password", "LEAK-ME", "landstack",
                       "localhost:5432", "site-packages", "backend\\app", "backend/app")


def assert_no_internals(response):
    blob = response.text
    for word in FORBIDDEN_IN_ERRORS:
        assert word.lower() not in blob.lower(), (word, blob[:200])


def test_an_unexpected_server_error_is_a_plain_500_with_no_internals(quiet_client, auth, monkeypatch):
    def boom(conn):
        raise RuntimeError("SELECT * FROM users WHERE password_hash = 'LEAK-ME' at C:\\\\site-packages\\\\psycopg")
    monkeypatch.setattr(main, "scored", boom)
    monkeypatch.setattr(passport, "scored", boom)
    for path in ("/plots", f"/plots/{PLOT}", "/summary"):
        r = quiet_client.get(path, headers=auth("admin"))
        assert r.status_code == 500 and r.json() == {"detail": "Internal server error"}, path
        assert_no_internals(r)


def test_a_database_that_is_down_is_a_plain_503_with_no_host_user_or_password(quiet_client, auth, monkeypatch):
    def down():
        raise psycopg.OperationalError('connection to server at "localhost" (::1), port 5432 failed: FATAL: password authentication failed for user "landstack"')
    headers = auth("officer")                       # log in first: the token does not need the database to be read here
    monkeypatch.setattr(db, "connect", down)
    r = quiet_client.get("/plots", headers=headers)
    assert r.status_code == 503 and r.json() == {"detail": "Database unavailable"}
    assert_no_internals(r)


def test_bad_input_and_unknown_routes_give_short_generic_errors(anon_client, auth):
    for r in (anon_client.get("/plots/not-a-ulpin", headers=auth("officer")), anon_client.get("/no/such/route"),
              anon_client.get("/verify/%00%00%00%00"), anon_client.post("/guide/ask", headers=auth("officer"), json={"question": ""}),
              anon_client.get("/plots", headers={"Authorization": "Bearer not.a.token"})):
        assert r.status_code in (401, 404, 422)
        assert_no_internals(r)


def test_the_server_refuses_to_start_without_a_real_jwt_secret(monkeypatch):
    for value in ("", "change-me-generate-a-long-random-string", "short"):
        with pytest.raises(RuntimeError):
            security.load_settings({"JWT_SECRET": value, "JWT_EXPIRE_MINUTES": "60"})
    with pytest.raises(RuntimeError):
        security.load_settings({"JWT_EXPIRE_MINUTES": "60"})


# ====================================================================== B. the VITE_DEMO_ACCOUNTS row is OFF unless exactly "true"

def test_the_demo_login_row_is_off_by_default():
    source = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "features" / "login" / "demoAccounts.ts").read_text(encoding="utf-8")
    assert 'VITE_DEMO_ACCOUNTS === "true"' in source and '!== "false"' not in source


# ====================================================================== B. a citizen can reach NOTHING that is not theirs, on ANY endpoint

# (method, path) -> what a citizen gets, and what a visitor with no login gets. A new endpoint makes the first test below fail
# until someone decides who may use it and adds it here with a test.
MATRIX = {
    ("GET", "/health"): ("open", 200),
    ("POST", "/auth/login"): ("open", None),
    ("GET", "/auth/me"): (200, 401),
    ("GET", "/conflict-types"): (200, 401),
    ("GET", "/plots"): ("only their own plots", 401),
    ("GET", "/plots/{ulpin}"): ("own 200, other 404", 401),
    ("POST", "/plots/{ulpin}/explain"): ("own 200, other 404", 401),
    ("GET", "/plots/{ulpin}/passport.pdf"): ("own 200, other 404", 401),
    ("GET", "/construction-alerts"): ("only their own plots", 401),
    ("POST", "/guide/ask"): (200, 401),
    ("GET", "/summary"): (403, 401),
    ("GET", "/audit"): (403, 401),
    ("GET", "/verify/{doc_id}"): ("open", None),
    ("GET", "/public/stats"): ("open", None),            # Phase 13a: public by design, counts only (tested in test_public.py)
    ("GET", "/public/plot/{ulpin}"): ("open", None),    # Phase 13a: public by design, village and band only
}


def test_every_endpoint_has_a_decision_in_the_matrix(anon_client):
    routes = {(method.upper(), path) for path, item in anon_client.get("/openapi.json").json()["paths"].items() for method in item}
    assert routes == set(MATRIX), (routes ^ set(MATRIX))


def other_plot(users):
    return users["citizen_b"]["plots"][0]


def test_citizens_and_visitors_get_exactly_what_the_matrix_says(anon_client, auth, users):
    own, other = users["citizen_a"]["plots"][0], other_plot(users)
    for (method, template), (citizen, anonymous) in MATRIX.items():
        if citizen == "open" or anonymous is None:
            continue
        path = template.replace("{ulpin}", own)
        body = {"question": "What is a ULPIN?"} if template == "/guide/ask" else ({} if method == "POST" else None)
        as_citizen = anon_client.request(method, path, headers=auth("citizen_a"), json=body)
        no_login = anon_client.request(method, path, json=body)
        bad_token = anon_client.request(method, path, headers={"Authorization": "Bearer not.a.token"}, json=body)
        if isinstance(citizen, int):
            assert as_citizen.status_code == citizen, (method, template, as_citizen.status_code)
        else:
            assert as_citizen.status_code == 200, (method, template)
        assert no_login.status_code == anonymous and bad_token.status_code == 401, (method, template)
        if "{ulpin}" in template:
            denied = anon_client.request(method, template.replace("{ulpin}", other), headers=auth("citizen_a"), json=body)
            assert denied.status_code == 404, (method, template)                     # not theirs: the same 404 as a plot that does not exist
            missing = anon_client.request(method, template.replace("{ulpin}", "MH999900000099"), headers=auth("citizen_a"), json=body)
            assert missing.status_code == 404 and missing.json()["detail"].replace("MH999900000099", "X") == denied.json()["detail"].replace(other, "X")


def test_list_endpoints_only_ever_return_a_citizens_own_plots(anon_client, auth, users, conn, truth):
    own = set(users["citizen_a"]["plots"])
    alert_plot = sorted(u for u, t in truth["conflicts"].items() if "unrecorded_construction" in t)[0]
    conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (users["citizen_a"]["username"], alert_plot))
    try:
        for path in ("/plots", "/plots?village=Hinjewadi", "/plots?band=red", "/plots?conflict_type=boundary_overlap", "/construction-alerts"):
            r = anon_client.get(path, headers=auth("citizen_a"))
            assert r.status_code == 200
            ids = {f["properties"]["ulpin"] for f in r.json()["features"]}
            assert ids <= own | {alert_plot}, path
            assert not set(ULPIN.findall(r.text)) - own - {alert_plot}, path
        assert {f["properties"]["ulpin"] for f in anon_client.get("/construction-alerts", headers=auth("citizen_a")).json()["features"]} == {alert_plot}
    finally:
        conn.execute("DELETE FROM user_plots WHERE username = %s AND ulpin = %s", (users["citizen_a"]["username"], alert_plot))


def test_a_citizens_own_plot_responses_never_name_another_plot(anon_client, auth, users):
    own = users["citizen_a"]["plots"][0]                                  # a plot that overlaps another plot
    for r in (anon_client.get(f"/plots/{own}", headers=auth("citizen_a")), anon_client.post(f"/plots/{own}/explain", headers=auth("citizen_a"), json={})):
        assert r.status_code == 200 and set(ULPIN.findall(r.text)) <= set(users["citizen_a"]["plots"])
    _pages, text = pdf_text(anon_client.get(f"/plots/{own}/passport.pdf", headers=auth("citizen_a")).content)
    assert set(ULPIN.findall(text)) <= set(users["citizen_a"]["plots"])


def test_odd_ways_of_asking_for_someone_elses_plot_do_not_work(anon_client, auth, users):
    other = other_plot(users)
    for path in (f"/plots/{other.lower()}", f"/plots/{other}%20", f"/plots/{other}/", f"/plots//{other}", f"/plots/{other}.pdf", f"/plots/{other}?ulpin={users['citizen_a']['plots'][0]}"):
        r = anon_client.get(path, headers=auth("citizen_a"))
        assert r.status_code in (404, 422, 307), path
        assert "properties" not in r.text and "findings" not in r.text and "owner" not in r.text.lower(), path   # no plot data came back


# ====================================================================== C1. the friendly /verify page (same URL, the Accept header decides)

@pytest.mark.parametrize("accept,html", [
    (BROWSER_ACCEPT, True), ("text/html", True), ("TEXT/HTML; charset=utf-8", True), ("text/html;q=0.9, application/json", True),
    (None, False), ("*/*", False), ("application/json", False), ("application/json, text/html", False), ("", False), ("image/png", False),
])
def test_wants_html_only_for_browsers(accept, html):
    assert verify_page.wants_html(accept) is html


@pytest.fixture
def issued(anon_client, auth):
    r = issue_pdf(anon_client, auth)
    return r.headers["x-document-id"]


def test_a_browser_gets_a_friendly_page_and_a_program_still_gets_json(anon_client, issued):
    page = anon_client.get(f"/verify/{issued}", headers={"Accept": BROWSER_ACCEPT})
    assert page.status_code == 200 and page.headers["content-type"].startswith("text/html")
    assert "MATCHES" in page.text and PLOT in page.text and issued in page.text and "LandStack" in page.text
    for accept in (None, "*/*", "application/json"):
        headers = {"Accept": accept} if accept else {}
        j = anon_client.get(f"/verify/{issued}", headers=headers)
        assert j.headers["content-type"].startswith("application/json")
        assert j.json()["valid"] is True and j.json()["ulpin"] == PLOT and set(j.json()) == {"valid", "ulpin", "issued_at", "status"}


def test_the_page_is_safe_no_scripts_no_external_loads_strict_headers_no_personal_data(anon_client, issued, conn):
    page = anon_client.get(f"/verify/{issued}", headers={"Accept": BROWSER_ACCEPT})
    body = page.text.lower()
    assert "<script" not in body and "http://" not in body and "https://" not in body and "<img" not in body and "<iframe" not in body
    assert "onclick" not in body and "javascript:" not in body
    csp = page.headers["content-security-policy"]
    assert "default-src 'none'" in csp and "script-src" not in csp and "frame-ancestors 'none'" in csp
    assert page.headers["x-content-type-options"] == "nosniff" and page.headers["cache-control"] == "no-store"
    assert page.headers["referrer-policy"] == "no-referrer" and 'name="robots"' in body
    owners = [o for (o,) in conn.execute("SELECT owner_name FROM ror_records WHERE ulpin = %s UNION SELECT owner_name FROM registrations WHERE ulpin = %s", (PLOT, PLOT))]
    assert owners and not any(o.lower() in body for o in owners)                    # no names
    assert "overlap" not in body and "red band" not in body and "100" not in re.sub(r"[a-z0-9-]{4}-[a-z0-9-]{4}-[a-z0-9-]{4}|mh\d+", "", body)   # no evidence, no score


def test_a_changed_record_shows_the_changed_page(anon_client, issued, conn):
    conn.execute("UPDATE ror_records SET recorded_area_sqm = recorded_area_sqm + 1 WHERE ulpin = %s", (PLOT,))
    try:
        page = anon_client.get(f"/verify/{issued}", headers={"Accept": "text/html"})
        assert page.status_code == 200 and "HAS CHANGED" in page.text and "Do not rely" in page.text and "MATCHES" not in page.text
        assert anon_client.get(f"/verify/{issued}").json()["status"] == main.CHANGED
    finally:
        conn.execute("UPDATE ror_records SET recorded_area_sqm = recorded_area_sqm - 1 WHERE ulpin = %s", (PLOT,))
    assert "MATCHES" in anon_client.get(f"/verify/{issued}", headers={"Accept": "text/html"}).text


def test_an_unknown_document_is_a_friendly_404_for_browsers_and_json_for_programs(anon_client):
    page = anon_client.get("/verify/AAAA-BBBB-CCCC", headers={"Accept": BROWSER_ACCEPT})
    assert page.status_code == 404 and page.headers["content-type"].startswith("text/html") and "NOT FOUND" in page.text
    assert "AAAA-BBBB-CCCC" not in page.text                                  # the id is not echoed back at all
    j = anon_client.get("/verify/AAAA-BBBB-CCCC")
    assert j.status_code == 404 and j.json() == {"detail": "No document found with that id"}


def test_every_value_in_the_page_is_html_escaped():
    html = verify_page.found_page('<b>"x"</b>', "<script>alert(1)</script>", datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc), True)
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html and "<b>" not in html
    assert "2026-11-11 12:00 UTC" in html


def test_the_page_is_subject_to_the_same_strict_rate_limit(anon_client, issued, monkeypatch):
    monkeypatch.setattr(config, "RATE_VERIFY", "2/minute")
    codes = [anon_client.get(f"/verify/{issued}", headers={"Accept": "text/html"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


# ====================================================================== C2. the "capped at 100" flag (shown, never part of the tamper-evidence hash)

@pytest.mark.parametrize("points,capped", [([], False), ([40, 30, 25], False), ([40, 30, 30], False), ([40, 30, 30, 1], True), ([40, 30, 25, 20], True), ([100], False), ([101], True)])
def test_is_capped_means_more_than_100_exactly_100_is_not_capped(points, capped):
    assert passport.is_capped([{"points": p} for p in points]) is capped


def capped_plots(truth):
    return sorted(u for u, t in truth["conflicts"].items() if sum(config.POINTS[x] for x in t) > config.SCORE_CAP)


def test_the_passport_says_whether_the_score_was_capped(anon_client, auth, truth):
    capped = capped_plots(truth)
    assert len(capped) == 2
    for u in capped:
        body = anon_client.get(f"/plots/{u}", headers=auth("officer")).json()
        assert body["capped"] is True and body["score"] == 100 and sum(f["points"] for f in body["findings"]) > 100
    for u in sorted(truth["conflicts"])[:30]:
        if u not in capped:
            body = anon_client.get(f"/plots/{u}", headers=auth("officer")).json()
            assert body["capped"] is False and sum(f["points"] for f in body["findings"]) <= 100
    clean = next(f["properties"]["ulpin"] for f in anon_client.get("/plots?band=green", headers=auth("officer")).json()["features"] if f["properties"]["score"] == 0)
    assert anon_client.get(f"/plots/{clean}", headers=auth("officer")).json()["capped"] is False


def test_the_flag_is_not_part_of_what_is_hashed_so_old_passports_still_verify(conn, anon_client, issued):
    full = passport.load_passport(conn, PLOT)
    assert "capped" not in full and "unusual" not in full
    assert anon_client.get(f"/verify/{issued}").json()["valid"] is True


def test_the_pdf_shows_the_cap_note_only_when_the_score_was_capped(anon_client, auth, truth):
    capped_u = capped_plots(truth)[0]
    total = sum(config.POINTS[t] for t in truth["conflicts"][capped_u])
    pages, text = pdf_text(anon_client.get(f"/plots/{capped_u}/passport.pdf", headers=auth("officer")).content)
    assert pages == 1 and f"Capped at 100: findings add up to {total}" in text
    plain = sorted(u for u, t in truth["conflicts"].items() if u not in capped_plots(truth))[0]
    assert "Capped at" not in pdf_text(anon_client.get(f"/plots/{plain}/passport.pdf", headers=auth("officer")).content)[1]


def test_the_pdf_builder_works_out_the_cap_itself_when_the_flag_is_missing(conn):
    from backend.app import pdf
    full = passport.load_passport(conn, PLOT)                                   # no "capped" key at all
    make = lambda p: pdf.build_passport_pdf(p, doc_id="ABCD-EFGH-JKLM", issued_at=datetime(2026, 11, 11, tzinfo=timezone.utc),  # noqa: E731
                                            issued_to="admin", issued_role="admin", url="http://localhost:8000/verify/ABCD-EFGH-JKLM")
    assert "Capped at 100: findings add up to 110" in pdf_text(make(full))[1]
    exactly = dict(full, findings=[{"type": "tax_overdue", "points": 100, "evidence": "x"}], score=100)
    assert "Capped at" not in pdf_text(make(exactly))[1]                        # exactly 100 is not capped


def test_a_citizen_also_sees_the_flag_and_the_note_on_their_own_capped_plot(anon_client, auth, users, conn, truth):
    u = capped_plots(truth)[0]
    conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (users["citizen_a"]["username"], u))
    try:
        assert anon_client.get(f"/plots/{u}", headers=auth("citizen_a")).json()["capped"] is True
        _p, text = pdf_text(anon_client.get(f"/plots/{u}/passport.pdf", headers=auth("citizen_a")).content)
        assert "Capped at 100" in text and set(ULPIN.findall(text)) <= {u}
    finally:
        conn.execute("DELETE FROM user_plots WHERE username = %s AND ulpin = %s", (users["citizen_a"]["username"], u))


def test_the_score_band_and_findings_are_exactly_what_the_checks_say(conn, anon_client, auth):
    """The flag only reports; it must never change a score or a band."""
    from backend.app import scoring
    results = scoring.run_all(conn)
    for u in (PLOT, "MH000100000009", "MH000200000021"):
        body = anon_client.get(f"/plots/{u}", headers=auth("admin")).json()
        assert (body["score"], body["band"]) == (results[u]["score"], results[u]["band"])
        assert [(f["type"], f["points"]) for f in body["findings"]] == [(f["type"], f["points"]) for f in results[u]["findings"]]


# ====================================================================== C3. the X-Document-Id header on the PDF response

def test_the_pdf_response_carries_the_document_id_that_is_printed_on_the_page(anon_client, auth, conn):
    r = issue_pdf(anon_client, auth)
    header = r.headers["x-document-id"]
    assert DOC_ID.fullmatch(header)
    _pages, text = pdf_text(r.content)
    assert header in text                                                       # the same id as on the paper and in its QR code
    assert conn.execute("SELECT ulpin, issued_to FROM passport_issues WHERE doc_id = %s", (header,)).fetchone() == (PLOT, "test_officer")
    assert anon_client.get(f"/verify/{header}").json()["valid"] is True
    assert issue_pdf(anon_client, auth).headers["x-document-id"] != header      # every download is its own document


def test_no_document_id_header_when_no_pdf_was_made(anon_client, auth, users, conn):
    before = conn.execute("SELECT count(*) FROM passport_issues").fetchone()[0]
    denied = anon_client.get(f"/plots/{other_plot(users)}/passport.pdf", headers=auth("citizen_a"))
    assert denied.status_code == 404 and "x-document-id" not in denied.headers
    assert anon_client.get("/plots/MH999900000099/passport.pdf", headers=auth("officer")).status_code == 404
    assert conn.execute("SELECT count(*) FROM passport_issues").fetchone()[0] == before


def test_a_browser_page_may_read_the_header(anon_client, auth):
    r = anon_client.get(f"/plots/{PLOT}/passport.pdf", headers={**auth("officer"), "Origin": "http://localhost:5173"})
    assert "x-document-id" in r.headers and "X-Document-Id" in r.headers["access-control-expose-headers"]
