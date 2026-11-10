"""Each check must flag exactly the plots planted_truth.json says: no misses, no extras."""
import re

import pytest

from backend.app import checks, config, db as appdb, scoring

CHECK_FUNCS = [
    ("boundary_overlap", checks.check_boundary_overlap),
    ("restricted_zone_clash", checks.check_restricted_zone_clash),
    ("area_mismatch", checks.check_area_mismatch),
    ("owner_mismatch", checks.check_owner_mismatch),
    ("duplicate_survey_no", checks.check_duplicate_survey_no),
    ("invalid_boundary", checks.check_invalid_boundary),
    ("tax_overdue", checks.check_tax_overdue),
    ("missing_record", checks.check_missing_record),
    ("unrecorded_construction", checks.check_unrecorded_construction),     # Phase 10 (SIMULATED)
]


def test_every_check_is_covered_by_the_planted_truth_test():
    assert [c for c, _ in CHECK_FUNCS] == list(checks.ALL_CHECKS)


def planted(truth, ctype):
    return {u for u, types in truth["conflicts"].items() if ctype in types}


@pytest.mark.parametrize("ctype,func", CHECK_FUNCS, ids=[c for c, _ in CHECK_FUNCS])
def test_check_matches_planted_truth(conn, truth, ctype, func):
    findings = func(conn)
    assert {f["ulpin"] for f in findings} == planted(truth, ctype)
    for f in findings:
        assert f["type"] == ctype
        assert f["points"] > 0 and f["evidence"]


def test_no_decoy_is_flagged_as_owner_mismatch(conn, truth):
    flagged = {f["ulpin"] for f in checks.check_owner_mismatch(conn)}
    decoys = {d["ulpin"] for d in truth["decoys"]}
    assert len(decoys) == 6
    assert not (flagged & decoys)


def test_plots_with_no_planted_problem_score_zero(conn, truth):      # renamed in Phase 10 (was test_clean_plots_score_zero)
    results = scoring.run_all(conn)
    clean = [u for u in results if u not in truth["conflicts"]]
    assert len(clean) == truth["plots"] - len(truth["conflicts"])
    for u in clean:
        assert results[u]["score"] == 0
        assert results[u]["band"] == "green"
        assert results[u]["findings"] == []


def test_planted_plots_score_above_zero(conn, truth):
    results = scoring.run_all(conn)
    for u in truth["conflicts"]:
        assert results[u]["score"] > 0


def test_overlap_evidence_names_the_partner_and_says_how(conn, truth):
    by_plot = {f["ulpin"]: f for f in checks.check_boundary_overlap(conn)}
    wording = {"overlaps": "overlaps plot ", "inside": "lies completely inside plot ", "contains": " lies completely inside this plot"}
    assert len(by_plot) == 14
    relations = set()
    for ulpin, d in truth["details"].items():
        if "overlap_partner" in d:
            assert d["overlap_partner"] in by_plot[ulpin]["evidence"]
            assert wording[d["overlap_relation"]] in by_plot[ulpin]["evidence"]
            relations.add(d["overlap_relation"])
    assert relations == {"overlaps", "inside", "contains"}          # all three kinds are in the demo data


def test_the_touching_pair_in_the_demo_data_is_not_flagged(conn, truth):
    ((a, b),) = truth["touching_pairs"]
    row = conn.execute(
        "SELECT ST_Intersects(x.geom, y.geom), ST_Overlaps(x.geom, y.geom), "
        "ST_Area(ST_Intersection(x.geom, y.geom)::geography) FROM plots x, plots y WHERE x.ulpin = %s AND y.ulpin = %s",
        (a, b)).fetchone()
    assert row[0] is True and row[1] is False and row[2] == 0          # they touch, they do not overlap, no shared ground
    flagged = {f["ulpin"] for f in checks.check_boundary_overlap(conn)}
    assert a not in flagged and b not in flagged
    assert {f["ulpin"] for f in checks.run_checks(conn)} .isdisjoint({a, b})   # no check flags them at all


def test_every_planted_plot_scores_the_sum_of_its_problems(conn, truth):
    results = scoring.run_all(conn)
    for ulpin, types in truth["conflicts"].items():
        assert {f["type"] for f in results[ulpin]["findings"]} == set(types)
        assert results[ulpin]["score"] == min(sum(config.POINTS[t] for t in types), config.SCORE_CAP)


def test_the_cap_at_100_is_really_reached(conn, truth):
    results = scoring.run_all(conn)
    capped = [u for u, t in truth["conflicts"].items() if sum(config.POINTS[x] for x in t) > config.SCORE_CAP]
    assert len(capped) == 2 and all(results[u]["score"] == 100 and results[u]["band"] == "red" for u in capped)
    bands = [r["band"] for r in results.values()]
    assert (bands.count("green"), bands.count("amber"), bands.count("red")) == (58, 29, 13)     # was 60/28/12 before Phase 10


# ---- the overlap rules, on temporary plots (a transaction that is always rolled back) ----
# BASE is about 42 m x 44 m, placed far from the seeded plots (which are near lon 73.8, lat 18.55).

BASE = (74.5000, 19.0000, 74.5004, 19.0004)


@pytest.fixture
def tx(conn):
    connection = appdb.connect()
    yield connection
    connection.rollback()
    connection.close()


def add_plot(connection, ulpin, box):
    connection.execute(
        "INSERT INTO plots (ulpin, geom, village, land_use, survey_no) "
        "VALUES (%s, ST_MakeEnvelope(%s, %s, %s, %s, 4326), 'Testville', 'residential', %s)", (ulpin, *box, ulpin))


def flagged(connection, *ulpins):
    return {f["ulpin"]: f["evidence"] for f in checks.check_boundary_overlap(connection) if f["ulpin"] in ulpins}


def two_plots(connection, other_box):
    add_plot(connection, "TESTPLOTAAAA01", BASE)
    add_plot(connection, "TESTPLOTBBBB02", other_box)
    return flagged(connection, "TESTPLOTAAAA01", "TESTPLOTBBBB02")


def test_a_plot_completely_inside_another_is_found(tx):
    inner = (74.50010, 19.00010, 74.50030, 19.00030)
    found = two_plots(tx, inner)
    assert set(found) == {"TESTPLOTAAAA01", "TESTPLOTBBBB02"}
    assert "TESTPLOTBBBB02 lies completely inside this plot" in found["TESTPLOTAAAA01"]
    assert "lies completely inside plot TESTPLOTAAAA01" in found["TESTPLOTBBBB02"] and "all of this plot" in found["TESTPLOTBBBB02"]
    # this is exactly what ST_Overlaps cannot see, and why the check uses ST_Intersects with a minimum area
    assert tx.execute("SELECT ST_Overlaps(a.geom, b.geom), ST_Intersects(a.geom, b.geom) FROM plots a, plots b "
                      "WHERE a.ulpin = 'TESTPLOTAAAA01' AND b.ulpin = 'TESTPLOTBBBB02'").fetchone() == (False, True)


def test_two_identical_plots_are_found(tx):
    found = two_plots(tx, BASE)
    assert set(found) == {"TESTPLOTAAAA01", "TESTPLOTBBBB02"}
    assert all("exactly the same boundary" in text for text in found.values())


def test_a_partial_overlap_is_found_with_real_numbers(tx):
    found = two_plots(tx, (74.50020, 19.00020, 74.50060, 19.00060))
    assert set(found) == {"TESTPLOTAAAA01", "TESTPLOTBBBB02"}
    assert re.search(r"overlaps plot TESTPLOTBBBB02 by [\d,]+ sq m \(\d+% of this plot\)", found["TESTPLOTAAAA01"])
    assert "overlaps plot TESTPLOTAAAA01 by" in found["TESTPLOTBBBB02"]


@pytest.mark.parametrize("name,other", [
    ("along a whole edge", (74.5004, 19.0000, 74.5008, 19.0004)),
    ("along part of an edge", (74.5004, 19.0001, 74.5008, 19.0003)),
    ("at one corner only", (74.5004, 19.0004, 74.5008, 19.0008)),
])
def test_plots_that_only_touch_are_not_flagged(tx, name, other):
    found = two_plots(tx, other)
    assert found == {}, name
    assert tx.execute("SELECT ST_Intersects(a.geom, b.geom), ST_Overlaps(a.geom, b.geom) FROM plots a, plots b "
                      "WHERE a.ulpin = 'TESTPLOTAAAA01' AND b.ulpin = 'TESTPLOTBBBB02'").fetchone() == (True, False)


def test_the_minimum_area_decides_between_survey_noise_and_a_real_overlap(tx, monkeypatch):
    # 1 centimetre of overlap along a 44 m edge is about 0.5 sq m: below the 5 sq m limit, so not flagged
    assert config.MIN_OVERLAP_SQM == 5.0
    assert two_plots(tx, (74.5003999, 19.0000, 74.5008, 19.0004)) == {}
    tx.rollback()
    # 20 centimetres of overlap along the same edge is about 9 sq m: flagged
    found = two_plots(tx, (74.500398, 19.0000, 74.5008, 19.0004))
    assert set(found) == {"TESTPLOTAAAA01", "TESTPLOTBBBB02"}
    # and the limit really does come from config.py: raise it and the same overlap is ignored
    monkeypatch.setattr(config, "MIN_OVERLAP_SQM", 20.0)
    assert flagged(tx, "TESTPLOTAAAA01", "TESTPLOTBBBB02") == {}


def test_invalid_shapes_are_still_left_out_of_the_overlap_check(tx):
    add_plot(tx, "TESTPLOTAAAA01", BASE)
    tx.execute("INSERT INTO plots (ulpin, geom, village, land_use, survey_no) VALUES "
               "('TESTPLOTBBBB02', ST_GeomFromText('POLYGON((74.5001 19.0001, 74.5003 19.0003, 74.5003 19.0001, 74.5001 19.0003, "
               "74.5001 19.0001))', 4326), 'Testville', 'residential', 'x')")
    assert flagged(tx, "TESTPLOTAAAA01", "TESTPLOTBBBB02") == {}
