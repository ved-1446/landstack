"""Seed LandStack with deterministic fake land data near Pune.

Usage: python db/seed.py [--plots 100] [--problem-rate 0.4] [--seed 42]

generate() is pure (no database): the same arguments always return the same data.
main() loads that data into PostgreSQL and writes db/planted_truth.json.
"""
import argparse
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

# (conflict type, plots it uses). Cycled until the problem quota is filled.
CYCLE = [
    ("boundary_overlap", 2), ("restricted_zone_clash", 1), ("area_mismatch", 1),
    ("owner_mismatch", 1), ("duplicate_survey_no", 2), ("invalid_boundary", 1),
    ("tax_overdue", 1), ("missing_record", 1),
]
CONFLICT_TYPES = [t for t, _ in CYCLE]
MISSING_TABLES = ["ror_records", "registrations", "tax_records"]


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


def _assign_roles(rng, n, rate):
    """Pick which plots get which planted problem. Returns (roles, partners)."""
    target = min(n, round(n * rate))
    pool = list(range(n))
    rng.shuffle(pool)
    roles, partners = {}, {}
    left = target
    while left > 0:
        for ctype, size in CYCLE:
            if size > left:
                continue
            members = [pool.pop() for _ in range(size)]
            for m in members:
                roles[m] = ctype
            if size == 2:
                partners[members[0]], partners[members[1]] = members[1], members[0]
            left -= size
            if left == 0:
                break
    return roles, partners


def generate(plots=100, problem_rate=0.4, seed=42):
    rng = random.Random(seed)
    cols = math.ceil(math.sqrt(plots))
    roles, partners = _assign_roles(rng, plots, problem_rate)

    ulpins = [f"MH{(i // 20) + 1:04d}{i + 1:08d}" for i in range(plots)]
    villages = [VILLAGES[(i // 20) % len(VILLAGES)] for i in range(plots)]
    survey = [f"{100 + i}/{rng.randint(1, 9)}" for i in range(plots)]  # unique per plot
    missing_counter = 0

    rows = {"plots": [], "ror_records": [], "registrations": [], "tax_records": [],
            "zones": [], "building_snapshots": [], "users": [], "audit_log": []}
    shapes = {}   # index -> metric shapely polygon (the plot as intended)
    truth, details = {}, {}

    # Pass 1: geometry (every plot consumes the same random draws, in index order)
    for i in range(plots):
        col, row = i % cols, i // cols
        compact = roles.get(i) == "boundary_overlap"
        w, h = rng.uniform(30, 50), rng.uniform(30, 50)
        ox = rng.uniform(10, 30 if compact else 60)
        oy = rng.uniform(10, 30 if compact else 60)
        shapes[i] = box(col * CELL + ox, row * CELL + oy, col * CELL + ox + w, row * CELL + oy + h)

    # Pair partners: overlap B is A moved partway sideways; duplicate B copies A's survey no.
    for i, ctype in roles.items():
        j = partners.get(i)
        if j is None or i > j:
            continue
        if ctype == "boundary_overlap":
            x0, y0, x1, y1 = shapes[i].bounds
            shapes[j] = translate(shapes[i], xoff=(x1 - x0) * 0.5, yoff=(y1 - y0) * 0.3)
        if ctype == "duplicate_survey_no":
            villages[j] = villages[i]
            survey[j] = survey[i]

    # Pass 2: records
    clean = [i for i in range(plots) if i not in roles]
    decoy_idx = sorted(rng.sample(clean, min(len(DECOY_PAIRS), len(clean))))
    decoy_by_idx = dict(zip(decoy_idx, DECOY_PAIRS))
    decoys = [{"ulpin": ulpins[i], "ror_owner": p[0], "registration_owner": p[1]}
              for i, p in decoy_by_idx.items()]

    for i in range(plots):
        ctype = roles.get(i)
        shape = shapes[i]
        real_area = shape.area  # square metres (the shape is in metres)
        if ctype == "invalid_boundary":
            x0, y0, x1, y1 = shape.bounds
            drawn = Polygon([(x0, y0), (x1, y1), (x1, y0), (x0, y1), (x0, y0)])  # bow-tie
        else:
            drawn = shape
        rows["plots"].append({"ulpin": ulpins[i], "wkt": _wkt(drawn), "village": villages[i],
                              "land_use": rng.choice(LAND_USES), "survey_no": survey[i]})

        recorded = real_area * (1 + rng.uniform(-0.02, 0.02))
        if ctype == "area_mismatch":
            recorded = real_area * (1 + rng.choice([1, -1]) * rng.uniform(0.15, 0.30))
        ror_owner = reg_owner = _owner(rng)
        if i in decoy_by_idx:
            ror_owner, reg_owner = decoy_by_idx[i]
        if ctype == "owner_mismatch":
            reg_owner = _different_owner(rng, ror_owner)
        reg_date = _rand_date(rng, date(2005, 1, 1), date(2024, 12, 31))
        if ctype == "tax_overdue":
            paid = _rand_date(rng, date(2021, 1, 1), date(2023, 6, 30))  # > 2 years before ref
        else:
            paid = _rand_date(rng, date(2025, 1, 1), date(2026, 12, 31))

        skip = None
        if ctype == "missing_record":
            skip = MISSING_TABLES[missing_counter % 3]
            missing_counter += 1
            details[ulpins[i]] = {"missing_table": skip}
        if skip != "ror_records":
            rows["ror_records"].append({"ulpin": ulpins[i], "owner_name": ror_owner,
                                        "recorded_area_sqm": round(recorded, 2)})
        if skip != "registrations":
            rows["registrations"].append({"ulpin": ulpins[i], "owner_name": reg_owner,
                                          "registered_on": reg_date.isoformat()})
        if skip != "tax_records":
            rows["tax_records"].append({"ulpin": ulpins[i], "paid_until": paid.isoformat()})

        if ctype:
            truth[ulpins[i]] = [ctype]
        if i in partners:
            details[ulpins[i]] = {"partner": ulpins[partners[i]]}

        if ctype == "restricted_zone_clash":
            x0, y0, x1, y1 = shape.bounds
            frac = rng.uniform(0.4, 0.7)  # share of the plot inside the zone
            cut = x1 - (x1 - x0) * frac
            zone = box(cut, y0 - 8, x1 + 8, y1 + 8)  # stays inside the plot's own cell
            rows["zones"].append({"zone_type": rng.choice(ZONE_TYPES), "wkt": _wkt(zone)})
            details[ulpins[i]] = {"zone_fraction": round(frac, 3)}

    return {
        "rows": rows,
        "truth": {
            "seed": seed, "plots": plots, "problem_rate": problem_rate,
            "reference_date": REFERENCE_DATE.isoformat(),
            "conflicts": truth, "details": details, "decoys": decoys,
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
    ap.add_argument("--problem-rate", type=float, default=0.4)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    data = generate(a.plots, a.problem_rate, a.seed)
    write_truth(data)
    load(data)
    print(f"Seeded {a.plots} plots (seed={a.seed}); wrote {TRUTH_PATH}")


if __name__ == "__main__":
    main()
