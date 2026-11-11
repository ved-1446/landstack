"""API tests on the live database (skipped if it is down), using FastAPI's TestClient."""
import pytest
from fastapi.testclient import TestClient

from backend.app import config, scoring
from backend.app.main import app


@pytest.fixture(scope="module")
def client(conn, auth):  # `conn` loads the live database with the seeded data first
    """Logged in as an officer (who may see everything), so the Phase 3 tests still test the same things."""
    c = TestClient(app)
    c.headers.update(auth("officer"))
    return c


@pytest.fixture(scope="module")
def results(conn):
    return scoring.run_all(conn)


def first(truth, ctype):
    return sorted(u for u, t in truth["conflicts"].items() if t == [ctype])[0]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok"}


def test_plots_returns_all_features_with_valid_geometry(client, truth):
    body = client.get("/plots").json()
    assert body["type"] == "FeatureCollection"
    feats = body["features"]
    assert len(feats) == truth["plots"] == 100
    for f in feats:
        assert f["type"] == "Feature"
        ring = f["geometry"]["coordinates"][0]
        assert f["geometry"]["type"] == "Polygon"
        assert len(ring) >= 4 and ring[0] == ring[-1]
        assert all(70 < lon < 77 and 17 < lat < 20 for lon, lat in ring)  # near Pune
        p = f["properties"]
        assert 0 <= p["score"] <= 100
        assert p["band"] == scoring.band_for(p["score"])
        assert {"ulpin", "village", "land_use", "survey_no"} <= p.keys()


def test_plots_filter_by_band(client, results):
    for band in ("green", "amber", "red"):
        feats = client.get("/plots", params={"band": band}).json()["features"]
        expected = {u for u, r in results.items() if r["band"] == band}
        assert {f["properties"]["ulpin"] for f in feats} == expected
        assert all(f["properties"]["band"] == band for f in feats)
    assert len(client.get("/plots", params={"band": "amber"}).json()["features"]) < 100


def test_plots_filter_by_village(client):
    feats = client.get("/plots", params={"village": "Wagholi"}).json()["features"]
    assert 0 < len(feats) < 100
    assert {f["properties"]["village"] for f in feats} == {"Wagholi"}
    assert client.get("/plots", params={"village": "Nowhere"}).json()["features"] == []


def test_plots_filter_by_conflict_type(client, truth):
    for ctype in config.POINTS:
        feats = client.get("/plots", params={"conflict_type": ctype}).json()["features"]
        expected = {u for u, t in truth["conflicts"].items() if ctype in t}
        assert {f["properties"]["ulpin"] for f in feats} == expected


def test_plots_filters_combine(client, truth):
    feats = client.get("/plots", params={"conflict_type": "boundary_overlap",
                                         "band": "green"}).json()["features"]
    assert feats == []  # an overlap is 40 points, so never green


def test_plots_bad_filter_values_are_422(client):
    assert client.get("/plots", params={"band": "purple"}).status_code == 422
    assert client.get("/plots", params={"conflict_type": "nope"}).status_code == 422


def test_passport_clean_plot(client, truth):
    decoys = {d["ulpin"] for d in truth["decoys"]}
    clean = sorted(u for u in (p["properties"]["ulpin"] for p in
                               client.get("/plots").json()["features"])
                   if u not in truth["conflicts"] and u not in decoys)[0]
    body = client.get(f"/plots/{clean}").json()
    assert body["score"] == 0 and body["band"] == "green" and body["findings"] == []
    assert body["ror"] and body["registration"] and body["tax"]
    assert body["ror"]["owner_name"] == body["registration"]["owner_name"]
    assert 1000 < body["area_sqm"] < 3000
    assert body["geometry"]["type"] == "Polygon"



def test_passport_overlap_plot_names_the_partner(client, truth):
    ulpin = first(truth, "boundary_overlap")                    # a plot whose only problem is an overlap
    partner = truth["details"][ulpin]["overlap_partner"]
    body = client.get(f"/plots/{ulpin}").json()
    assert body["score"] == 40 and body["band"] == "amber"
    assert [f["type"] for f in body["findings"]] == ["boundary_overlap"]
    assert body["findings"][0]["points"] == 40
    assert partner in body["findings"][0]["evidence"]



def test_passport_missing_record_is_null(client, truth):
    key = {"ror_records": "ror", "registrations": "registration", "tax_records": "tax"}
    seen = set()
    planted = [u for u, types in truth["conflicts"].items() if "missing_record" in types]   # alone or with other problems
    assert len(planted) == 4
    for ulpin in planted:
        body = client.get(f"/plots/{ulpin}").json()
        missing = key[truth["details"][ulpin]["missing_table"]]
        seen.add(missing)
        assert body[missing] is None
        assert all(body[k] is not None for k in key.values() if k != missing)
        assert "missing_record" in [f["type"] for f in body["findings"]]
        assert body["score"] == min(sum(config.POINTS[t] for t in truth["conflicts"][ulpin]), config.SCORE_CAP)
    assert seen == {"ror", "registration", "tax"}


def test_passport_invalid_shape_has_no_area(client, truth):
    body = client.get(f"/plots/{first(truth, 'invalid_boundary')}").json()
    assert body["area_sqm"] is None
    assert body["findings"][0]["type"] == "invalid_boundary"


def test_unknown_ulpin_is_404_with_clear_message(client):
    r = client.get("/plots/MH999999999999")
    assert r.status_code == 404
    assert r.json() == {"detail": "No plot found with ulpin MH999999999999"}


@pytest.mark.parametrize("bad", ["MH0001", "mh000100000001", "MH00010000000!", "MH0001000000012"])
def test_malformed_ulpin_is_422(client, bad):
    r = client.get(f"/plots/{bad}")
    assert r.status_code == 422
    assert "detail" in r.json()



def test_summary_matches_engine_and_truth(client, truth, results):
    body = client.get("/summary").json()
    assert body["total_plots"] == truth["plots"]
    # same numbers the Phase 2 summary command prints (it uses scoring.run_all too)
    for band in ("green", "amber", "red"):
        assert body["plots_per_band"][band] == sum(r["band"] == band for r in results.values())
    assert sum(body["plots_per_band"].values()) == truth["plots"]
    # and the planted truth (every plot has at most one finding per type, so findings = plots per type)
    for ctype in config.POINTS:
        planted = sum(ctype in t for t in truth["conflicts"].values())
        assert body["findings_per_type"][ctype] == planted
    # the demo mix, worked out from the truth file alone (points added and capped, then banded)
    def band(score):
        return "red" if score >= config.RED_FROM else "amber" if score >= config.AMBER_FROM else "green"
    ulpins = [f["properties"]["ulpin"] for f in client.get("/plots").json()["features"]]
    scores = [min(sum(config.POINTS[t] for t in truth["conflicts"].get(u, [])), config.SCORE_CAP) for u in ulpins]
    assert body["plots_per_band"] == {b: sum(band(s) == b for s in scores) for b in ("green", "amber", "red")}
    assert body["plots_per_band"] == {"green": 58, "amber": 29, "red": 13}      # was 60 / 28 / 12 before Phase 10


def test_conflict_types(client):
    body = client.get("/conflict-types").json()
    assert [t["type"] for t in body] == list(config.POINTS)
    for t in body:
        assert t["points"] == config.POINTS[t["type"]]
        assert len(t["description"]) > 10


def test_cors_allows_only_the_vite_dev_server(client):
    ok = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_openapi_lists_every_endpoint(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(paths) == {"/health", "/plots", "/plots/{ulpin}", "/summary", "/conflict-types",
                          "/auth/login", "/auth/me", "/audit",
                          "/plots/{ulpin}/passport.pdf", "/verify/{doc_id}",
                          "/construction-alerts",       # Phase 10 (SIMULATED footprints for the map)
                          "/plots/{ulpin}/explain", "/guide/ask",      # Phase 11 (the AI explainer and the Land Guide)
                          "/public/stats", "/public/plot/{ulpin}",      # Phase 13a (public counts, and village + band of one plot)
                          "/me/activity", "/conflicts", "/zones"}      # Phase 13b (own activity; staff-only conflict list and zones)


def test_database_down_returns_clean_json(monkeypatch):
    from backend.app import db
    import psycopg

    def boom():
        raise psycopg.OperationalError("connection refused: secret details")
    monkeypatch.setattr(db, "connect", boom)
    r = TestClient(app).get("/health")
    assert r.status_code == 503
    assert r.json() == {"detail": "Database unavailable"}
