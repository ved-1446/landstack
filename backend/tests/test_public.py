"""Phase 13a: the two public endpoints (/public/stats and /public/plot/{ulpin}).

They are open to everyone, so these tests check what they must NOT say (no personal data, no scores, no ids),
that they agree with the logged-in API, that they are rate limited per IP, and that a token changes nothing."""
import pytest

from backend.app import config, public

ALLOWED_PLOT_FIELDS = {"ulpin", "village", "band"}
ALLOWED_STATS_FIELDS = {"total_plots", "plots_per_band"}


@pytest.fixture(autouse=True)
def fresh_cache():
    public.clear_cache()
    yield
    public.clear_cache()


def officer_plots(client, auth):
    features = client.get("/plots", headers=auth("officer")).json()["features"]
    return {f["properties"]["ulpin"]: f["properties"] for f in features}


# ---------------------------------------------------------------- /public/stats

def test_stats_have_exactly_the_allowed_fields_and_match_the_staff_summary(anon_client, auth):
    body = anon_client.get("/public/stats").json()
    assert set(body) == ALLOWED_STATS_FIELDS
    assert set(body["plots_per_band"]) == {"green", "amber", "red"}
    staff = anon_client.get("/summary", headers=auth("officer")).json()
    assert body["total_plots"] == staff["total_plots"] == 100
    assert body["plots_per_band"] == staff["plots_per_band"]
    assert sum(body["plots_per_band"].values()) == body["total_plots"]


def test_stats_are_cached_for_about_a_minute(anon_client, monkeypatch):
    calls = []
    real = public.scored
    monkeypatch.setattr(public, "scored", lambda conn: calls.append(1) or real(conn))
    first = anon_client.get("/public/stats").json()
    second = anon_client.get("/public/stats").json()
    assert first == second and len(calls) == 1
    public.clear_cache()
    anon_client.get("/public/stats")
    assert len(calls) == 2


def test_stats_are_rate_limited_per_ip(anon_client, monkeypatch):
    monkeypatch.setattr(config, "RATE_PUBLIC_STATS", "2/minute")
    codes = [anon_client.get("/public/stats").status_code for _ in range(3)]
    assert codes == [200, 200, 429]


# ---------------------------------------------------------------- /public/plot/{ulpin}

def test_every_plot_answers_with_exactly_ulpin_village_and_band_matching_the_staff_list(anon_client, auth):
    staff = officer_plots(anon_client, auth)
    assert len(staff) == 100
    for ulpin, props in staff.items():
        body = anon_client.get(f"/public/plot/{ulpin}").json()
        assert set(body) == ALLOWED_PLOT_FIELDS
        assert body == {"ulpin": ulpin, "village": props["village"], "band": props["band"]}


def test_the_plot_answer_holds_no_personal_data_score_evidence_or_ids(anon_client, truth, conn):
    flagged = sorted(truth["conflicts"])[0]
    text = anon_client.get(f"/public/plot/{flagged}").text.lower()
    owners = [name for (name,) in conn.execute("SELECT owner_name FROM ror_records")] + \
             [name for (name,) in conn.execute("SELECT owner_name FROM registrations")]
    assert owners and not any(name.lower() in text for name in owners)
    surveys = [s for (s,) in conn.execute("SELECT survey_no FROM plots WHERE ulpin = %s", (flagged,))]
    assert not any(s.lower() in text for s in surveys)
    for word in ("score", "findings", "evidence", "survey", "owner", "geometry", "doc_id", "area", "points", "tax"):
        assert word not in text


@pytest.mark.parametrize("bad", ["MH000100000999", "ZZ999999999999", "mh000100000001", "MH0001000000011", "MH00010000001",
                                 "MH-00100000001", "%20MH000100000001", "MH000100000001%27--"])
def test_wrong_malformed_and_unknown_ids_all_get_the_same_generic_404(anon_client, bad):
    r = anon_client.get(f"/public/plot/{bad}")
    assert r.status_code == 404
    assert r.json() == {"detail": "No plot found"}


def test_the_404_for_a_valid_looking_unknown_id_equals_the_404_for_garbage(anon_client):
    a = anon_client.get("/public/plot/MH000100000999")
    b = anon_client.get("/public/plot/not-a-plot")
    assert (a.status_code, a.json(), a.headers["content-type"]) == (b.status_code, b.json(), b.headers["content-type"])


def test_the_plot_endpoint_has_its_own_strict_per_ip_limit(anon_client, monkeypatch):
    monkeypatch.setattr(config, "RATE_PUBLIC_PLOT", "3/minute")
    codes = [anon_client.get(f"/public/plot/MH0001000000{n:02d}").status_code for n in (1, 2, 3, 4)]
    assert codes == [200, 200, 200, 429]                       # one counter for the endpoint, not one per id
    assert anon_client.get("/public/plot/MH000100000001").headers.get("Retry-After")


def test_the_default_limit_is_20_a_minute_for_plots():
    import re                                                  # the tests relax the live value, so read the real default from the file
    source = open(config.__file__, encoding="utf-8").read()
    assert re.search(r'^RATE_PUBLIC_PLOT = "20/minute"', source, re.M)


# ---------------------------------------------------------------- tokens change nothing; no AI

def test_a_citizen_or_officer_token_gets_exactly_the_same_answers(anon_client, auth, users):
    foreign = next(u for u in officer_plots(anon_client, auth) if u not in users["citizen_a"]["plots"])  # not citizen A's
    anonymous = anon_client.get(f"/public/plot/{foreign}").json()
    stats = anon_client.get("/public/stats").json()
    for who in ("citizen_a", "officer", "admin"):
        public.clear_cache()
        assert anon_client.get(f"/public/plot/{foreign}", headers=auth(who)).json() == anonymous
        assert anon_client.get("/public/stats", headers=auth(who)).json() == stats


def test_a_garbage_token_is_ignored_not_rejected(anon_client):
    assert anon_client.get("/public/stats", headers={"Authorization": "Bearer nonsense"}).status_code == 200


def test_the_public_endpoints_never_call_the_ai(anon_client, monkeypatch):
    from backend.app import llm
    monkeypatch.setattr(llm, "complete", lambda *a, **k: (_ for _ in ()).throw(AssertionError("the AI must not be called")))
    assert anon_client.get("/public/stats").status_code == 200
    assert anon_client.get("/public/plot/MH000100000001").status_code == 200
    assert anon_client.get("/public/plot/nope").status_code == 404


def test_the_public_router_does_not_import_the_ai_modules():
    source = open(public.__file__, encoding="utf-8").read()
    for name in ("llm", "explain", "translate", "guide"):
        assert f"import {name}" not in source and f"from .{name}" not in source


def test_calls_are_only_counted_not_logged_with_ids(anon_client):
    before = dict(public.COUNTS)
    anon_client.get("/public/plot/MH000100000001")
    anon_client.get("/public/plot/MH000100000998")
    assert public.COUNTS["plot_found"] == before["plot_found"] + 1
    assert public.COUNTS["plot_not_found"] == before["plot_not_found"] + 1


def test_the_api_docs_list_both_endpoints_without_a_login_requirement(anon_client):
    spec = anon_client.get("/openapi.json").json()["paths"]
    for path in ("/public/stats", "/public/plot/{ulpin}"):
        assert "security" not in spec[path]["get"]
