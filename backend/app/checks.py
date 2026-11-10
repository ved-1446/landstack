"""The nine conflict checks. Every check is visible raw PostGIS SQL plus a few lines of Python.

Each check_* function takes an open psycopg connection and returns a list of findings:
    {"ulpin": ..., "type": ..., "points": ..., "evidence": "plain facts with real numbers"}

Rules used throughout:
- Areas are in square metres, measured with a geography cast (geom::geography).
- Plots with an invalid shape (ST_IsValid is false) are SKIPPED by the overlap, zone and
  area checks, because their area and intersections are meaningless. We do not repair them;
  the invalid_boundary check reports them instead.
"""
import json
from collections import Counter
from pathlib import Path

from . import config, names

TRUTH_PATH = Path(__file__).resolve().parents[2] / "db" / "planted_truth.json"


def _finding(ulpin, ctype, evidence):
    return {"ulpin": ulpin, "type": ctype, "points": config.POINTS[ctype], "evidence": evidence}


def check_boundary_overlap(conn):
    # ST_Intersects is true for ANY shared ground: a partial overlap, one plot completely inside another, two
    # identical plots, and also two plots that merely touch along an edge. (ST_Overlaps would miss "inside" and
    # "identical".) So we measure the shared piece in square metres and ignore anything below MIN_OVERLAP_SQM:
    # a shared edge is a line with 0 sq m, which is how touching plots stay out.
    # Joining a to b and b to a gives BOTH plots a row, so both plots get a finding.
    sql = """
        WITH pairs AS (
            SELECT a.ulpin, b.ulpin AS other, a.geom AS a_geom, b.geom AS b_geom,
                   ST_Area(ST_Intersection(a.geom, b.geom)::geography) AS overlap_sqm
            FROM plots a
            JOIN plots b ON a.ulpin <> b.ulpin AND ST_Intersects(a.geom, b.geom)
            WHERE ST_IsValid(a.geom) AND ST_IsValid(b.geom)
        )
        SELECT ulpin, other, overlap_sqm,
               ST_Area(a_geom::geography) AS area_sqm,
               ST_Equals(a_geom, b_geom)  AS identical,
               ST_Covers(b_geom, a_geom)  AS inside_other,      -- this plot lies completely inside the other
               ST_Covers(a_geom, b_geom)  AS contains_other     -- the other plot lies completely inside this one
        FROM pairs
        WHERE overlap_sqm >= %s
        ORDER BY ulpin, other
    """
    parts = {}
    for ulpin, other, overlap, area, identical, inside, contains in conn.execute(
            sql, (config.MIN_OVERLAP_SQM,)).fetchall():
        if identical:
            text = f"has exactly the same boundary as plot {other} ({overlap:,.0f} sq m)"
        elif inside:
            text = f"lies completely inside plot {other} ({overlap:,.0f} sq m, all of this plot)"
        elif contains:
            text = f"plot {other} lies completely inside this plot ({overlap:,.0f} sq m, {overlap / area:.0%} of this plot)"
        else:
            text = f"overlaps plot {other} by {overlap:,.0f} sq m ({overlap / area:.0%} of this plot)"
        parts.setdefault(ulpin, []).append(text)
    return [_finding(u, "boundary_overlap", "; ".join(p)) for u, p in parts.items()]


def check_restricted_zone_clash(conn):
    # All zones touching a plot are merged (ST_Union) first, so two zones covering the same
    # corner are not counted twice.
    sql = """
        WITH hits AS (
            SELECT p.ulpin,
                   ST_Union(z.geom) AS zone_geom,
                   string_agg(DISTINCT z.zone_type, ', ') AS zone_types
            FROM plots p
            JOIN zones z ON ST_Intersects(p.geom, z.geom)
            WHERE ST_IsValid(p.geom)
            GROUP BY p.ulpin
        )
        SELECT h.ulpin, h.zone_types,
               ST_Area(ST_Intersection(p.geom, h.zone_geom)::geography) AS inside_sqm,
               ST_Area(p.geom::geography) AS area_sqm
        FROM hits h
        JOIN plots p USING (ulpin)
        WHERE ST_Area(ST_Intersection(p.geom, h.zone_geom)::geography)
              / ST_Area(p.geom::geography) > %s
        ORDER BY h.ulpin
    """
    out = []
    for ulpin, zone_types, inside, area in conn.execute(sql, (config.ZONE_SHARE_LIMIT,)):
        out.append(_finding(
            ulpin, "restricted_zone_clash",
            f"{inside:,.0f} sq m of {area:,.0f} sq m ({inside / area:.0%}) lies inside "
            f"restricted zone: {zone_types}; limit is {config.ZONE_SHARE_LIMIT:.0%}"))
    return out


def check_area_mismatch(conn):
    sql = """
        SELECT p.ulpin, r.recorded_area_sqm,
               ST_Area(p.geom::geography) AS real_sqm
        FROM plots p
        JOIN ror_records r USING (ulpin)
        WHERE ST_IsValid(p.geom)
          AND abs(r.recorded_area_sqm - ST_Area(p.geom::geography))
              / ST_Area(p.geom::geography) > %s
        ORDER BY p.ulpin
    """
    out = []
    for ulpin, recorded, real in conn.execute(sql, (config.AREA_MISMATCH_LIMIT,)):
        recorded = float(recorded)
        out.append(_finding(
            ulpin, "area_mismatch",
            f"record says {recorded:,.0f} sq m but the mapped plot is {real:,.0f} sq m "
            f"({(recorded - real) / real:+.0%}); limit is {config.AREA_MISMATCH_LIMIT:.0%}"))
    return out


def check_owner_mismatch(conn):
    sql = """
        SELECT r.ulpin, r.owner_name, g.owner_name
        FROM ror_records r
        JOIN registrations g USING (ulpin)
        ORDER BY r.ulpin
    """
    out, seen = [], set()
    for ulpin, ror_owner, reg_owner in conn.execute(sql).fetchall():
        same, score = names.same_person(ror_owner, reg_owner)
        if not same and ulpin not in seen:
            seen.add(ulpin)
            out.append(_finding(
                ulpin, "owner_mismatch",
                f"record owner '{ror_owner}' vs registration owner '{reg_owner}'; "
                f"name similarity {score:.2f} (needs {config.NAME_MATCH_THRESHOLD:.2f})"))
    return out


def check_duplicate_survey_no(conn):
    sql = """
        SELECT village, survey_no, array_agg(ulpin ORDER BY ulpin) AS ulpins
        FROM plots
        GROUP BY village, survey_no
        HAVING count(*) > 1
        ORDER BY village, survey_no
    """
    out = []
    for village, survey_no, ulpins in conn.execute(sql).fetchall():
        for u in ulpins:
            others = ", ".join(x for x in ulpins if x != u)
            out.append(_finding(
                u, "duplicate_survey_no",
                f"survey number {survey_no} in {village} is also used by plot {others}"))
    return out


def check_invalid_boundary(conn):
    sql = """
        SELECT ulpin, ST_IsValidReason(geom)
        FROM plots
        WHERE NOT ST_IsValid(geom)
        ORDER BY ulpin
    """
    return [_finding(u, "invalid_boundary", f"boundary shape is invalid: {reason}")
            for u, reason in conn.execute(sql).fetchall()]


def check_tax_overdue(conn):
    # Latest paid-until per plot, compared with REFERENCE_DATE minus 2 years.
    sql = """
        SELECT ulpin, max(paid_until) AS paid_until
        FROM tax_records
        GROUP BY ulpin
        HAVING max(paid_until) < (%s::date - make_interval(years => %s))
        ORDER BY ulpin
    """
    out = []
    for ulpin, paid_until in conn.execute(
            sql, (config.REFERENCE_DATE, config.TAX_OVERDUE_YEARS)).fetchall():
        days = (config.REFERENCE_DATE - paid_until).days
        out.append(_finding(
            ulpin, "tax_overdue",
            f"tax paid only until {paid_until}, which is {days} days "
            f"({days / 365.25:.1f} years) before {config.REFERENCE_DATE}; "
            f"limit is {config.TAX_OVERDUE_YEARS} years"))
    return out


# SIMULATED change detection with two snapshots of building outlines, T0 (earlier) and T1 (later); there is no real
# satellite or imagery data. Per plot: merge all T1 footprints (ST_Union), merge all T0 footprints, and SUBTRACT T0
# from T1 (ST_Difference). What is left is ground that has a building in T1 but had none in T0: the new built-up
# area. A building in both snapshots subtracts to nothing, a building that disappeared in T1 is not in T1 at all, and
# a footprint shifted by a metre or two leaves only a thin sliver. The area is measured in square metres (geography
# cast). A plot with a T1 footprint but no T0 footprints at all has everything new (COALESCE gives an empty T0).
# Plots with an invalid shape are skipped, like in the other geometry checks.
# The map's footprints (construction_footprints below) use this SAME text, so the map can never disagree with the check.
_NEW_BUILT_SQL = """
    WITH t0 AS (
        SELECT ulpin, ST_Union(footprint) AS geom FROM building_snapshots WHERE snapshot = 'T0' GROUP BY ulpin
    ), t1 AS (
        SELECT ulpin, ST_Union(footprint) AS geom FROM building_snapshots WHERE snapshot = 'T1' GROUP BY ulpin
    ), new_built AS (
        SELECT t1.ulpin,
               ST_Difference(t1.geom, COALESCE(t0.geom, ST_GeomFromText('POLYGON EMPTY', 4326))) AS geom,
               ST_Area(ST_Difference(t1.geom,
                       COALESCE(t0.geom, ST_GeomFromText('POLYGON EMPTY', 4326)))::geography) AS new_sqm
        FROM t1
        JOIN plots p ON p.ulpin = t1.ulpin
        LEFT JOIN t0 ON t0.ulpin = t1.ulpin
        WHERE ST_IsValid(p.geom)
    )
"""


def check_unrecorded_construction(conn):
    # Flag the plot only if the new built area is at least MIN_NEW_BUILT_SQM, so slivers (survey jitter) stay below the line.
    sql = _NEW_BUILT_SQL + "SELECT ulpin, new_sqm FROM new_built WHERE new_sqm >= %s ORDER BY ulpin"
    return [_finding(ulpin, "unrecorded_construction",
                     f"SIMULATED: about {new_sqm:,.0f} sq m of new building appeared between T0 and T1 that is not "
                     f"in the records; limit is {config.MIN_NEW_BUILT_SQM:,.0f} sq m (no real imagery is used)")
            for ulpin, new_sqm in conn.execute(sql, (config.MIN_NEW_BUILT_SQM,)).fetchall()]


def construction_footprints(conn, ulpins=None):
    """The new-building outlines behind the alert (SIMULATED), one row per building piece, for the map.
    Only plots the check flags (so no jitter slivers); `ulpins` (a list) limits them to those plots, for citizens.
    Returns [{"ulpin", "new_sqm" (for the whole plot), "piece_sqm", "geometry" (GeoJSON Polygon)}]."""
    sql = _NEW_BUILT_SQL + """
        SELECT nb.ulpin, nb.new_sqm, ST_Area(d.geom::geography) AS piece_sqm, ST_AsGeoJSON(d.geom)::json
        FROM new_built nb
        CROSS JOIN LATERAL ST_Dump(nb.geom) AS d
        WHERE nb.new_sqm >= %(minimum)s
          AND (%(ulpins)s::text[] IS NULL OR nb.ulpin = ANY(%(ulpins)s::text[]))
          AND ST_Area(d.geom::geography) >= 1
        ORDER BY nb.ulpin, piece_sqm DESC
    """
    return [{"ulpin": u, "new_sqm": new, "piece_sqm": piece, "geometry": geometry}
            for u, new, piece, geometry in conn.execute(
                sql, {"minimum": config.MIN_NEW_BUILT_SQM, "ulpins": ulpins}).fetchall()]


# Fixed table names (never user input), so building the SQL text here is safe.
_RECORD_TABLES = [("ror_records", "RoR record"), ("registrations", "registration"),
                  ("tax_records", "tax record")]


def check_missing_record(conn):
    out = []
    for table, label in _RECORD_TABLES:
        sql = f"""
            SELECT p.ulpin FROM plots p
            WHERE NOT EXISTS (SELECT 1 FROM {table} t WHERE t.ulpin = p.ulpin)
            ORDER BY p.ulpin
        """
        out += [_finding(u, "missing_record", f"no {label} found for this plot ({table} is empty)")
                for (u,) in conn.execute(sql).fetchall()]
    return out


ALL_CHECKS = {
    "boundary_overlap": check_boundary_overlap,
    "restricted_zone_clash": check_restricted_zone_clash,
    "area_mismatch": check_area_mismatch,
    "owner_mismatch": check_owner_mismatch,
    "duplicate_survey_no": check_duplicate_survey_no,
    "invalid_boundary": check_invalid_boundary,
    "tax_overdue": check_tax_overdue,
    "missing_record": check_missing_record,
    "unrecorded_construction": check_unrecorded_construction,
}


def run_checks(conn):
    """Run every check and return all findings in one list."""
    findings = []
    for check in ALL_CHECKS.values():
        findings += check(conn)
    return findings


def main():
    from . import db, scoring  # imported here so `python -m` does not load scoring twice

    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    truth_counts = Counter(t for types in truth["conflicts"].values() for t in types)
    with db.connect() as conn:
        results = scoring.run_all(conn)

    flagged = {t: set() for t in ALL_CHECKS}
    for res in results.values():
        for f in res["findings"]:
            flagged[f["type"]].add(f["ulpin"])

    print(f"{'conflict type':<24}{'flagged':>8}{'planted':>9}")
    for t in ALL_CHECKS:
        print(f"{t:<24}{len(flagged[t]):>8}{truth_counts.get(t, 0):>9}")

    bands = Counter(r["band"] for r in results.values())
    print("\nBands:", ", ".join(f"{b} {bands.get(b, 0)}" for b in ("green", "amber", "red")))

    print("\nTop 3 plots by score:")
    top = sorted(results.items(), key=lambda kv: (-kv[1]["score"], kv[0]))[:3]
    for ulpin, res in top:
        print(f"  {ulpin}  score {res['score']}  ({res['band']})")
        for f in res["findings"]:
            print(f"    - {f['type']} (+{f['points']}): {f['evidence']}")


if __name__ == "__main__":
    main()
