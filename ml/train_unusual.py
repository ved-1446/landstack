"""Train the "unusual plot" model (unsupervised: it never sees a label).

    python -m ml.make_dataset         # first: build ml/data/
    python -m ml.train_unusual        # writes ml/models/unusual.joblib and ml/models/unusual.json

An Isolation Forest learns what a typical plot looks like from the numbers in ml/features.py alone.
How many plots get the "unusual" badge is a percentile of the score (config.UNUSUAL_PERCENTILE):
at 95, the 5% most unusual of the training plots are "unusual". The model never changes a score, a band or a
conflict; it only adds a statistical note.

SECURITY: a .joblib file is Python's pickle format. Loading one RUNS CODE. Only load model files you trained
yourself (load() below is only ever pointed at ml/models/).
"""
import argparse
import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import IsolationForest

from backend.app import config
from ml import features, make_dataset

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_FILE = "unusual.joblib"
META_FILE = "unusual.json"
DEFAULT_SEED = 2026
N_TREES = 200


class ModelProblem(Exception):
    """The saved model cannot be used (missing, or made with a different feature list or scikit-learn)."""


def fit(matrix, seed=DEFAULT_SEED, percentile=config.UNUSUAL_PERCENTILE, trees=N_TREES):
    """Fit on the feature rows only. Returns a bundle dict (see below)."""
    X = np.asarray(matrix, dtype=float)
    model = IsolationForest(n_estimators=trees, random_state=seed, contamination="auto").fit(X)
    train_scores = np.sort(-model.score_samples(X))             # higher = more unusual
    return {
        "model": model,
        "train_scores": train_scores,
        "threshold": float(np.percentile(train_scores, percentile)),
        "percentile": percentile,
        "medians": [float(v) for v in np.median(X, axis=0)],     # "typical" values, for the plain-English reasons
        "spread": [float(v) if v > 0 else 1.0 for v in X.std(axis=0)],
        "seed": seed,
        "n_train": int(X.shape[0]),
    }


def score(bundle, matrix):
    """Unusualness of each row (higher = more unusual)."""
    return -bundle["model"].score_samples(np.asarray(matrix, dtype=float))


def percentile_of(bundle, value):
    """Share (0 to 100) of the training plots that are LESS unusual than this score."""
    return 100.0 * float(np.searchsorted(bundle["train_scores"], value, side="left")) / len(bundle["train_scores"])


def is_unusual(bundle, value):
    return bool(value >= bundle["threshold"])


def metadata(bundle):
    return {
        "feature_names": features.FEATURE_NAMES,
        "sklearn_version": sklearn.__version__,
        "seed": bundle["seed"],
        "training_date": date.today().isoformat(),
        "percentile": bundle["percentile"],
        "threshold": bundle["threshold"],
        "n_train": bundle["n_train"],
        "n_trees": len(bundle["model"].estimators_),
        "what_it_is": "Isolation Forest trained on generated demo data, no labels. A statistical hint, not a conflict.",
    }


def save(bundle, folder=MODEL_DIR):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, folder / MODEL_FILE)
    (folder / META_FILE).write_text(json.dumps(metadata(bundle), indent=2) + "\n", encoding="utf-8")


def load(folder=MODEL_DIR):
    """Load a model YOU trained. Raises ModelProblem if it is missing or does not fit this code."""
    folder = Path(folder)
    model_path, meta_path = folder / MODEL_FILE, folder / META_FILE
    if not model_path.is_file() or not meta_path.is_file():
        raise ModelProblem(f"no model files in {folder}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("feature_names") != features.FEATURE_NAMES:
        raise ModelProblem("the model was trained with a different feature list: retrain it")
    if meta.get("sklearn_version") != sklearn.__version__:
        raise ModelProblem(f"the model was saved with scikit-learn {meta.get('sklearn_version')}, "
                           f"this is {sklearn.__version__}: retrain it")
    return joblib.load(model_path)      # runs code if the file is not yours: see the SECURITY note above


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(make_dataset.DATA_DIR))
    ap.add_argument("--out", default=str(MODEL_DIR))
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--percentile", type=float, default=config.UNUSUAL_PERCENTILE)
    args = ap.parse_args()
    ulpins, matrix, _labels, _meta = make_dataset.read(args.data)    # the labels are not used for training
    bundle = fit(matrix, args.seed, args.percentile)
    save(bundle, args.out)
    flagged = int(sum(score(bundle, matrix) >= bundle["threshold"]))
    print(f"trained on {len(ulpins)} plots (no labels); threshold at the {args.percentile:g}th percentile = "
          f"{bundle['threshold']:.4f}; {flagged} training plots are 'unusual'; saved to {args.out}")


if __name__ == "__main__":
    main()
