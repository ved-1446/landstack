"""Seed LandStack with deterministic fake land data near Pune.

Usage: python db/seed.py [--plots 100] [--problem-rate 0.4] [--seed 42]

generate() is pure (no database): the same arguments always return the same data.
main() loads that data into PostgreSQL and writes db/planted_truth.json.
"""
import argparse
import itertools
import json
import math
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

from shapely import to_wkt
from shapely.affinity import translate
from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app.config import REFERENCE_DATE  # noqa: E402  (single copy lives in config.py)
TRUTH_PATH = Path(__file__).resolve().parent / "planted_truth.json"

ORIGIN_LON, ORIGIN_LAT = 73.80, 18.55  # near Pune
CELL = 120.0  # metres between plot cells; plots are at most 50 m wide

VILLAGES = ["Hinjewadi", "Wagholi", "Mulshi", "Lohegaon", "Pirangut"]
LAND_USES = ["residential", "agricultural", "commercial", "industrial"]
ZONE_TYPES = ["forest", "river_buffer", "defence", "flood_plain"]
FIRST = ["Amit", "Sanjay", "Rahul", "Neha", "Pooja", "Suresh", "Kavita", "Mahesh",
         "Rohit", "Swati", "Anil", "Deepak", "Savita", "Nitin", "Archana", "Ganesh"]
LAST = ["Pawar", "Gaikwad", "More", "Bhosale", "Kale", "Chavan", "Salunkhe", "Thorat",
        "Jagtap", "Kamble", "Mane", "Sawant", "Lokhande", "Nikam", "Gore", "Ghadge"]
# (name in RoR, same person spelled differently in the registration)
DECOY_PAIRS = [
    ("Ramesh Kulkarni", "Kulkarni Ramesh S."),
    ("Sunita Deshpande", "Sunita R. Deshpande"),
    ("Prakash Joshi", "Joshi Prakash"),
    ("Anita Patil", "Anita D Patil"),
    ("Vijay Shinde", "Vijay K. Shinde"),
    ("Meena Jadhav", "Jadhav Meena D."),
]

# One problem per plot, cycled. Only used as FILLER when --problem-rate asks for more problem plots
# than the designed demo set below contains.
CYCLE = [
    ("boundary_overlap", 2), ("restricted_zone_clash", 1), ("area_mismatch", 1),
    ("owner_mismatch", 1), ("duplicate_survey_no", 2), ("invalid_boundary", 1),
    ("tax_overdue", 1), ("missing_record", 1),
]
CONFLICT_TYPES = [t for t, _ in CYCLE]
MISSING_TABLES = ["ror_records", "registrations", "tax_records"]

OVERLAP, ZONE, AREA, OWNER = "boundary_overlap", "restricted_zone_clash", "area_mismatch", "owner_mismatch"
DUP, INVALID, TAX, MISSING = "duplicate_survey_no", "invalid_boundary", "tax_overdue", "missing_record"


def _g(plots, *links):
    """A group of plots that belong together. `plots` lists the problems of each plot; a link is
    (problem, anchor plot, partner plot[, relation]) and says the two plots share that problem
    (an overlap or a duplicate survey number). relation "inside" = the partner lies inside the anchor."""
    return {"plots": [list(p) for p in plots], "links": list(links)}


_OVERLAPS = "overlaps"
_TRIPLE = [_g([[ZONE]]), _g([[AREA]]), _g([[OWNER]])]        # three plain single-problem plots (all score 25 to 30)

# The designed demo set for 100 plots at problem rate 0.48: 48 problem plots. Single problems score at most 40, so a
# RED plot (60+) must carry several problems; the capped plots (100) carry four. Order matters only for small runs:
# the first groups give a balanced mix, and a run that wants fewer problem plots simply stops early.
DESIGNED = [
    _g([[OVERLAP, ZONE], [OVERLAP]], (OVERLAP, 0, 1, _OVERLAPS)),                                   # 70 red, 40 amber
    *_TRIPLE,
    _g([[DUP, AREA, OWNER], [DUP, MISSING]], (DUP, 0, 1)),                                          # 70 red, 30 amber
    _g([[INVALID]]),                                                                                # 15 green
    _g([[MISSING]]),                                                                                # 10 green
    _g([[OVERLAP], [OVERLAP]], (OVERLAP, 0, 1, "inside")),                                          # one plot lies inside the other
    *_TRIPLE,
    _g([[OVERLAP, ZONE, OWNER], [OVERLAP, MISSING]], (OVERLAP, 0, 1, _OVERLAPS)),                   # 95 red, 50 amber
    _g([[AREA, OWNER, TAX]]),                                                                       # 65 red
    _g([[OVERLAP, OWNER, TAX], [OVERLAP, AREA]], (OVERLAP, 0, 1, _OVERLAPS)),                       # 80 red, 65 red
    *_TRIPLE,
    _g([[DUP, ZONE, TAX], [DUP]], (DUP, 0, 1)),                                                     # 65 red, 20 green
    _g([[INVALID]]),
    _g([[ZONE, OWNER, TAX]]),                                                                       # 70 red
    *_TRIPLE,
    _g([[OVERLAP, DUP, TAX], [OVERLAP, MISSING], [DUP]], (OVERLAP, 0, 1, _OVERLAPS), (DUP, 0, 2)),  # 75 red, 50 amber, 20 green
    _g([[INVALID]]),
    *_TRIPLE,
    _g([[OVERLAP, ZONE, OWNER, TAX], [OVERLAP, AREA]], (OVERLAP, 0, 1, _OVERLAPS)),                 # 110 -> capped 100, 65 red
    _g([[OVERLAP, AREA, OWNER, DUP], [OVERLAP], [DUP]], (OVERLAP, 0, 1, _OVERLAPS), (DUP, 0, 2)),   # 110 -> capped 100, 40, 20
    *_TRIPLE,
    _g([[INVALID]]),
    *_TRIPLE,
]
FILLER = [_g([[OVERLAP], [OVERLAP]], (OVERLAP, 0, 1, _OVERLAPS)), _g([[ZONE]]), _g([[AREA]]), _g([[OWNER]]),
          _g([[DUP], [DUP]], (DUP, 0, 1)), _g([[INVALID]]), _g([[TAX]]), _g([[MISSING]])]


def _to_lonlat(x, y):
    """Metres east/north of the origin -> (lon, lat), using WGS84 degree lengths."""
    phi = math.radians(ORIGIN_LAT)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return ORIGIN_LON + x / m_lon, ORIGIN_LAT + y / m_lat


def _wkt(poly):
    ring = Polygon([_to_lonlat(x, y) for x, y in poly.exterior.coords])
    return to_wkt(ring, rounding_precision=8)


def _rand_date(rng, start, end):
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _owner(rng):
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def _different_owner(rng, other):
    first, last = other.split()
    while True:
        first2, last2 = _owner(rng).split()
        if first2 != first and last2 != last:
            return f"{first2} {last2}"


def _make_plan(rng, n, rate):
    """Decide which plots get which problems. Returns (problems, links):
    problems = {plot index: set of problem types}, links = [(problem, anchor, partner, relation)]."""
    target = min(n, round(n * rate))
    pool = list(range(n))
    rng.shuffle(pool)
    problems, links = {}, []
    left = target
    for group in itertools.chain(DESIGNED, itertools.cycle(FILLER)):
        if left == 0:
            break
        size = len(group["plots"])
        if size > left:
            continue                                   # a group that no longer fits is skipped
        members = [pool.pop() for _ in range(size)]
        for index, plot_problems in zip(members, group["plots"]):
            problems[index] = set(plot_problems)
        for link in group["links"]:
            relation = link[3] if len(link) > 3 else None
            links.append((link[0], members[link[1]], members[link[2]], relation))
        left -= size
    return problems, links


def generate(plots=100, problem_rate=0.48, seed=42):
    rng = random.Random(seed)
    cols = math.ceil(math.sqrt(plots))
    problems, links = _make_plan(rng, plots, problem_rate)

    ulpins = [f"MH{(i // 20) + 1:04d}{i + 1:08d}" for i in range(plots)]
    villages = [VILLAGES[(i // 20) % len(VILLAGES)] for i in range(plots)]
    survey = [f"{100 + i}/{rng.randint(1, 9)}" for i in range(plots)]  # unique per plot
    missing_counter = 0

    rows = {"plots": [], "ror_records": [], "registrations": [], "tax_records": [],
            "zones": [], "building_snapshots": [], "users": [], "audit_log": []}
    shapes = {}   # index -> metric shapely polygon (the plot as intended)
    truth, details = {}, {}

    # Two clean plots that only TOUCH along an edge (no shared area). They must stay clean.
    clean_pool = sorted(i for i in range(plots) if i not in problems)
    touching = tuple(rng.sample(clean_pool, 2)) if plots >= 20 and len(clean_pool) >= 2 else None

    # What each plot is to the others, for the details in the truth file.
    relation_of = {}
    for ctype, a, b, relation in links:
        if ctype == OVERLAP:
            relation_of.setdefault(a, {}).update(overlap_partner=ulpins[b],
                                                 overlap_relation="contains" if relation == "inside" else "overlaps")
            relation_of.setdefault(b, {}).update(overlap_partner=ulpins[a],
                                                 overlap_relation="inside" if relation == "inside" else "overlaps")
        if ctype == DUP:
            relation_of.setdefault(a, {})["dup_partner"] = ulpins[b]
            relation_of.setdefault(b, {})["dup_partner"] = ulpins[a]
    overlap_anchor = {a for ctype, a, b, rel in links if ctype == OVERLAP and rel != "inside"}

    # Pass 1: geometry (every plot consumes the same random draws, in index order)
    for i in range(plots):
        col, row = i % cols, i // cols
        compact = i in overlap_anchor or (touching is not None and i == touching[0])
        top = 40 if touching is not None and i == touching[0] else 50   # touching plots stay narrow enough for their cell
        w, h = rng.uniform(30, top), rng.uniform(30, top)
        ox = rng.uniform(10, 30 if compact else 60)
        oy = rng.uniform(10, 30 if compact else 60)
        shapes[i] = box(col * CELL + ox, row * CELL + oy, col * CELL + ox + w, row * CELL + oy + h)

    # Linked plots: an overlapping partner is the anchor moved partway sideways; an "inside" partner is a smaller plot
    # in the middle of the anchor; a duplicate partner copies the anchor's village and survey number.
    for ctype, a, b, relation in links:
        x0, y0, x1, y1 = shapes[a].bounds
        if ctype == OVERLAP and relation == "inside":
            shapes[b] = box(x0 + 0.3 * (x1 - x0), y0 + 0.3 * (y1 - y0), x0 + 0.7 * (x1 - x0), y0 + 0.7 * (y1 - y0))
        elif ctype == OVERLAP:
            shapes[b] = translate(shapes[a], xoff=(x1 - x0) * 0.5, yoff=(y1 - y0) * 0.3)
        elif ctype == DUP:
            villages[b] = villages[a]
            survey[b] = survey[a]
    if touching is not None:
        x0, y0, x1, y1 = shapes[touching[0]].bounds
        shapes[touching[1]] = box(x1, y0, x1 + (x1 - x0), y1)     # shares the whole right edge, no shared area

    # Pass 2: records
    clean = [i for i in clean_pool if touching is None or i not in touching]
    decoy_idx = sorted(rng.sample(clean, min(len(DECOY_PAIRS), len(clean))))
    decoy_by_idx = dict(zip(decoy_idx, DECOY_PAIRS))
    decoys = [{"ulpin": ulpins[i], "ror_owner": p[0], "registration_owner": p[1]}
              for i, p in decoy_by_idx.items()]

    for i in range(plots):
        mine = problems.get(i, set())
        shape = shapes[i]
        real_area = shape.area  # square metres (the shape is in metres)
        if INVALID in mine:
            x0, y0, x1, y1 = shape.bounds
            drawn = Polygon([(x0, y0), (x1, y1), (x1, y0), (x0, y1), (x0, y0)])  # bow-tie
        else:
            drawn = shape
        rows["plots"].append({"ulpin": ulpins[i], "wkt": _wkt(drawn), "village": villages[i],
                              "land_use": rng.choice(LAND_USES), "survey_no": survey[i]})

        recorded = real_area * (1 + rng.uniform(-0.02, 0.02))
        if AREA in mine:
            recorded = real_area * (1 + rng.choice([1, -1]) * rng.uniform(0.15, 0.30))
        ror_owner = reg_owner = _owner(rng)
        if i in decoy_by_idx:
            ror_owner, reg_owner = decoy_by_idx[i]
        if OWNER in mine:
            reg_owner = _different_owner(rng, ror_owner)
        reg_date = _rand_date(rng, date(2005, 1, 1), date(2024, 12, 31))
        if TAX in mine:
            paid = _rand_date(rng, date(2021, 1, 1), date(2023, 6, 30))  # > 2 years before ref
        else:
            paid = _rand_date(rng, date(2025, 1, 1), date(2026, 12, 31))

        info = dict(relation_of.get(i, {}))
        skip = None
        if MISSING in mine:
            # Never remove a record that another planted problem on the same plot needs.
            needed = set()
            if OWNER in mine:
                needed |= {"ror_records", "registrations"}
            if AREA in mine:
                needed.add("ror_records")
            if TAX in mine:
                needed.add("tax_records")
            choices = [t for t in MISSING_TABLES if t not in needed]
            skip = choices[missing_counter % len(choices)]
            missing_counter += 1
            info["missing_table"] = skip
        if skip != "ror_records":
            rows["ror_records"].append({"ulpin": ulpins[i], "owner_name": ror_owner,
                                        "recorded_area_sqm": round(recorded, 2)})
        if skip != "registrations":
            rows["registrations"].append({"ulpin": ulpins[i], "owner_name": reg_owner,
                                          "registered_on": reg_date.isoformat()})
        if skip != "tax_records":
            rows["tax_records"].append({"ulpin": ulpins[i], "paid_until": paid.isoformat()})

        if ZONE in mine:
            x0, y0, x1, y1 = shape.bounds
            if i in overlap_anchor:
                # the anchor's overlapping partner sits to the right, so its zone goes on the left
                frac = rng.uniform(0.3, 0.45)
                zone = box(x0 - 8, y0 - 8, x0 + (x1 - x0) * frac, y1 + 8)
            else:
                frac = rng.uniform(0.4, 0.7)  # share of the plot inside the zone
                zone = box(x1 - (x1 - x0) * frac, y0 - 8, x1 + 8, y1 + 8)   # stays inside the plot's own cell
            rows["zones"].append({"zone_type": rng.choice(ZONE_TYPES), "wkt": _wkt(zone)})
            info["zone_fraction"] = round(frac, 3)

        if mine:
            truth[ulpins[i]] = [t for t in CONFLICT_TYPES if t in mine]
        if info:
            details[ulpins[i]] = info

    return {
        "rows": rows,
        "truth": {
            "seed": seed, "plots": plots, "problem_rate": problem_rate,
            "reference_date": REFERENCE_DATE.isoformat(),
            "conflicts": truth, "details": details, "decoys": decoys,
            # two clean plots that only touch along an edge: the overlap check must NOT flag them
            "touching_pairs": [[ulpins[touching[0]], ulpins[touching[1]]]] if touching else [],
        },
    }


def write_truth(data, path=TRUTH_PATH):
    Path(path).write_text(json.dumps(data["truth"], indent=2) + "\n", encoding="utf-8")


def _read_env():
    env = dict(os.environ)
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def connect():
    import psycopg
    env = _read_env()
    return psycopg.connect(
        host=env.get("POSTGRES_HOST", "localhost"), port=env.get("POSTGRES_PORT", "5432"),
        user=env.get("POSTGRES_USER", "landstack"), password=env["POSTGRES_PASSWORD"],
        dbname=env.get("POSTGRES_DB", "landstack"))


def load(data):
    r = data["rows"]
    with connect() as conn, conn.cursor() as cur:
        # Clears plots and everything pointing at them (audit_log); users is left alone.
        cur.execute("TRUNCATE plots, zones, building_snapshots RESTART IDENTITY CASCADE")
        cur.executemany(
            "INSERT INTO plots (ulpin, geom, village, land_use, survey_no) "
            "VALUES (%(ulpin)s, ST_GeomFromText(%(wkt)s, 4326), %(village)s, "
            "%(land_use)s, %(survey_no)s)", r["plots"])
        cur.executemany(
            "INSERT INTO ror_records (ulpin, owner_name, recorded_area_sqm) "
            "VALUES (%(ulpin)s, %(owner_name)s, %(recorded_area_sqm)s)", r["ror_records"])
        cur.executemany(
            "INSERT INTO registrations (ulpin, owner_name, registered_on) "
            "VALUES (%(ulpin)s, %(owner_name)s, %(registered_on)s)", r["registrations"])
        cur.executemany(
            "INSERT INTO tax_records (ulpin, paid_until) VALUES (%(ulpin)s, %(paid_until)s)",
            r["tax_records"])
        cur.executemany(
            "INSERT INTO zones (zone_type, geom) "
            "VALUES (%(zone_type)s, ST_GeomFromText(%(wkt)s, 4326))", r["zones"])


def main():
    ap = argparse.ArgumentParser(description="Seed LandStack with fake land data.")
    ap.add_argument("--plots", type=int, default=100)
    ap.add_argument("--problem-rate", type=float, default=0.48)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    data = generate(a.plots, a.problem_rate, a.seed)
    write_truth(data)
    load(data)
    print(f"Seeded {a.plots} plots (seed={a.seed}); wrote {TRUTH_PATH}")


if __name__ == "__main__":
    main()
