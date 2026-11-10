"""An honest report on the unusual-plot model.

    python -m ml.evaluate                 # scores a FRESH set of 2,000 generated plots (different seed)
    python -m ml.evaluate --plots 5000 --seed 99

The labels are used only here, after training, to ask: do the plots the model calls unusual tend to be the ones
with a planted problem? The model never saw the labels and never sees the problem names. The thresholds are
the score cut-offs learned on the TRAINING plots (the percentiles below), applied to the new plots.
"""
import argparse
from collections import Counter

import numpy as np

from backend.app import config
from ml import explain, features, make_dataset, train_unusual

PERCENTILES = [90, 95, 97, 99]


def evaluate(bundle, ulpins, matrix, labels, percentiles=PERCENTILES):
    """Numbers only (also used by the tests and the notebook)."""
    scores = train_unusual.score(bundle, matrix)
    has_problem = np.array([bool(labels[u]) for u in ulpins])
    n_problem, n_clean = int(has_problem.sum()), int((~has_problem).sum())
    rows = []
    for p in percentiles:
        cut = float(np.percentile(bundle["train_scores"], p))
        flagged = scores >= cut
        tp = int((flagged & has_problem).sum())
        fp = int((flagged & ~has_problem).sum())
        rows.append({
            "percentile": p, "flagged": int(flagged.sum()),
            "problem_plots_flagged": tp, "recall": tp / n_problem if n_problem else 0.0,
            "clean_plots_flagged": fp, "false_alarm_rate": fp / n_clean if n_clean else 0.0,
            "precision": tp / int(flagged.sum()) if flagged.sum() else 0.0,
            "lift": (tp / int(flagged.sum())) / (n_problem / len(ulpins)) if flagged.sum() and n_problem else 0.0,
        })
    return {"scores": scores, "rows": rows, "n_plots": len(ulpins), "n_problem": n_problem,
            "base_rate": n_problem / len(ulpins)}


def recall_by_type(bundle, ulpins, matrix, labels, percentile):
    """For each planted problem type: (flagged, total) over all plots that have it, and (flagged, total) over the
    plots whose ONLY planted problem it is. The second pair is the honest one: a plot with several problems is
    often flagged because of a different one."""
    flagged = train_unusual.score(bundle, matrix) >= float(np.percentile(bundle["train_scores"], percentile))
    seen, hit, seen_alone, hit_alone = Counter(), Counter(), Counter(), Counter()
    for u, f in zip(ulpins, flagged):
        for t in labels[u]:
            seen[t] += 1
            hit[t] += int(f)
            if len(labels[u]) == 1:
                seen_alone[t] += 1
                hit_alone[t] += int(f)
    return {t: {"all": (hit[t], seen[t]), "alone": (hit_alone[t], seen_alone[t])} for t in sorted(seen)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plots", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=make_dataset.DEFAULT_SEED + 1, help="must differ from the training seed")
    ap.add_argument("--rate", type=float, default=make_dataset.DEFAULT_RATE)
    ap.add_argument("--models", default=str(train_unusual.MODEL_DIR))
    args = ap.parse_args()

    bundle = train_unusual.load(args.models)
    ulpins, matrix, labels = make_dataset.build(args.plots, args.rate, args.seed)
    result = evaluate(bundle, ulpins, matrix, labels)
    base = result["base_rate"]

    print(f"Evaluation on {result['n_plots']} NEW generated plots (seed {args.seed}); the model was trained on "
          f"{bundle['n_train']} others (seed {bundle['seed']}).")
    print(f"{result['n_problem']} plots have at least one planted problem ({base:.1%}); "
          f"{result['n_plots'] - result['n_problem']} are clean.\n")
    print("Threshold  Flagged  Problem plots flagged   Clean plots flagged   Precision  Lift vs luck")
    for r in result["rows"]:
        mark = "  <- used by the API" if r["percentile"] == config.UNUSUAL_PERCENTILE else ""
        print(f"  p{r['percentile']:<7} {r['flagged']:>7}  {r['problem_plots_flagged']:>6} of {result['n_problem']:<4} "
              f"({r['recall']:>5.1%})  {r['clean_plots_flagged']:>6} ({r['false_alarm_rate']:>5.1%})      "
              f"{r['precision']:>6.1%}    {r['lift']:>5.2f}x{mark}")
    print(f"\n'Luck' = flagging the same number of plots at random: it would catch about the same share of "
          f"problem plots as the share flagged, with precision {base:.1%}.\n")

    p = config.UNUSUAL_PERCENTILE
    print(f"Which planted problems does the p{p} cut-off catch?")
    print(f"  {'problem':<24} {'any plot with it':<22} {'plots where it is the only problem'}")
    for t, d in recall_by_type(bundle, ulpins, matrix, labels, p).items():
        (h, n), (ha, na) = d["all"], d["alone"]
        alone = f"{ha:>3} of {na:<4} ({ha / na:>5.1%})" if na else "none in this set"
        print(f"  {t:<24} {h:>3} of {n:<4} ({h / n:>5.1%})   {alone}")
    print(f"  (flagging {100 - p:g}% of plots at random would catch about {100 - p:g}% of any group)\n")

    explainer = explain.Explainer(bundle)
    order = np.argsort(-result["scores"])[:8]
    print(f"\nThe 8 most unusual plots, with the reasons ({explainer.method}):")
    for i in order:
        print(f"  {ulpins[i]}  score {result['scores'][i]:.3f}  planted: {', '.join(labels[ulpins[i]]) or 'nothing (clean)'}")
        for line in explainer.reasons(matrix[i]):
            print(f"      - {line}")

    if explainer.method == "shap":
        z = explain.Explainer.__new__(explain.Explainer)
        z.__dict__.update(explainer.__dict__)
        z._shap = None
        flagged_rows = [matrix[i] for i in range(len(ulpins)) if result["scores"][i] >= bundle["threshold"]]
        same = sum(explainer.top_features(r, 1) == z.top_features(r, 1) for r in flagged_rows)
        print(f"\nSHAP and plain z-scores name the same top feature for {same} of {len(flagged_rows)} flagged plots "
              f"({same / len(flagged_rows):.0%}).")

    print(f"""
WHAT THIS PROVES
  - On generated data, the model is clearly better than luck at pointing at plots with a numeric oddity
    (an overlap, an invalid shape, an area that does not match, a zone clash, overdue tax).
WHAT IT DOES NOT PROVE
  - The data was made by db/seed.py. The model mostly relearns that generator: the problems are planted by
    simple rules, so rules show up as odd numbers. Real land records have messier oddities and messier normals.
  - It is blind to problems that are not numbers in the feature list (a different owner name, a duplicate
    survey number, a missing record). Look at the "only problem" column: those are caught about as often as
    luck. When they are caught in the first column it is mostly because the same plot also has a visible problem.
  - The overlap result is the most flattering: in the generated map no two plots ever touch unless an overlap
    was planted, so "number of neighbours" alone gives it away. Real maps have touching neighbours everywhere.
  - It tells you a plot is rare, not that it is wrong. Many unusual plots are fine, and many bad plots look normal.
  - Nothing here shows it would work on real records. That needs real records and a person checking the answers.
""")


if __name__ == "__main__":
    main()
