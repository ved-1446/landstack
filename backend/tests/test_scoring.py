"""Scoring tests with hand-made findings (no database needed)."""
import pytest

from backend.app import config, scoring


def fs(*points):
    return [{"ulpin": "X", "type": "t", "points": p, "evidence": "e"} for p in points]


def test_no_findings_scores_zero_green():
    r = scoring.score_plot([])
    assert (r["score"], r["band"], r["findings"]) == (0, "green", [])


def test_points_are_added():
    r = scoring.score_plot(fs(40, 25, 10))
    assert r["score"] == 75
    assert r["band"] == "red"
    assert len(r["findings"]) == 3


def test_score_caps_at_100():
    assert scoring.score_plot(fs(40, 30, 25, 25, 20))["score"] == 100


@pytest.mark.parametrize("score,band", [
    (0, "green"), (24, "green"), (25, "amber"), (59, "amber"), (60, "red"), (100, "red"),
])
def test_band_edges(score, band):
    assert scoring.band_for(score) == band


def test_band_edges_through_score_plot():
    assert scoring.score_plot(fs(24))["band"] == "green"
    assert scoring.score_plot(fs(25))["band"] == "amber"
    assert scoring.score_plot(fs(59))["band"] == "amber"
    assert scoring.score_plot(fs(60))["band"] == "red"


def test_point_values_match_the_brief():
    assert config.POINTS == {
        "boundary_overlap": 40, "restricted_zone_clash": 30, "area_mismatch": 25,
        "owner_mismatch": 25, "duplicate_survey_no": 20, "invalid_boundary": 15,
        "tax_overdue": 15, "missing_record": 10,
    }
    assert config.SCORE_CAP == 100
