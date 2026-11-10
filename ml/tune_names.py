"""Compare the name matcher with simple baselines, on pairs it was not tuned on.

    python -m ml.make_name_pairs     # once: ml/data/name_pairs.csv
    python -m ml.tune_names

The pairs are split into a TRAIN part and a TEST part (60/40, stratified by pair kind, fixed seed). Each method's
threshold is picked on the TRAIN part only; every number in the report is measured on the TEST part.
This script never edits config.py. It prints a decision; the change (if any) is made by hand.

How the threshold is picked: try 0.00, 0.01, ... 1.00 and take the one with the best F1 on the train pairs
(F1 balances "do not miss a real match" against "do not call different people the same"). If several thresholds tie, take the
middle of the tied range, because the middle is the least fragile choice.
"""
import difflib
import random
import re
import string
from collections import defaultdict

from backend.app import config, names
from ml import make_name_pairs

SPLIT_SEED = 11
TRAIN_SHARE = 0.6
GRID = [i / 100 for i in range(0, 101)]
MIN_F1_GAIN = 0.02      # "clearly better": the test F1 must improve by at least this much
_PUNCT = re.compile(f"[{re.escape(string.punctuation)}]")


# ---- the methods: each turns a pair into a score between 0 and 1 (exact match is 0 or 1) ----

def score_current(a, b):
    return names.similarity(a, b)


def score_exact(a, b):
    return 1.0 if a == b else 0.0


def score_difflib(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _sorted_tokens(name):
    return " ".join(sorted(_PUNCT.sub(" ", name.lower()).split()))


def score_token_sorted(a, b):
    return difflib.SequenceMatcher(None, _sorted_tokens(a), _sorted_tokens(b)).ratio()


SCORERS = {"current (TF-IDF)": score_current, "exact match": score_exact,
           "difflib ratio": score_difflib, "token-sorted ratio": score_token_sorted}


# ---- splitting, thresholds, metrics ----

def split(rows, seed=SPLIT_SEED, train_share=TRAIN_SHARE):
    by_kind = defaultdict(list)
    for r in rows:
        by_kind[r[3]].append(r)
    train, test = [], []
    rng = random.Random(seed)
    for kind in sorted(by_kind):
        group = by_kind[kind][:]
        rng.shuffle(group)
        cut = round(len(group) * train_share)
        train += group[:cut]
        test += group[cut:]
    return train, test


def confusion(scores, labels, threshold):
    tp = sum(1 for s, y in zip(scores, labels) if s >= threshold and y == 1)
    fp = sum(1 for s, y in zip(scores, labels) if s >= threshold and y == 0)
    fn = sum(1 for s, y in zip(scores, labels) if s < threshold and y == 1)
    tn = sum(1 for s, y in zip(scores, labels) if s < threshold and y == 0)
    return tp, fp, fn, tn


def metrics(tp, fp, fn, tn):
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}


def pick_threshold(scores, labels):
    """Best-F1 threshold on the given pairs; ties -> the middle of the tied thresholds."""
    f1s = [(metrics(*confusion(scores, labels, t))["f1"], t) for t in GRID]
    best = max(f for f, _ in f1s)
    tied = [t for f, t in f1s if best - f < 1e-12]
    return tied[len(tied) // 2]


def run(rows=None):
    rows = rows if rows is not None else make_name_pairs.read()
    train, test = split(rows)
    ytr, yte = [r[2] for r in train], [r[2] for r in test]
    out = {"n_train": len(train), "n_test": len(test), "methods": {}, "train": train, "test": test}
    for label, fn in SCORERS.items():
        s_train = [fn(r[0], r[1]) for r in train]
        s_test = [fn(r[0], r[1]) for r in test]
        tuned = 0.5 if label == "exact match" else pick_threshold(s_train, ytr)
        entry = {"threshold": tuned, "test": metrics(*confusion(s_test, yte, tuned)), "scores_test": s_test}
        if label.startswith("current"):
            entry["test_at_shipped"] = metrics(*confusion(s_test, yte, config.NAME_MATCH_THRESHOLD))
            entry["train_at_shipped"] = metrics(*confusion([fn(r[0], r[1]) for r in train], ytr, config.NAME_MATCH_THRESHOLD))
        out["methods"][label] = entry
    return out


def demo_pairs():
    """The 6 decoy pairs (same person, written differently) and the genuinely different owner pairs in the demo data."""
    from db import seed
    data = seed.generate()
    ror = {r["ulpin"]: r["owner_name"] for r in data["rows"]["ror_records"]}
    reg = {r["ulpin"]: r["owner_name"] for r in data["rows"]["registrations"]}
    decoys = [(d["ror_owner"], d["registration_owner"]) for d in data["truth"]["decoys"]]
    different = [(ror[u], reg[u]) for u, t in data["truth"]["conflicts"].items() if "owner_mismatch" in t]
    return decoys, different


def decide(result, decoys, different, shipped=config.NAME_MATCH_THRESHOLD):
    """(change?, candidate threshold, reasons). Change only if ALL of: clearly better on the test pairs, every decoy still
    matches, and no genuinely different demo pair matches."""
    candidate = result["methods"]["current (TF-IDF)"]["threshold"]
    gain = (result["methods"]["current (TF-IDF)"]["test"]["f1"]
            - result["methods"]["current (TF-IDF)"]["test_at_shipped"]["f1"])
    decoys_ok = all(names.similarity(a, b) >= candidate for a, b in decoys)
    different_ok = all(names.similarity(a, b) < candidate for a, b in different)
    reasons = [f"test F1 gain {gain:+.3f} (needs at least +{MIN_F1_GAIN:.2f})",
               f"all {len(decoys)} decoy pairs still match at {candidate:.2f}: {decoys_ok}",
               f"none of the {len(different)} genuinely different demo pairs match at {candidate:.2f}: {different_ok}"]
    return (gain >= MIN_F1_GAIN and decoys_ok and different_ok and candidate != shipped), candidate, reasons


def mistakes(result, which, count=5):
    """Examples where the current matcher (at the shipped threshold) is wrong, from the test pairs first."""
    t = config.NAME_MATCH_THRESHOLD
    wanted = (lambda s, y: s < t and y == 1) if which == "missed" else (lambda s, y: s >= t and y == 0)
    found = [(r, s) for r, s in zip(result["test"], result["methods"]["current (TF-IDF)"]["scores_test"]) if wanted(s, r[2])]
    return sorted(found, key=lambda x: -abs(x[1] - t))[:count]


def main():
    result = run()
    n = make_name_pairs.read()
    pos = sum(r[2] for r in n)
    print(f"{len(n)} pairs ({pos} same person, {len(n) - pos} different) -> {result['n_train']} train / {result['n_test']} test. "
          f"Thresholds are picked on train; everything below is measured on the {result['n_test']} TEST pairs.\n")
    print(f"{'method':<28}{'threshold':>9}{'precision':>11}{'recall':>9}{'F1':>8}   confusion (TP FP FN TN)")
    cur = result["methods"]["current (TF-IDF)"]
    rows = [("current, as shipped", config.NAME_MATCH_THRESHOLD, cur["test_at_shipped"])]
    rows += [(label + (", tuned" if label.startswith("current") else ""), e["threshold"], e["test"])
             for label, e in result["methods"].items()]
    for label, t, m in rows:
        print(f"{label:<28}{t:>9.2f}{m['precision']:>11.3f}{m['recall']:>9.3f}{m['f1']:>8.3f}   "
              f"{m['tp']:>3} {m['fp']:>3} {m['fn']:>3} {m['tn']:>3}")
    print("\n(precision = of the pairs called 'same person', how many really are; recall = of the real same-person pairs, how many were found)")

    for which, title in (("missed", "MISSED (same person, but the score is below the threshold)"),
                         ("wrong", "FALSE MATCHES (different people, but the score is at or above the threshold)")):
        print(f"\nCurrent matcher at {config.NAME_MATCH_THRESHOLD:.2f}: {title}")
        for (a, b, _y, kind), s in mistakes(result, which):
            print(f"  {a!r:<32} vs {b!r:<32} score {s:.2f}  [{kind}]")

    decoys, different = demo_pairs()
    change, candidate, reasons = decide(result, decoys, different)
    print("\nDecision rule: change NAME_MATCH_THRESHOLD only if ALL are true")
    for r in reasons:
        print("  -", r)
    print(f"=> {'CHANGE to ' + format(candidate, '.2f') if change else 'KEEP ' + format(config.NAME_MATCH_THRESHOLD, '.2f')}")
    print("\nThe pairs were made by rules (ml/make_name_pairs.py). Real names will behave differently.")


if __name__ == "__main__":
    main()
