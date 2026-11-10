"""Phase 9: the feature function (no database, no model files)."""
import math
from datetime import date

import pytest
from shapely.geometry import Polygon, box

from backend.app import config
from ml import features


def lonlat_box(x0, y0, x1, y1):
    """A rectangle given in METRES, placed in lon/lat the way the database stores shapes."""
    return box(x0 / features._M_LON, y0 / features._M_LAT, x1 / features._M_LON, y1 / features._M_LAT)


def plot(ulpin, geom, village="Hinjewadi", recorded=None, registered=date(2015, 1, 1), paid=date(2025, 6, 1)):
    return {"ulpin": ulpin, "village": village, "geom": geom, "recorded_area_sqm": recorded,
            "registered_on": registered, "paid_until": paid}


def one(p, others=(), zones=()):
    ctx = features.Context([p, *others], list(zones))
    return features.plot_features(p, ctx)


def test_feature_list_matches_what_the_function_returns():
    row = one(plot("A", lonlat_box(0, 0, 40, 30)))
    assert list(row) == features.FEATURE_NAMES
    assert all(isinstance(v, float) and math.isfinite(v) for v in row.values())


def test_a_known_rectangle_gives_hand_worked_numbers():
    row = one(plot("A", lonlat_box(0, 0, 40, 30), recorded=1260.0))
    assert row["area_sqm"] == pytest.approx(1200, rel=0.001)
    assert row["perimeter_m"] == pytest.approx(140, rel=0.001)
    assert row["compactness"] == pytest.approx(4 * math.pi * 1200 / 140 ** 2, rel=0.002)
    assert row["aspect_ratio"] == pytest.approx(40 / 30, rel=0.002)
    assert row["vertex_count"] == 4
    assert row["recorded_over_mapped"] == pytest.approx(1.05, rel=0.002)
    assert row["years_since_tax_paid"] == pytest.approx((config.REFERENCE_DATE - date(2025, 6, 1)).days / 365.25)
    assert row["years_since_registration"] == pytest.approx((config.REFERENCE_DATE - date(2015, 1, 1)).days / 365.25)
    assert row["invalid_shape"] == 0.0
    assert row["area_vs_village_median"] == 1.0       # the only plot in its village


def test_deterministic():
    p = plot("A", lonlat_box(0, 0, 40, 30), recorded=1000.0)
    other = plot("B", lonlat_box(20, 10, 60, 40))
    assert one(p, [other]) == one(p, [other])


def test_neighbours_count_overlaps_and_touches_but_not_far_plots():
    a = plot("A", lonlat_box(0, 0, 40, 30))
    overlapping = plot("B", lonlat_box(20, 10, 60, 40))
    touching = plot("C", lonlat_box(-40, 0, 0, 30))          # shares the left edge, no shared area
    far = plot("D", lonlat_box(500, 500, 540, 530))
    assert one(a, [overlapping, touching, far])["neighbour_count"] == 2
    assert one(a, [far])["neighbour_count"] == 0


def test_zone_distance():
    a = plot("A", lonlat_box(0, 0, 40, 30))
    assert one(a, zones=[lonlat_box(140, 0, 200, 30)])["zone_distance_m"] == pytest.approx(100, rel=0.01)
    assert one(a, zones=[lonlat_box(30, 0, 90, 30)])["zone_distance_m"] == 0.0         # overlapping a zone
    assert one(a)["zone_distance_m"] == features.FALLBACK_ZONE_DISTANCE_M              # no zones at all


def test_area_compared_with_the_village_median():
    plots = [plot(f"P{i}", lonlat_box(i * 100, 0, i * 100 + s, s)) for i, s in enumerate([30, 30, 30, 60])]
    ctx = features.Context(plots, [])
    big = features.plot_features(plots[3], ctx)
    assert big["area_vs_village_median"] == pytest.approx(3600 / 900, rel=0.01)


def test_invalid_shape_gets_safe_values_and_a_flag_instead_of_a_crash():
    x0, y0, x1, y1 = 0 / features._M_LON, 0, 40 / features._M_LON, 30 / features._M_LAT
    bow_tie = Polygon([(x0, y0), (x1, y1), (x1, y0), (x0, y1), (x0, y0)])
    assert not bow_tie.is_valid
    row = one(plot("A", bow_tie, recorded=900.0))
    assert row["invalid_shape"] == 1.0
    assert all(math.isfinite(v) for v in row.values())
    assert row["area_sqm"] > 0                        # measured on the convex hull


def test_empty_shape_and_empty_records_do_not_crash():
    p = {"ulpin": "A", "village": None, "geom": Polygon(), "recorded_area_sqm": None,
         "registered_on": None, "paid_until": None}
    row = one(p)
    assert row["invalid_shape"] == 1.0 and row["area_sqm"] == 0.0 and row["compactness"] == 0.0
    assert row["recorded_over_mapped"] == features.FALLBACK_RATIO
    assert row["years_since_tax_paid"] == features.FALLBACK_TAX_YEARS
    assert row["years_since_registration"] == features.FALLBACK_REGISTRATION_YEARS
    assert all(math.isfinite(v) for v in row.values())
    assert one({**p, "geom": None})["invalid_shape"] == 1.0           # no geometry at all


def test_a_plot_with_a_shape_but_no_records_is_fine():
    p = plot("A", lonlat_box(0, 0, 40, 30), recorded=None, registered=None, paid=None)
    row = one(p)
    assert row["recorded_over_mapped"] == 1.0 and row["invalid_shape"] == 0.0


def test_features_for_all_matches_plot_features():
    plots = [plot("A", lonlat_box(0, 0, 40, 30), recorded=1000.0), plot("B", lonlat_box(30, 10, 70, 40))]
    ulpins, rows = features.features_for_all(plots, [])
    ctx = features.Context(plots, [])
    assert ulpins == ["A", "B"]
    assert rows[1] == [features.plot_features(plots[1], ctx)[n] for n in features.FEATURE_NAMES]
