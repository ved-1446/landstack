"""Phase 9: dataset, training, saving, evaluation and reasons. Small data, temporary folders, no database."""
import json
import re

import numpy as np
import pytest

from ml import evaluate, explain, features, make_dataset, train_unusual
from backend.tests.test_ml_features import lonlat_box, plot

SMALL = dict(plots=500, rate=0.08, seed_value=5)


@pytest.fixture(scope="module")
def small():
    ulpins, matrix, labels = make_dataset.build(**SMALL)
    return ulpins, matrix, labels


@pytest.fixture(scope="module")
def bundle(small):
    return train_unusual.fit(small[1], seed=1)


def test_dataset_is_deterministic_and_keeps_labels_apart(small, tmp_path):
    again = make_dataset.build(**SMALL)
    assert again[0] == small[0] and again[1] == small[1] and again[2] == small[2]
    ulpins, matrix, labels = small
    assert len(ulpins) == 500 and len(matrix[0]) == len(features.FEATURE_NAMES)
    assert 0.05 <= sum(1 for t in labels.values() if t) / 500 <= 0.12        # about 8%
    make_dataset.write(ulpins, matrix, labels, {"seed": 5}, tmp_path)
    header = (tmp_path / "features.csv").read_text(encoding="utf-8").splitlines()[0]
    assert "problems" not in header and "n_problems" not in header        # the model's file has no labels in it
    u2, m2, l2, meta = make_dataset.read(tmp_path)
    assert u2 == ulpins and l2 == labels and meta == {"seed": 5}
    assert np.allclose(m2, matrix)


def test_training_is_deterministic(small, bundle):
    again = train_unusual.fit(small[1], seed=1)
    flagged = lambda b: [i for i, s in enumerate(train_unusual.score(b, small[1])) if s >= b["threshold"]]  # noqa: E731
    assert flagged(bundle) == flagged(again) and len(flagged(bundle)) > 0
    assert again["threshold"] == bundle["threshold"]


def test_the_percentile_decides_how_many_are_flagged(small):
    for p in (90, 95, 99):
        b = train_unusual.fit(small[1], seed=1, percentile=p)
        n = int(sum(train_unusual.score(b, small[1]) >= b["threshold"]))
        assert abs(n - round(500 * (100 - p) / 100)) <= 2


def test_save_and_reload_from_a_temporary_folder(small, bundle, tmp_path):
    train_unusual.save(bundle, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["unusual.joblib", "unusual.json"]
    meta = json.loads((tmp_path / "unusual.json").read_text(encoding="utf-8"))
    assert meta["feature_names"] == features.FEATURE_NAMES and meta["seed"] == 1 and meta["threshold"] == bundle["threshold"]
    assert {"sklearn_version", "training_date", "percentile", "n_train"} <= set(meta)
    loaded = train_unusual.load(tmp_path)
    assert np.allclose(train_unusual.score(loaded, small[1]), train_unusual.score(bundle, small[1]))


def test_a_missing_or_unfit_model_is_refused_with_a_clear_error(bundle, tmp_path):
    with pytest.raises(train_unusual.ModelProblem):
        train_unusual.load(tmp_path / "nothing-here")
    train_unusual.save(bundle, tmp_path)
    meta = json.loads((tmp_path / "unusual.json").read_text(encoding="utf-8"))
    meta["feature_names"] = meta["feature_names"][:-1]
    (tmp_path / "unusual.json").write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(train_unusual.ModelProblem, match="different feature list"):
        train_unusual.load(tmp_path)


def test_an_extreme_plot_is_flagged_and_typical_plots_mostly_are_not():
    ulpins, matrix, _ = make_dataset.build(plots=400, rate=0.0, seed_value=8)            # a typical map, no planted problems
    model = train_unusual.fit(matrix, seed=1)
    # a huge, thin sliver with a recorded area that is far too small and old unpaid tax
    sliver = plot("EXTREME", lonlat_box(0, 0, 3000, 6), recorded=500.0, paid=__import__("datetime").date(2015, 1, 1))
    ctx = features.Context([sliver], [])
    row = [features.plot_features(sliver, ctx)[n] for n in features.FEATURE_NAMES]
    assert train_unusual.is_unusual(model, train_unusual.score(model, [row])[0])
    typical = [train_unusual.is_unusual(model, s) for s in train_unusual.score(model, matrix)]
    assert sum(typical) <= 0.06 * len(typical)
    assert train_unusual.percentile_of(model, train_unusual.score(model, [row])[0]) == 100.0


def test_evaluation_is_better_than_luck_on_generated_data(bundle):
    ulpins, matrix, labels = make_dataset.build(plots=1500, rate=0.08, seed_value=6)
    result = evaluate.evaluate(bundle, ulpins, matrix, labels, percentiles=[95])
    row = result["rows"][0]
    assert row["flagged"] > 0 and row["problem_plots_flagged"] + row["clean_plots_flagged"] == row["flagged"]
    assert row["lift"] > 2          # (on generated data only: this is the generator being relearned, see the README)
    by_type = evaluate.recall_by_type(bundle, ulpins, matrix, labels, 95)
    assert by_type["boundary_overlap"]["all"][1] > 0 and by_type["boundary_overlap"]["all"][0] > 0


def test_reasons_are_short_plain_and_never_name_another_plot(small, bundle):
    ulpins, matrix, _ = small
    scores = train_unusual.score(bundle, matrix)
    top = [matrix[i] for i in np.argsort(-scores)[:25]]
    for method in ("shap", "z-score"):
        e = explain.Explainer(bundle)
        if method == "z-score":
            e._shap, e.method = None, "z-score"
        for row in top:
            reasons = e.reasons(row)
            assert 1 <= len(reasons) <= 3
            for line in reasons:
                assert isinstance(line, str) and 10 < len(line) < 140
                assert not re.search(r"\b[A-Z0-9]{14}\b", line)
                assert "nan" not in line.lower()
