"""Phase 10: the unrecorded-construction alert. EVERYTHING ABOUT IT IS SIMULATED (two generated building snapshots,
T0 and T1; no real imagery). The check flags new built area, the score adds a fixed 15, and nothing here is a model."""
import io
import math
import re

import pytest
from pypdf import PdfReader

from backend.app import checks, config, db as appdb, scoring
from backend.app.passport import hide_other_plots  # noqa: F401  (the redaction rule is re-tested through the API below)
import seed

CONSTRUCTION = "unrecorded_construction"
ULPIN_IN_TEXT = re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{14}\b")


def planted_alerts(truth):
    return {u for u, types in truth["conflicts"].items() if CONSTRUCTION in types}


# ------------------------------------------------------------------ the demo data (live database)

def test_the_check_flags_exactly_the_planted_alerts(conn, truth):
    found = checks.check_unrecorded_construction(conn)
    assert {f["ulpin"] for f in found} == planted_alerts(truth)           # no misses, no extras
    assert len(found) == len(planted_alerts(truth)) == 10                 # at most one finding per plot
    for f in found:
        assert f["type"] == CONSTRUCTION and f["points"] == config.CONSTRUCTION_ALERT_POINTS == 15


def test_none_of_the_jitter_plots_is_flagged_and_they_really_did_change(conn, truth):
    decoys = truth["construction_decoys"]
    assert len(decoys) == 8 and {d["kind"] for d in decoys} == {"shift", "edge_noise"}
    flagged = {f["ulpin"] for f in checks.check_unrecorded_construction(conn)}
    for d in decoys:
        assert d["ulpin"] not in flagged
        # the test is only meaningful if T1 really differs from T0 for them: some "new" ground, but under the threshold
        (new_sqm,) = conn.execute(
            """
            SELECT ST_Area(ST_Difference(
                       (SELECT ST_Union(footprint) FROM building_snapshots WHERE ulpin = %(u)s AND snapshot = 'T1'),
                       (SELECT ST_Union(footprint) FROM building_snapshots WHERE ulpin = %(u)s AND snapshot = 'T0'))::geography)
            """, {"u": d["ulpin"]}).fetchone()
        assert 0 < new_sqm < config.MIN_NEW_BUILT_SQM
        assert new_sqm < 0.85 * config.MIN_NEW_BUILT_SQM                  # a clear margin, not a near miss
    assert not {d["ulpin"] for d in decoys} & planted_alerts(truth)


def test_the_planted_sizes_are_clearly_above_the_threshold_and_the_evidence_has_real_numbers(conn, truth):
    found = {f["ulpin"]: f for f in checks.check_unrecorded_construction(conn)}
    for u, f in found.items():
        planted = truth["details"][u]["new_built_sqm"]
        assert planted >= 1.3 * config.MIN_NEW_BUILT_SQM
        said = float(re.search(r"about ([\d,]+) sq m", f["evidence"]).group(1).replace(",", ""))
        assert abs(said - planted) <= 1.5                                 # same number, up to rounding and the geography cast
        assert f["evidence"].startswith("SIMULATED: about ")
        assert "new building appeared between T0 and T1 that is not in the records" in f["evidence"]


def test_the_alerts_mix_plots_that_were_clean_with_plots_that_already_had_problems(truth):
    alerts = planted_alerts(truth)
    had_problem = {u for u in alerts if set(truth["conflicts"][u]) - {CONSTRUCTION}}
    assert len(alerts) == 10 and len(had_problem) == 5 and len(alerts - had_problem) == 5


def test_every_valid_plot_has_buildings_in_both_snapshots_and_they_lie_inside_the_plot(conn):
    rows = conn.execute(
        """
        SELECT p.ulpin,
               count(*) FILTER (WHERE b.snapshot = 'T0') AS t0, count(*) FILTER (WHERE b.snapshot = 'T1') AS t1,
               bool_and(ST_Covers(p.geom, b.footprint)) AS inside
        FROM plots p JOIN building_snapshots b USING (ulpin)
        WHERE ST_IsValid(p.geom) GROUP BY p.ulpin
        """).fetchall()
    assert len(rows) == 96                                                # 100 plots minus the 4 invalid ones
    assert all(t0 >= 1 and t1 >= t0 and inside for _u, t0, t1, inside in rows)
    assert conn.execute("SELECT count(DISTINCT ulpin) FROM building_snapshots").fetchone() == (100,)


def test_the_check_is_visible_raw_sql_with_the_agreed_rules():
    import inspect
    # the SQL text is one shared constant (the map's footprints use the same text), next to the check that uses it
    source = inspect.getsource(checks.check_unrecorded_construction) + checks._NEW_BUILT_SQL
    assert "_NEW_BUILT_SQL" in inspect.getsource(checks.construction_footprints)
    for needed in ("ST_Difference", "ST_Union", "::geography", "ST_IsValid", "MIN_NEW_BUILT_SQM", "SIMULATED"):
        assert needed in source


# ------------------------------------------------------------------ edges, on temporary plots (always rolled back)
# BASE is about 42 m x 44 m, far from the seeded plots. Buildings are drawn in METRES from a corner of the plot.

BASE = (74.5000, 19.0000, 74.5004, 19.0004)
_PHI = math.radians(19.0)
_M_LAT = 111132.92 - 559.82 * math.cos(2 * _PHI) + 1.175 * math.cos(4 * _PHI)
_M_LON = 111412.84 * math.cos(_PHI) - 93.5 * math.cos(3 * _PHI)


def rect(x_m, y_m, w_m, h_m):
    """A rectangle w x h metres, its lower-left corner x_m, y_m metres from BASE's lower-left corner, as a lon/lat box."""
    x0, y0 = BASE[0] + x_m / _M_LON, BASE[1] + y_m / _M_LAT
    return (x0, y0, x0 + w_m / _M_LON, y0 + h_m / _M_LAT)


@pytest.fixture
def tx(conn):
    connection = appdb.connect()
    yield connection
    connection.rollback()
    connection.close()


def add_plot(connection, ulpin="TESTPLOTAAAA01", valid=True):
    if valid:
        connection.execute(
            "INSERT INTO plots (ulpin, geom, village, land_use, survey_no) "
            "VALUES (%s, ST_MakeEnvelope(%s, %s, %s, %s, 4326), 'Testville', 'residential', %s)", (ulpin, *BASE, ulpin))
    else:      # a bow-tie: the corners are visited in a crossing order
        x0, y0, x1, y1 = BASE
        connection.execute(
            "INSERT INTO plots (ulpin, geom, village, land_use, survey_no) VALUES "
            "(%s, ST_GeomFromText(%s, 4326), 'Testville', 'residential', %s)",
            (ulpin, f"POLYGON(({x0} {y0}, {x1} {y1}, {x1} {y0}, {x0} {y1}, {x0} {y0}))", ulpin))


def add_building(connection, ulpin, snapshot, box):
    connection.execute("INSERT INTO building_snapshots (ulpin, snapshot, footprint) "
                       "VALUES (%s, %s, ST_MakeEnvelope(%s, %s, %s, %s, 4326))", (ulpin, snapshot, *box))


def alert_for(connection, ulpin="TESTPLOTAAAA01"):
    return {f["ulpin"]: f for f in checks.check_unrecorded_construction(connection)}.get(ulpin)


OLD = rect(2, 2, 12, 10)                       # an old building, 120 sq m, in both snapshots in most tests


@pytest.mark.parametrize("new_sqm,flagged", [(29.0, False), (31.0, True)])
def test_the_threshold_edge_just_below_and_just_above(tx, new_sqm, flagged):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(25, 25, 5, new_sqm / 5))      # 5 m wide, so 29 or 31 sq m
    found = alert_for(tx)
    assert (found is not None) is flagged
    if found:
        assert "about 31 sq m" in found["evidence"] and found["points"] == 15
        assert f"limit is {config.MIN_NEW_BUILT_SQM:.0f} sq m" in found["evidence"]


def test_the_threshold_is_the_named_constant(tx, monkeypatch):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(25, 25, 5, 8))               # 40 sq m
    assert alert_for(tx) is not None
    monkeypatch.setattr(config, "MIN_NEW_BUILT_SQM", 50.0)
    assert alert_for(tx) is None


def test_a_building_that_is_in_both_snapshots_is_not_flagged(tx):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", OLD)
    assert alert_for(tx) is None


def test_a_building_removed_in_t1_is_not_flagged(tx):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T0", rect(25, 25, 8, 9))                # a second old building...
    add_building(tx, "TESTPLOTAAAA01", "T1", OLD)                               # ...gone in T1
    assert alert_for(tx) is None


def test_a_plot_with_no_buildings_in_t1_is_not_flagged(tx):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    assert alert_for(tx) is None


def test_a_building_shifted_by_survey_jitter_is_not_flagged(tx):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(2 + 1.8, 2, 12, 10))          # the same building, 1.8 m to the right
    assert alert_for(tx) is None
    (sliver,) = tx.execute(
        "SELECT ST_Area(ST_Difference((SELECT ST_Union(footprint) FROM building_snapshots WHERE snapshot = 'T1' "
        "AND ulpin = 'TESTPLOTAAAA01'), (SELECT ST_Union(footprint) FROM building_snapshots WHERE snapshot = 'T0' "
        "AND ulpin = 'TESTPLOTAAAA01'))::geography)").fetchone()
    assert 10 < sliver < 25                                                      # there IS a sliver; it is just too small to count


def test_a_new_building_with_no_t0_at_all_is_everything_new(tx):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(5, 5, 10, 8))                 # 80 sq m
    assert "about 80 sq m" in alert_for(tx)["evidence"]


def test_two_new_buildings_are_added_together(tx):
    add_plot(tx)
    add_building(tx, "TESTPLOTAAAA01", "T0", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", OLD)
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(20, 2, 4, 5))                 # 20 sq m: under the line on its own
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(20, 20, 4, 5))                # another 20: together 40
    assert "about 40 sq m" in alert_for(tx)["evidence"]


def test_an_invalid_shape_is_skipped(tx):
    add_plot(tx, valid=False)
    add_building(tx, "TESTPLOTAAAA01", "T1", rect(5, 5, 10, 8))                 # 80 sq m of "new" building
    assert tx.execute("SELECT ST_IsValid(geom) FROM plots WHERE ulpin = 'TESTPLOTAAAA01'").fetchone() == (False,)
    assert alert_for(tx) is None
    # the control: exactly the same buildings on a valid plot ARE flagged, so the skip is what made the difference
    tx.execute("DELETE FROM plots WHERE ulpin = 'TESTPLOTAAAA01'")
    add_plot(tx)
    assert alert_for(tx) is not None


# ------------------------------------------------------------------ scoring (+15, cap, band edges)

def fs(*types):
    return [{"ulpin": "X", "type": t, "points": config.POINTS[t], "evidence": "e"} for t in types]


def test_the_alert_adds_exactly_15_points():
    assert scoring.score_plot(fs(CONSTRUCTION))["score"] == 15
    assert scoring.score_plot(fs("tax_overdue", CONSTRUCTION))["score"] == 30
    assert config.POINTS[CONSTRUCTION] == config.CONSTRUCTION_ALERT_POINTS


def test_the_cap_at_100_still_holds_with_the_alert():
    r = scoring.score_plot(fs("boundary_overlap", "restricted_zone_clash", "area_mismatch", CONSTRUCTION))   # 40+30+25+15 = 110
    assert (r["score"], r["band"]) == (100, "red")
    assert sum(f["points"] for f in r["findings"]) == 110                       # the findings keep their real points


@pytest.mark.parametrize("types,score,band", [
    ([CONSTRUCTION], 15, "green"),
    (["missing_record", CONSTRUCTION], 25, "amber"),                            # 10 + 15: exactly on the amber edge
    (["boundary_overlap", CONSTRUCTION], 55, "amber"),
    (["area_mismatch", "duplicate_survey_no", CONSTRUCTION], 60, "red"),        # 25 + 20 + 15: exactly on the red edge
    (["owner_mismatch", "area_mismatch", "invalid_boundary"], 65, "red"),
])
def test_band_edges_with_the_alert(types, score, band):
    r = scoring.score_plot(fs(*types))
    assert (r["score"], r["band"]) == (score, band)


def test_every_planted_alert_plot_scores_its_sum_and_the_live_bands_are_right(conn, truth):
    results = scoring.run_all(conn)
    for u in planted_alerts(truth):
        assert CONSTRUCTION in {f["type"] for f in results[u]["findings"]}
        assert results[u]["score"] == min(sum(config.POINTS[t] for t in truth["conflicts"][u]), config.SCORE_CAP)
    for u, r in results.items():
        assert r["band"] == scoring.band_for(r["score"])


# ------------------------------------------------------------------ the API, the PDF and the redaction rules

def alert_only_plot(truth):
    return sorted(u for u, t in truth["conflicts"].items() if t == [CONSTRUCTION])[0]


def test_the_passport_shows_the_finding_with_the_simulated_wording(anon_client, auth, truth):
    u = alert_only_plot(truth)
    body = anon_client.get(f"/plots/{u}", headers=auth("officer")).json()
    (finding,) = body["findings"]
    assert finding["type"] == CONSTRUCTION and finding["points"] == 15
    assert finding["evidence"].startswith("SIMULATED: about ")
    assert (body["score"], body["band"]) == (15, "green")


def test_conflict_types_lists_it_with_the_simulated_marker(anon_client, auth):
    body = anon_client.get("/conflict-types", headers=auth("citizen_a")).json()
    assert [t["type"] for t in body] == list(config.POINTS) and len(body) == 9
    by_type = {t["type"]: t for t in body}
    assert by_type[CONSTRUCTION]["simulated"] is True and by_type[CONSTRUCTION]["points"] == 15
    assert "SIMULATED" in by_type[CONSTRUCTION]["description"]
    assert [t for t, v in by_type.items() if v["simulated"]] == [CONSTRUCTION]    # nothing else is simulated


def test_the_summary_and_the_plot_filter_know_the_new_type(anon_client, auth, truth):
    summary = anon_client.get("/summary", headers=auth("officer")).json()
    assert summary["findings_per_type"][CONSTRUCTION] == 10
    plots = anon_client.get("/plots", params={"conflict_type": CONSTRUCTION}, headers=auth("officer")).json()
    assert {f["properties"]["ulpin"] for f in plots["features"]} == planted_alerts(truth)


def test_an_unknown_conflict_type_is_still_refused(anon_client, auth):
    assert anon_client.get("/plots", params={"conflict_type": "made_up"}, headers=auth("officer")).status_code == 422


def test_a_citizen_sees_the_finding_on_their_own_plot_and_other_rules_still_hold(anon_client, auth, users, conn, truth):
    u = alert_only_plot(truth)
    other = users["citizen_b"]["plots"][0]
    conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (users["citizen_a"]["username"], u))
    try:
        body = anon_client.get(f"/plots/{u}", headers=auth("citizen_a")).json()
        assert body["findings"][0]["evidence"].startswith("SIMULATED:")
        assert not ULPIN_IN_TEXT.findall(body["findings"][0]["evidence"])         # it never names another plot
        assert anon_client.get(f"/plots/{u}", headers=auth("citizen_b")).status_code == 404   # still only the owner
        assert anon_client.get(f"/plots/{other}", headers=auth("citizen_a")).status_code == 404
        listed = anon_client.get("/plots", params={"conflict_type": CONSTRUCTION}, headers=auth("citizen_a")).json()
        assert {f["properties"]["ulpin"] for f in listed["features"]} == {u}      # a citizen's list is only their own plots
    finally:
        conn.execute("DELETE FROM user_plots WHERE username = %s AND ulpin = %s", (users["citizen_a"]["username"], u))


def test_the_pdf_findings_table_carries_the_simulated_text(anon_client, auth, truth):
    u = alert_only_plot(truth)
    r = anon_client.get(f"/plots/{u}/passport.pdf", headers=auth("officer"))
    assert r.status_code == 200
    reader = PdfReader(io.BytesIO(r.content))
    text = " ".join(reader.pages[0].extract_text().split())
    assert len(reader.pages) == 1
    assert "SIMULATED: about" in text and "new building appeared between T0 and T1" in text


def test_the_busiest_alert_plot_still_fits_on_one_page_with_the_text_in_it(anon_client, auth, truth):
    u = max(planted_alerts(truth), key=lambda x: len(truth["conflicts"][x]))
    r = anon_client.get(f"/plots/{u}/passport.pdf", headers=auth("officer"))
    reader = PdfReader(io.BytesIO(r.content))
    text = " ".join(reader.pages[0].extract_text().split())
    assert len(reader.pages) == 1 and "SIMULATED" in text and "more finding(s) not shown" not in text


def test_a_citizens_pdf_of_an_alert_plot_names_only_their_own_plot(anon_client, auth, users, conn, truth):
    u = alert_only_plot(truth)
    conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (users["citizen_a"]["username"], u))
    try:
        r = anon_client.get(f"/plots/{u}/passport.pdf", headers=auth("citizen_a"))
        assert r.status_code == 200
        text = PdfReader(io.BytesIO(r.content)).pages[0].extract_text()
        assert "SIMULATED" in text and set(ULPIN_IN_TEXT.findall(text)) <= {u}
    finally:
        conn.execute("DELETE FROM user_plots WHERE username = %s AND ulpin = %s", (users["citizen_a"]["username"], u))


def test_the_seed_never_changes_the_plots_or_records_when_buildings_are_added():
    with_buildings = seed.generate()
    without = seed.generate(construction=False)
    for table in ("plots", "ror_records", "registrations", "tax_records", "zones"):
        assert with_buildings["rows"][table] == without["rows"][table]
    earlier = {u: [t for t in types if t != CONSTRUCTION] for u, types in with_buildings["truth"]["conflicts"].items()}
    assert {u: t for u, t in earlier.items() if t} == without["truth"]["conflicts"]
    assert without["rows"]["building_snapshots"] == []


# ------------------------------------------------------------------ GET /construction-alerts (the map's footprints, SIMULATED)

def test_the_footprints_are_exactly_the_flagged_plots_and_say_simulated(anon_client, auth, truth):
    body = anon_client.get("/construction-alerts", headers=auth("officer")).json()
    assert body["type"] == "FeatureCollection"
    assert {f["properties"]["ulpin"] for f in body["features"]} == planted_alerts(truth)
    for f in body["features"]:
        assert f["geometry"]["type"] == "Polygon" and f["properties"]["simulated"] is True
        assert f["properties"]["piece_sqm"] <= f["properties"]["new_sqm"] + 0.01
        assert f["properties"]["new_sqm"] >= config.MIN_NEW_BUILT_SQM


def test_the_footprints_match_the_check_and_lie_inside_their_plot(anon_client, auth, conn):
    body = anon_client.get("/construction-alerts", headers=auth("admin")).json()
    said = {f["ulpin"]: float(re.search(r"about ([\d,]+) sq m", f["evidence"]).group(1).replace(",", ""))
            for f in checks.check_unrecorded_construction(conn)}
    for ulpin, claimed in said.items():
        pieces = [f["properties"]["piece_sqm"] for f in body["features"] if f["properties"]["ulpin"] == ulpin]
        assert abs(sum(pieces) - claimed) <= 1.0                                  # the map shows what the evidence says
    import json
    for f in body["features"]:
        (inside,) = conn.execute(
            "SELECT ST_Covers(geom, ST_GeomFromGeoJSON(%s)) FROM plots WHERE ulpin = %s",
            (json.dumps(f["geometry"]), f["properties"]["ulpin"])).fetchone()
        assert inside


def test_the_jitter_plots_have_no_footprint(anon_client, auth, truth):
    shown = {f["properties"]["ulpin"] for f in anon_client.get("/construction-alerts", headers=auth("officer")).json()["features"]}
    assert not shown & {d["ulpin"] for d in truth["construction_decoys"]}


def test_citizens_get_only_their_own_plots_footprints(anon_client, auth, users, conn, truth):
    u = alert_only_plot(truth)
    assert anon_client.get("/construction-alerts", headers=auth("citizen_a")).json()["features"] == []   # owns none of the alerts
    conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (users["citizen_a"]["username"], u))
    try:
        mine = anon_client.get("/construction-alerts", headers=auth("citizen_a")).json()["features"]
        assert {f["properties"]["ulpin"] for f in mine} == {u}
        assert anon_client.get("/construction-alerts", headers=auth("citizen_b")).json()["features"] == []
    finally:
        conn.execute("DELETE FROM user_plots WHERE username = %s AND ulpin = %s", (users["citizen_a"]["username"], u))


def test_the_footprints_need_a_login(anon_client):
    assert anon_client.get("/construction-alerts").status_code == 401
