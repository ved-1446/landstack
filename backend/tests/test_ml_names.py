"""Phase 9, Part B: the labelled name pairs and the matcher tuning. No database."""
import csv

import pytest

from backend.app import config, names
from ml import make_name_pairs, tune_names


@pytest.fixture(scope="module")
def rows():
    return make_name_pairs.read()


@pytest.fixture(scope="module")
def result(rows):
    return tune_names.run(rows)


def test_the_saved_pair_set_loads_and_is_balanced(rows):
    assert make_name_pairs.PAIRS_FILE.is_file()
    assert len(rows) == 600
    assert sum(r[2] for r in rows) == 300
    assert {r[2] for r in rows} == {0, 1}
    assert len({(frozenset((r[0], r[1])), r[2]) for r in rows}) == 600        # no duplicates
    kinds = {r[3] for r in rows}
    assert {"order", "initial", "dropped_middle", "spelling", "honorific", "case_punctuation",
            "same_surname", "lookalike_surname", "lookalike_first_name", "different_middle_name"} <= kinds
    assert all(r[0].strip() and r[1].strip() for r in rows)


def test_the_saved_file_is_what_the_generator_makes_today(rows, tmp_path):
    again = tmp_path / "pairs.csv"
    make_name_pairs.write(make_name_pairs.build(), again)
    assert make_name_pairs.read(again) == rows          # fixed seed: same file every time


def test_the_split_is_fixed_and_does_not_overlap(rows):
    train, test = tune_names.split(rows)
    assert (len(train), len(test)) == (360, 240)
    assert not set(train) & set(test)
    assert tune_names.split(rows) == (train, test)
    assert {r[2] for r in train} == {r[2] for r in test} == {0, 1}


def test_the_metrics_are_reproducible(rows, result):
    again = tune_names.run(rows)
    for label, entry in result["methods"].items():
        assert again["methods"][label]["threshold"] == entry["threshold"]
        assert again["methods"][label]["test"] == entry["test"]
    cur = result["methods"]["current (TF-IDF)"]
    assert cur["test_at_shipped"] == again["methods"]["current (TF-IDF)"]["test_at_shipped"]


def test_metric_arithmetic_on_a_hand_made_example():
    m = tune_names.metrics(tp=8, fp=2, fn=2, tn=88)
    assert m["precision"] == 0.8 and m["recall"] == 0.8 and m["f1"] == pytest.approx(0.8)
    assert tune_names.confusion([0.9, 0.8, 0.2, 0.1], [1, 0, 1, 0], 0.5) == (1, 1, 1, 1)
    assert tune_names.metrics(0, 0, 5, 5)["f1"] == 0.0


def test_the_current_matcher_beats_the_trivial_baselines(result):
    f1 = {k: v["test"]["f1"] for k, v in result["methods"].items()}
    assert f1["current (TF-IDF)"] > f1["exact match"]
    assert f1["current (TF-IDF)"] > f1["difflib ratio"]
    assert result["methods"]["exact match"]["test"]["recall"] < 0.2      # exact match misses nearly every reordered or misspelt name


def test_every_decoy_still_matches_and_every_genuine_mismatch_still_does_not():
    decoys, different = tune_names.demo_pairs()
    assert len(decoys) == 6 and len(different) == 14
    for a, b in decoys:
        assert names.same_person(a, b)[0], (a, b)
    for a, b in different:
        assert not names.same_person(a, b)[0], (a, b)


def test_the_decision_rule_keeps_the_threshold_unless_the_evidence_is_clear(result):
    decoys, different = tune_names.demo_pairs()
    change, candidate, reasons = tune_names.decide(result, decoys, different)
    assert len(reasons) == 3
    if change:
        # a change is only allowed when it clearly helps AND is safe on the demo data
        assert candidate != config.NAME_MATCH_THRESHOLD
    else:
        assert config.NAME_MATCH_THRESHOLD == 0.60 or candidate == config.NAME_MATCH_THRESHOLD
    # and whatever is shipped must satisfy the safety rules for the decoys and the genuine mismatches
    assert all(names.similarity(a, b) >= config.NAME_MATCH_THRESHOLD for a, b in decoys)
    assert all(names.similarity(a, b) < config.NAME_MATCH_THRESHOLD for a, b in different)


def _pretend(result, threshold):
    """A copy of the result in which tuning 'found' this threshold and a perfect test score (rule 1 passes)."""
    cur = result["methods"]["current (TF-IDF)"]
    methods = {**result["methods"], "current (TF-IDF)": {**cur, "threshold": threshold, "test": {**cur["test"], "f1": 1.0}}}
    return {**result, "methods": methods}


def test_the_decision_refuses_a_threshold_that_would_lose_a_decoy(result):
    decoys, different = tune_names.demo_pairs()
    change, _, reasons = tune_names.decide(_pretend(result, 1.01), decoys, different)     # nothing can reach 1.01
    assert not change and reasons[1].endswith("False")


def test_the_decision_refuses_a_threshold_that_would_match_different_owners(result):
    decoys, different = tune_names.demo_pairs()
    change, _, reasons = tune_names.decide(_pretend(result, 0.01), decoys, different)
    assert not change and reasons[2].endswith("False")


def test_mistakes_lists_real_errors(result):
    missed = tune_names.mistakes(result, "missed")
    wrong = tune_names.mistakes(result, "wrong")
    assert 0 < len(missed) <= 5 and 0 < len(wrong) <= 5
    for (a, b, y, _k), s in missed:
        assert y == 1 and s < config.NAME_MATCH_THRESHOLD
    for (a, b, y, _k), s in wrong:
        assert y == 0 and s >= config.NAME_MATCH_THRESHOLD


def test_the_pair_file_has_the_expected_columns():
    with open(make_name_pairs.PAIRS_FILE, newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == ["name_a", "name_b", "same_person", "kind"]
