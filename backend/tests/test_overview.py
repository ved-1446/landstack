"""Phase 13b: /me/activity, /conflicts, /zones and the area on /plots. Role access, no personal data, agreement with the engine."""
import re

import pytest

from backend.app import audit, config

ULPIN = re.compile(r"\b[A-Z]{2}\d{12}\b")


def clear(conn, *names):
    conn.execute("DELETE FROM audit_log WHERE username = ANY(%s::text[])", (list(names),))


# ---------------------------------------------------------------- area on /plots

def test_plots_carry_the_area_in_square_metres_and_it_matches_the_passport(anon_client, auth):
    features = anon_client.get("/plots", headers=auth("officer")).json()["features"]
    assert len(features) == 100
    areas = {f["properties"]["ulpin"]: f["properties"]["area_sqm"] for f in features}
    assert sum(a is not None for a in areas.values()) >= 90 and all(a > 0 for a in areas.values() if a is not None)
    for ulpin in sorted(areas)[:5]:
        assert anon_client.get(f"/plots/{ulpin}", headers=auth("officer")).json()["area_sqm"] == pytest.approx(areas[ulpin])


def test_a_citizen_gets_the_area_of_their_own_plots_only(anon_client, auth, users):
    features = anon_client.get("/plots", headers=auth("citizen_a")).json()["features"]
    assert {f["properties"]["ulpin"] for f in features} == set(users["citizen_a"]["plots"])
    assert all("area_sqm" in f["properties"] for f in features)


# ---------------------------------------------------------------- /me/activity

def test_activity_shows_only_my_own_rows_newest_first_without_username_or_role(anon_client, auth, users, conn):
    a, b = users["citizen_a"], users["citizen_b"]
    clear(conn, "test_citizen_a", "test_citizen_b", "test_officer")
    anon_client.get(f"/plots/{a['plots'][0]}", headers=auth("citizen_a"))
    anon_client.get(f"/plots/{a['plots'][1]}", headers=auth("citizen_a"))
    anon_client.get(f"/plots/{b['plots'][0]}", headers=auth("citizen_b"))
    anon_client.get(f"/plots/{a['plots'][2]}", headers=auth("officer"))
    mine = anon_client.get("/me/activity", headers=auth("citizen_a")).json()
    assert [(e["action"], e["ulpin"]) for e in mine] == [("view_passport", a["plots"][1]), ("view_passport", a["plots"][0])]
    assert all(set(e) == {"id", "action", "ulpin", "looked_at"} for e in mine)
    theirs = anon_client.get("/me/activity", headers=auth("citizen_b")).json()
    assert [e["ulpin"] for e in theirs] == [b["plots"][0]]
    assert [e["ulpin"] for e in anon_client.get("/me/activity", headers=auth("officer")).json()] == [a["plots"][2]]


def test_a_refused_request_does_not_show_back_the_plot_id_that_was_typed(anon_client, auth, users, conn):
    a, b = users["citizen_a"], users["citizen_b"]
    clear(conn, "test_citizen_a")
    anon_client.get(f"/plots/{b['plots'][0]}", headers=auth("citizen_a"))          # not theirs: audited as denied
    anon_client.get("/plots/MH999900000099", headers=auth("citizen_a"))            # does not exist
    rows = anon_client.get("/me/activity", headers=auth("citizen_a")).json()
    assert [r["action"] for r in rows] == [audit.DENIED, audit.DENIED]       # for a citizen a missing plot is audited exactly like one that is not theirs
    assert all(r["ulpin"] is None for r in rows)
    assert b["plots"][0] not in str(rows)
    clear(conn, "test_officer")
    anon_client.get("/plots/MH999900000099", headers=auth("officer"))              # staff: a plot that does not exist
    rows = anon_client.get("/me/activity", headers=auth("officer")).json()
    assert [(r["action"], r["ulpin"]) for r in rows] == [(audit.NOT_FOUND, None)]


def test_activity_needs_a_login_and_validates_the_limit(anon_client, auth):
    assert anon_client.get("/me/activity").status_code == 401
    assert anon_client.get("/me/activity", headers=auth("officer"), params={"limit": 0}).status_code == 422
    assert anon_client.get("/me/activity", headers=auth("officer"), params={"limit": 201}).status_code == 422
    assert len(anon_client.get("/me/activity", headers=auth("admin"), params={"limit": 1}).json()) <= 1


# ---------------------------------------------------------------- /conflicts

def test_conflicts_are_for_staff_only(anon_client, auth):
    assert anon_client.get("/conflicts").status_code == 401
    assert anon_client.get("/conflicts", headers=auth("citizen_a")).status_code == 403
    for who in ("officer", "admin"):
        assert anon_client.get("/conflicts", headers=auth(who)).status_code == 200


def test_conflicts_agree_with_the_engine_the_plots_list_and_the_planted_truth(anon_client, auth, truth):
    rows = anon_client.get("/conflicts", headers=auth("officer")).json()
    plots = {f["properties"]["ulpin"]: f["properties"] for f in anon_client.get("/plots", headers=auth("officer")).json()["features"]}
    assert [r["score"] for r in rows] == sorted((r["score"] for r in rows), reverse=True)
    for r in rows:
        assert set(r) == {"ulpin", "village", "score", "band", "findings"} and r["findings"]
        assert (r["score"], r["band"], r["village"]) == (plots[r["ulpin"]]["score"], plots[r["ulpin"]]["band"], plots[r["ulpin"]]["village"])
        assert all(set(f) == {"type", "points", "simulated"} and f["points"] == config.POINTS[f["type"]] for f in r["findings"])
    by_plot = {r["ulpin"]: {f["type"] for f in r["findings"]} for r in rows}
    for ulpin, types in truth["conflicts"].items():          # every planted problem is listed, with exactly the planted types
        assert by_plot.get(ulpin) == set(types), ulpin
    assert not {u for u in by_plot} - set(truth["conflicts"])  # and nothing else is listed


def test_only_the_construction_finding_is_marked_simulated(anon_client, auth):
    for r in anon_client.get("/conflicts", headers=auth("officer")).json():
        for f in r["findings"]:
            assert f["simulated"] == (f["type"] == "unrecorded_construction")


def test_conflicts_hold_no_evidence_text_names_survey_numbers_or_other_plot_ids(anon_client, auth, conn):
    text = anon_client.get("/conflicts", headers=auth("officer")).text
    rows = anon_client.get("/conflicts", headers=auth("officer")).json()
    own_ids = {r["ulpin"] for r in rows}
    assert set(ULPIN.findall(text)) == own_ids               # the only ids are the rows' own ids
    owners = [n for (n,) in conn.execute("SELECT owner_name FROM ror_records")] + [n for (n,) in conn.execute("SELECT owner_name FROM registrations")]
    assert owners and not any(n in text for n in owners)
    surveys = {s for (s,) in conn.execute("SELECT survey_no FROM plots")}
    assert not any(f'"{s}"' in text for s in surveys)
    for word in ("evidence", "overlaps", "sq m", "record says", "registration owner"):      # (type names like owner_mismatch and duplicate_survey_no are allowed; names and survey NUMBERS were checked above)
        assert word not in text


# ---------------------------------------------------------------- /zones

def test_zones_are_for_staff_only(anon_client, auth):
    assert anon_client.get("/zones").status_code == 401
    assert anon_client.get("/zones", headers=auth("citizen_a")).status_code == 403
    assert anon_client.get("/zones", headers=auth("officer")).status_code == 200


def test_zones_have_a_type_an_area_a_plot_count_and_an_outline_and_nothing_personal(anon_client, auth, conn):
    r = anon_client.get("/zones", headers=auth("officer"))
    rows = r.json()
    (n,) = conn.execute("SELECT count(*) FROM zones").fetchone()
    assert len(rows) == n > 0
    for z in rows:
        assert set(z) == {"id", "zone_type", "area_sqm", "plots_touching", "geometry"}
        assert z["area_sqm"] > 0 and isinstance(z["plots_touching"], int) and z["plots_touching"] >= 0
        assert z["geometry"]["type"] in ("Polygon", "MultiPolygon")
    assert not ULPIN.findall(r.text)
    assert {z["zone_type"] for z in rows} == {t for (t,) in conn.execute("SELECT DISTINCT zone_type FROM zones")}
    assert sum(z["plots_touching"] for z in rows) > 0
