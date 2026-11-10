"""The seed data is repeatable, has the designed mix of problems, and matches planted_truth.json."""
import json
import sys
from collections import Counter
from pathlib import Path

import pytest
from shapely import wkt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "db"))
import seed  # noqa: E402
from backend.app import config  # noqa: E402

CONSTRUCTION = "unrecorded_construction"      # Phase 10 (SIMULATED): counted apart from the eight earlier problems
EXPECTED_DEFAULT_COUNTS = {            # how many PLOTS carry each of the EIGHT earlier problems (a plot may carry several)
    "boundary_overlap": 14,            # 6 partial-overlap pairs + 1 contained pair = 14 plots
    "restricted_zone_clash": 12,
    "area_mismatch": 12,
    "owner_mismatch": 14,
    "duplicate_survey_no": 8,          # 4 pairs
    "invalid_boundary": 4,
    "tax_overdue": 6,
    "missing_record": 4,
}


def score_of(problems):
    """What the real scoring gives a plot with these problems (points added, capped), worked out here
    from the truth file alone, independent of the checks engine. (Missing record counts once per plot.)"""
    return min(sum(config.POINTS[t] for t in problems), config.SCORE_CAP)


def band_of(score):
    return "red" if score >= config.RED_FROM else "amber" if score >= config.AMBER_FROM else "green"


@pytest.fixture(scope="module")
def data():
    return seed.generate()                                   # the demo settings


@pytest.fixture(scope="module")
def shapes(data):
    return {p["ulpin"]: wkt.loads(p["wkt"]) for p in data["rows"]["plots"]}


def test_defaults_are_the_demo_settings():
    d = seed.generate()
    assert (d["truth"]["plots"], d["truth"]["problem_rate"], d["truth"]["seed"]) == (100, 0.48, 42)


def test_same_seed_gives_identical_data(data):
    assert seed.generate() == data


def test_different_seed_gives_different_data(data):
    assert seed.generate(100, 0.48, 7) != data


# ---------------- the designed mix ----------------

def test_truth_counts_per_conflict_type(data):
    # CHANGED in Phase 10: the truth now also lists the planted construction alerts. The eight earlier problems must be
    # exactly what they were (same counts, same 48 plots); the alerts are checked separately below.
    conflicts = data["truth"]["conflicts"]
    counts = Counter(t for types in conflicts.values() for t in types)
    assert counts.pop(CONSTRUCTION) == 10
    assert dict(counts) == EXPECTED_DEFAULT_COUNTS
    assert all(n >= 4 for n in counts.values())                  # every type on at least 4 plots
    had_earlier_problem = {u for u, types in conflicts.items() if set(types) - {CONSTRUCTION}}
    assert len(had_earlier_problem) == 48
    assert len(conflicts) == 53                                  # 48, plus 5 alert plots that had no other problem


def test_some_plots_carry_several_problems(data):
    # CHANGED in Phase 10: without the alerts the mix is exactly the old {1: 33, 2: 6, 3: 7, 4: 2}; with them (the alert is
    # one more problem on 10 plots, 5 of them new problem plots) it is {1: 36, 2: 6, 3: 8, 4: 3}.
    earlier = Counter(len([t for t in types if t != CONSTRUCTION]) for types in data["truth"]["conflicts"].values())
    earlier.pop(0)                                              # plots that only have an alert
    assert dict(earlier) == {1: 33, 2: 6, 3: 7, 4: 2}
    sizes = Counter(len(types) for types in data["truth"]["conflicts"].values())
    assert dict(sizes) == {1: 36, 2: 6, 3: 8, 4: 3}
    for types in data["truth"]["conflicts"].values():
        assert types == [t for t in config.POINTS if t in types]  # listed in the standard order, no repeats


def test_the_demo_has_58_green_29_amber_13_red(data):
    # CHANGED in Phase 10 (was 60 / 28 / 12): the +15 alert moves two plots green -> amber and one amber -> red.
    scores = {u: score_of(t) for u, t in data["truth"]["conflicts"].items()}
    bands = Counter(band_of(scores.get(p["ulpin"], 0)) for p in data["rows"]["plots"])
    assert dict(bands) == {"green": 58, "amber": 29, "red": 13}
    before = {u: score_of([t for t in types if t != CONSTRUCTION]) for u, types in data["truth"]["conflicts"].items()}
    moved = {(band_of(before[u]), band_of(scores[u])) for u in scores if band_of(before[u]) != band_of(scores[u])}
    assert moved == {("green", "amber"), ("amber", "red")}            # the alert visibly matters in the demo
    capped = [u for u, t in data["truth"]["conflicts"].items() if sum(config.POINTS[x] for x in t) > config.SCORE_CAP]
    assert len(capped) == 2 and all(scores[u] == 100 for u in capped)          # the cap is really shown
    red = [u for u, s in scores.items() if s >= config.RED_FROM]
    assert all(len(data["truth"]["conflicts"][u]) >= 2 for u in red)           # one problem never reaches red


def test_pairs_are_listed_on_both_plots(data):
    t = data["truth"]
    overlap_pairs, dup_pairs, contained = set(), set(), 0
    for ulpin, d in t["details"].items():
        if "overlap_partner" in d:
            other = t["details"][d["overlap_partner"]]
            assert other["overlap_partner"] == ulpin
            assert "boundary_overlap" in t["conflicts"][ulpin] and "boundary_overlap" in t["conflicts"][d["overlap_partner"]]
            assert {d["overlap_relation"], other["overlap_relation"]} in ({"overlaps"}, {"contains", "inside"})
            overlap_pairs.add(frozenset((ulpin, d["overlap_partner"])))
            contained += d["overlap_relation"] == "contains"
        if "dup_partner" in d:
            other = t["details"][d["dup_partner"]]
            assert other["dup_partner"] == ulpin
            assert "duplicate_survey_no" in t["conflicts"][ulpin] and "duplicate_survey_no" in t["conflicts"][d["dup_partner"]]
            dup_pairs.add(frozenset((ulpin, d["dup_partner"])))
    assert len(overlap_pairs) == 7 and contained == 1 and len(dup_pairs) == 4


def test_the_contained_pair_really_is_inside_and_the_touching_pair_really_only_touches(data, shapes):
    t = data["truth"]
    (outer,) = [u for u, d in t["details"].items() if d.get("overlap_relation") == "contains"]
    inner = t["details"][outer]["overlap_partner"]
    assert shapes[outer].contains(shapes[inner]) and not shapes[outer].equals(shapes[inner])

    ((a, b),) = t["touching_pairs"]
    assert a not in t["conflicts"] and b not in t["conflicts"]                 # both are clean
    assert shapes[a].touches(shapes[b])                                        # a shared edge...
    assert shapes[a].intersection(shapes[b]).area == 0                         # ...and no shared ground


def test_a_missing_record_never_removes_one_that_another_problem_needs(data):
    needs = {"owner_mismatch": {"ror_records", "registrations"}, "area_mismatch": {"ror_records"},
             "tax_overdue": {"tax_records"}}
    t = data["truth"]
    for ulpin, d in t["details"].items():
        if "missing_table" in d:
            assert "missing_record" in t["conflicts"][ulpin]
            for problem in t["conflicts"][ulpin]:
                assert d["missing_table"] not in needs.get(problem, set())


def test_planted_problems_do_not_clash_in_geometry(data):
    """Invalid shapes are only combined with record problems (the geometry checks skip invalid shapes)."""
    for ulpin, types in data["truth"]["conflicts"].items():
        if "invalid_boundary" in types:
            assert not set(types) & {"boundary_overlap", "restricted_zone_clash", "area_mismatch"}


# ---------------- clean plots, decoys, duplicates, zones ----------------

def test_plots_with_no_planted_problem_have_clean_records(data):
    # CHANGED in Phase 10: 5 formerly clean plots now carry a planted construction alert, so 47 plots (was 52) have no
    # planted problem at all. (Renamed from "clean plots": a plot with a record in good order can still have an alert.)
    plots = {p["ulpin"] for p in data["rows"]["plots"]}
    problem = set(data["truth"]["conflicts"])
    clean = plots - problem
    assert len(clean) == 47 and problem <= plots
    # clean plots have all three records, exact same owner (or a decoy), recent tax
    ror = {r["ulpin"]: r for r in data["rows"]["ror_records"]}
    reg = {r["ulpin"]: r for r in data["rows"]["registrations"]}
    tax = {r["ulpin"]: r for r in data["rows"]["tax_records"]}
    decoys = {d["ulpin"] for d in data["truth"]["decoys"]}
    for u in clean:
        assert u in ror and u in reg and u in tax
        if u not in decoys:
            assert ror[u]["owner_name"] == reg[u]["owner_name"]
        assert tax[u]["paid_until"] >= "2025-01-01"  # nowhere near 2 years overdue


def test_six_decoy_pairs_on_clean_plots(data):
    decoys = data["truth"]["decoys"]
    assert len(decoys) == 6
    touching = {u for pair in data["truth"]["touching_pairs"] for u in pair}
    for d in decoys:
        assert d["ulpin"] not in data["truth"]["conflicts"] and d["ulpin"] not in touching
        assert d["ror_owner"] != d["registration_owner"]
    ror = {r["ulpin"]: r["owner_name"] for r in data["rows"]["ror_records"]}
    reg = {r["ulpin"]: r["owner_name"] for r in data["rows"]["registrations"]}
    for d in decoys:
        assert ror[d["ulpin"]] == d["ror_owner"]
        assert reg[d["ulpin"]] == d["registration_owner"]


def test_survey_numbers_unique_except_planted_duplicates(data):
    dup_plots = {u for u, t in data["truth"]["conflicts"].items() if "duplicate_survey_no" in t}
    keys = Counter((p["village"], p["survey_no"]) for p in data["rows"]["plots"])
    repeated = {k for k, n in keys.items() if n > 1}
    assert len(repeated) == 4
    in_repeats = {p["ulpin"] for p in data["rows"]["plots"] if (p["village"], p["survey_no"]) in repeated}
    assert in_repeats == dup_plots


def test_zone_count_matches_zone_clashes(data):
    assert len(data["rows"]["zones"]) == EXPECTED_DEFAULT_COUNTS["restricted_zone_clash"]


def test_truth_file_is_written(data, tmp_path):
    path = tmp_path / "truth.json"
    seed.write_truth(data, path)
    assert json.loads(path.read_text(encoding="utf-8")) == data["truth"]


# ---------------- other sizes and rates ----------------

def test_small_runs_work():
    d = seed.generate(10, 0.3, 1)
    assert len(d["rows"]["plots"]) == 10
    # CHANGED in Phase 10: the 3 earlier problem plots are unchanged; one more plot carries the (planted) alert
    earlier = {u for u, types in d["truth"]["conflicts"].items() if set(types) - {CONSTRUCTION}}
    assert len(earlier) == 3
    assert sum(CONSTRUCTION in t for t in d["truth"]["conflicts"].values()) == 1
    assert d["truth"]["touching_pairs"] == []              # too few plots for a touching pair


def test_other_problem_rates_work():
    none = seed.generate(100, 0.0, 42)
    assert none["truth"]["conflicts"] == {}                  # rate 0 = no planted problem of any kind, alerts included
    assert none["truth"]["construction_decoys"] == []
    assert len(none["rows"]["building_snapshots"]) > 0       # ...but every plot still has its buildings
    more = seed.generate(100, 0.6, 42)                       # beyond the designed set: filler problems are added
    # CHANGED in Phase 10: 60 plots with an earlier problem, plus the alerts (which only add plots that had none)
    assert len([u for u, t in more["truth"]["conflicts"].items() if set(t) - {CONSTRUCTION}]) == 60
    assert seed.generate(100, 0.6, 42) == more


# --- Database check (skipped when the Docker database is not running) ---

def test_database_matches_truth_for_shapes_and_areas(truth):
    """Loaded data: bow-ties are exactly the invalid shapes; areas are within 3% unless an area mismatch was planted.
    (Loads the data planted_truth.json describes, so the live database stays consistent with it.)"""
    data = seed.generate(truth["plots"], truth["problem_rate"], truth["seed"])
    try:
        seed.connect().close()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"database not reachable: {exc}")
    seed.load(data)  # load() clears the data tables first
    with seed.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT ulpin FROM plots WHERE NOT ST_IsValid(geom)")
        invalid = {r[0] for r in cur.fetchall()}
        cur.execute(
            "SELECT p.ulpin, r.recorded_area_sqm / ST_Area(p.geom::geography) "
            "FROM plots p JOIN ror_records r USING (ulpin) WHERE ST_IsValid(p.geom)")
        ratios = dict(cur.fetchall())
    conflicts = data["truth"]["conflicts"]
    assert invalid == {u for u, t in conflicts.items() if "invalid_boundary" in t}
    for u, ratio in ratios.items():
        if "area_mismatch" in conflicts.get(u, []):
            assert abs(float(ratio) - 1) > 0.10
        else:
            assert abs(float(ratio) - 1) <= 0.03
