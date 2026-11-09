"""Phase 1 tests: the seed data is repeatable and matches planted_truth.json."""
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "db"))
import seed  # noqa: E402

EXPECTED_DEFAULT_COUNTS = {
    "boundary_overlap": 8,        # 4 pairs = 8 plots
    "restricted_zone_clash": 4,
    "area_mismatch": 4,
    "owner_mismatch": 4,
    "duplicate_survey_no": 8,     # 4 pairs = 8 plots
    "invalid_boundary": 4,
    "tax_overdue": 4,
    "missing_record": 4,
}


@pytest.fixture(scope="module")
def data():
    return seed.generate(100, 0.4, 42)


def test_same_seed_gives_identical_data(data):
    assert seed.generate(100, 0.4, 42) == data


def test_different_seed_gives_different_data(data):
    assert seed.generate(100, 0.4, 7) != data


def test_truth_counts_per_conflict_type(data):
    counts = Counter(t for types in data["truth"]["conflicts"].values() for t in types)
    assert dict(counts) == EXPECTED_DEFAULT_COUNTS
    assert len(data["truth"]["conflicts"]) == 40


def test_pairs_are_listed_on_both_plots(data):
    t = data["truth"]
    for ulpin, d in t["details"].items():
        if "partner" in d:
            assert t["conflicts"][ulpin] == t["conflicts"][d["partner"]]
            assert t["details"][d["partner"]]["partner"] == ulpin


def test_clean_plots_have_no_planted_problems(data):
    plots = {p["ulpin"] for p in data["rows"]["plots"]}
    problem = set(data["truth"]["conflicts"])
    clean = plots - problem
    assert len(clean) == 60
    assert problem <= plots
    # clean plots have all three records, exact same owner (or a decoy), area within 3%
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
    for d in decoys:
        assert d["ulpin"] not in data["truth"]["conflicts"]
        assert d["ror_owner"] != d["registration_owner"]
    ror = {r["ulpin"]: r["owner_name"] for r in data["rows"]["ror_records"]}
    reg = {r["ulpin"]: r["owner_name"] for r in data["rows"]["registrations"]}
    for d in decoys:
        assert ror[d["ulpin"]] == d["ror_owner"]
        assert reg[d["ulpin"]] == d["registration_owner"]


def test_survey_numbers_unique_except_planted_duplicates(data):
    dup_plots = {u for u, t in data["truth"]["conflicts"].items() if t == ["duplicate_survey_no"]}
    keys = Counter((p["village"], p["survey_no"]) for p in data["rows"]["plots"])
    repeated = {k for k, n in keys.items() if n > 1}
    assert len(repeated) == 4
    in_repeats = {p["ulpin"] for p in data["rows"]["plots"]
                  if (p["village"], p["survey_no"]) in repeated}
    assert in_repeats == dup_plots


def test_zone_count_matches_zone_clashes(data):
    assert len(data["rows"]["zones"]) == EXPECTED_DEFAULT_COUNTS["restricted_zone_clash"]


def test_truth_file_is_written(data, tmp_path):
    path = tmp_path / "truth.json"
    seed.write_truth(data, path)
    assert json.loads(path.read_text(encoding="utf-8")) == data["truth"]


def test_small_runs_work():
    d = seed.generate(10, 0.3, 1)
    assert len(d["rows"]["plots"]) == 10
    assert len(d["truth"]["conflicts"]) == 3


# --- Database check (skipped when the Docker database is not running) ---

def _db_or_skip():
    try:
        return seed.connect()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"database not reachable: {exc}")


def test_database_matches_truth_for_shapes_and_areas():
    """Loaded data: bow-ties are exactly the invalid shapes; clean areas within 3%."""
    data = seed.generate(100, 0.4, 42)
    _db_or_skip().close()
    seed.load(data)  # load() clears the data tables first
    with seed.connect() as conn, conn.cursor() as cur:
        cur.execute("SELECT ulpin FROM plots WHERE NOT ST_IsValid(geom)")
        invalid = {r[0] for r in cur.fetchall()}
        cur.execute(
            "SELECT p.ulpin, r.recorded_area_sqm / ST_Area(p.geom::geography) "
            "FROM plots p JOIN ror_records r USING (ulpin) WHERE ST_IsValid(p.geom)")
        ratios = dict(cur.fetchall())
    conflicts = data["truth"]["conflicts"]
    assert invalid == {u for u, t in conflicts.items() if t == ["invalid_boundary"]}
    for u, ratio in ratios.items():
        if "area_mismatch" in conflicts.get(u, []):
            assert abs(float(ratio) - 1) > 0.10
        else:
            assert abs(float(ratio) - 1) <= 0.03
