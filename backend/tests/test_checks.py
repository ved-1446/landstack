"""Each check must flag exactly the plots planted_truth.json says: no misses, no extras."""
import pytest

from backend.app import checks, scoring

CHECK_FUNCS = [
    ("boundary_overlap", checks.check_boundary_overlap),
    ("restricted_zone_clash", checks.check_restricted_zone_clash),
    ("area_mismatch", checks.check_area_mismatch),
    ("owner_mismatch", checks.check_owner_mismatch),
    ("duplicate_survey_no", checks.check_duplicate_survey_no),
    ("invalid_boundary", checks.check_invalid_boundary),
    ("tax_overdue", checks.check_tax_overdue),
    ("missing_record", checks.check_missing_record),
]


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


def test_clean_plots_score_zero(conn, truth):
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


def test_overlap_evidence_names_the_partner(conn, truth):
    by_plot = {f["ulpin"]: f for f in checks.check_boundary_overlap(conn)}
    for u, d in truth["details"].items():
        if u in by_plot:
            assert d["partner"] in by_plot[u]["evidence"]
