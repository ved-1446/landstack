"""Build the bigger training set for the unusual-plot model.

    python -m ml.make_dataset                    # 5,000 plots, about 8% with a planted problem, seed 2026
    python -m ml.make_dataset --plots 800 --seed 3

It calls db/seed.py's generate() in memory. It never touches the live database and does not change seed.py.
Output goes to ml/data/ (git-ignored):
    features.csv   ulpin + the numbers from ml/features.py          <- what the model is allowed to see
    labels.csv     ulpin + which planted problems it has            <- kept apart; used ONLY by evaluate.py
    dataset.json   how it was made (seed, size, rate)
Deterministic: the same seed always gives the same files.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

from shapely import wkt

from db import seed
from ml import features

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_PLOTS = 5000
DEFAULT_RATE = 0.08
DEFAULT_SEED = 2026


def inputs_from_generated(data):
    """db/seed.py's generated rows -> the plain inputs ml/features.py wants: (plots, zones, labels)."""
    rows = data["rows"]
    ror = {r["ulpin"]: r for r in rows["ror_records"]}
    reg = {r["ulpin"]: r for r in rows["registrations"]}
    tax = {r["ulpin"]: r for r in rows["tax_records"]}
    plots = []
    for p in rows["plots"]:
        u = p["ulpin"]
        plots.append({
            "ulpin": u, "village": p["village"], "geom": wkt.loads(p["wkt"]),
            "recorded_area_sqm": ror[u]["recorded_area_sqm"] if u in ror else None,
            "registered_on": date.fromisoformat(reg[u]["registered_on"]) if u in reg else None,
            "paid_until": date.fromisoformat(tax[u]["paid_until"]) if u in tax else None,
        })
    zones = [wkt.loads(z["wkt"]) for z in rows["zones"]]
    return plots, zones, data["truth"]["conflicts"]


def build(plots=DEFAULT_PLOTS, rate=DEFAULT_RATE, seed_value=DEFAULT_SEED):
    """Returns (ulpins, matrix, labels) where labels = {ulpin: [planted problem types]} (empty list = clean)."""
    data = seed.generate(plots, rate, seed_value, construction=False)   # the ML never looks at the simulated buildings
    plot_inputs, zones, conflicts = inputs_from_generated(data)
    ulpins, matrix = features.features_for_all(plot_inputs, zones)
    return ulpins, matrix, {u: conflicts.get(u, []) for u in ulpins}


def write(ulpins, matrix, labels, meta, folder=DATA_DIR):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "features.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ulpin", *features.FEATURE_NAMES])
        for u, row in zip(ulpins, matrix):
            w.writerow([u, *[repr(v) for v in row]])
    with open(folder / "labels.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ulpin", "n_problems", "problems"])
        for u in ulpins:
            w.writerow([u, len(labels[u]), "|".join(labels[u])])
    (folder / "dataset.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def read(folder=DATA_DIR):
    """(ulpins, matrix, labels, meta) back from disk."""
    folder = Path(folder)
    with open(folder / "features.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0][1:] == features.FEATURE_NAMES, "features.csv was made with a different feature list: rebuild it"
    ulpins = [r[0] for r in rows[1:]]
    matrix = [[float(v) for v in r[1:]] for r in rows[1:]]
    with open(folder / "labels.csv", newline="", encoding="utf-8") as f:
        labels = {r["ulpin"]: [t for t in r["problems"].split("|") if t] for r in csv.DictReader(f)}
    meta = json.loads((folder / "dataset.json").read_text(encoding="utf-8"))
    return ulpins, matrix, labels, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plots", type=int, default=DEFAULT_PLOTS)
    ap.add_argument("--rate", type=float, default=DEFAULT_RATE, help="share of plots with a planted problem")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", default=str(DATA_DIR))
    args = ap.parse_args()
    ulpins, matrix, labels = build(args.plots, args.rate, args.seed)
    with_problem = sum(1 for t in labels.values() if t)
    meta = {"plots": len(ulpins), "problem_rate_asked": args.rate, "plots_with_problem": with_problem,
            "problem_rate_real": round(with_problem / len(ulpins), 4), "seed": args.seed,
            "features": features.FEATURE_NAMES}
    write(ulpins, matrix, labels, meta, args.out)
    print(f"wrote {len(ulpins)} plots to {args.out}: {with_problem} with a planted problem "
          f"({meta['problem_rate_real']:.1%}); seed {args.seed}")


if __name__ == "__main__":
    main()
