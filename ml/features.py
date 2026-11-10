"""Turn a plot (its shape plus its records) into numbers.

ONE function, `plot_features`, is used for training AND for serving, so the two can never drift apart.
No database in here: callers hand in plain data (a shapely shape in lon/lat plus three record values).

Shapes arrive in lon/lat (degrees) like the database stores them. They are flattened to metres with a simple
local projection first (fine for one district: the error is far below a tenth of a percent), so that area,
length and distance mean square metres and metres.
"""
import math
from datetime import date

from shapely import STRtree
from shapely.affinity import scale
from shapely.geometry import Polygon

from backend.app import config

# The order of this list IS the model's input order. Change it and every saved model becomes invalid
# (the loader checks, and then serves "no model" instead of wrong answers).
FEATURE_NAMES = [
    "area_sqm",                 # mapped area, square metres
    "perimeter_m",              # length of the boundary, metres
    "compactness",              # 4*pi*area/perimeter^2: 1.0 = a circle, a square = 0.785, a thin strip -> 0
    "aspect_ratio",             # long side / short side of the smallest rotated rectangle around the plot
    "vertex_count",             # corners of the boundary
    "recorded_over_mapped",     # recorded area (land record) divided by mapped area; 1.0 = they agree
    "years_since_tax_paid",     # years between "tax paid until" and the reference date (negative = paid ahead)
    "years_since_registration",  # years between the registration date and the reference date
    "neighbour_count",          # how many other plots overlap or touch this one
    "zone_distance_m",          # metres to the nearest restricted zone (0 = inside or touching one)
    "area_vs_village_median",   # this plot's area / the median area of plots in its village
    "invalid_shape",            # 1 if the boundary is an invalid shape (crosses itself), else 0
]

# What a missing value turns into (a plot with no record is a conflict the checks already score; the model
# just needs a neutral number so it does not crash).
FALLBACK_RATIO = 1.0
FALLBACK_TAX_YEARS = 0.0
FALLBACK_REGISTRATION_YEARS = 10.0
FALLBACK_ZONE_DISTANCE_M = 5000.0      # also the cap: "far away" is all the same to the model
MAX_ASPECT = 100.0

_REF_LAT = 18.55    # the demo district (near Pune). Only used to turn degrees into metres.


def _metre_scale(lat=_REF_LAT):
    phi = math.radians(lat)
    m_lat = 111132.92 - 559.82 * math.cos(2 * phi) + 1.175 * math.cos(4 * phi)
    m_lon = 111412.84 * math.cos(phi) - 93.5 * math.cos(3 * phi)
    return m_lon, m_lat


_M_LON, _M_LAT = _metre_scale()


def to_metres(geom):
    """lon/lat shape -> shape in metres (a plain stretch; the origin does not matter for sizes and distances)."""
    return scale(geom, xfact=_M_LON, yfact=_M_LAT, origin=(0, 0))


def _vertex_count(geom):
    if geom is None or geom.is_empty or geom.geom_type != "Polygon":
        return 0
    return max(len(geom.exterior.coords) - 1, 0)


def _usable(geom):
    """(shape used for the measurements, is_invalid). An invalid or missing shape is replaced by its convex hull
    (or an empty polygon), so nothing crashes and the flag tells the model it happened."""
    if geom is None or geom.is_empty:
        return Polygon(), True
    metric = to_metres(geom)
    if metric.is_valid:
        return metric, False
    return metric.convex_hull, True


def _aspect(shape):
    if shape.is_empty or shape.area == 0:
        return 1.0
    rect = shape.minimum_rotated_rectangle
    if rect.geom_type != "Polygon":
        return MAX_ASPECT
    xs, ys = rect.exterior.coords.xy
    side_a = math.hypot(xs[1] - xs[0], ys[1] - ys[0])
    side_b = math.hypot(xs[2] - xs[1], ys[2] - ys[1])
    short, long_ = sorted((side_a, side_b))
    return min(long_ / short, MAX_ASPECT) if short > 0 else MAX_ASPECT


def _years_between(reference, earlier):
    return (reference - earlier).days / 365.25


class Context:
    """What a plot needs to know about the OTHER plots: who its neighbours are, the zones, the village medians.
    Build it once for a whole set of plots, then call plot_features for each one."""

    def __init__(self, plots, zones):
        self.shapes = {}
        for p in plots:
            self.shapes[p["ulpin"]], _ = _usable(p.get("geom"))
        self._ids = list(self.shapes)
        self._tree = STRtree([self.shapes[u] for u in self._ids])

        zone_shapes = []
        for z in zones:
            if z is not None and not z.is_empty:
                metric = to_metres(z)
                zone_shapes.append(metric if metric.is_valid else metric.convex_hull)
        self._zones = zone_shapes
        self._zone_tree = STRtree(zone_shapes) if zone_shapes else None

        by_village = {}
        for p in plots:
            area = self.shapes[p["ulpin"]].area
            if area > 0:
                by_village.setdefault(p.get("village"), []).append(area)
        self.village_median = {v: _median(a) for v, a in by_village.items()}
        self.overall_median = _median([a for areas in by_village.values() for a in areas]) or 1.0

    def neighbour_count(self, ulpin):
        shape = self.shapes[ulpin]
        if shape.is_empty:
            return 0
        hits = self._tree.query(shape, predicate="intersects")
        return sum(1 for i in hits if self._ids[i] != ulpin)

    def zone_distance(self, ulpin):
        shape = self.shapes[ulpin]
        if shape.is_empty or self._zone_tree is None:
            return FALLBACK_ZONE_DISTANCE_M
        index = self._zone_tree.nearest(shape)
        return min(shape.distance(self._zones[index]), FALLBACK_ZONE_DISTANCE_M)


def _median(values):
    values = sorted(values)
    if not values:
        return None
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def plot_features(plot, context, reference=config.REFERENCE_DATE):
    """The numbers for ONE plot, as {feature name: float}, in the order of FEATURE_NAMES.

    plot = {"ulpin", "village", "geom" (shapely, lon/lat), "recorded_area_sqm", "registered_on", "paid_until"}
    (any record value may be None: that plot simply has no such record).
    Deterministic, no randomness, no database. An invalid or missing shape gets safe fallback values and
    invalid_shape = 1 instead of an error."""
    shape, invalid = _usable(plot.get("geom"))
    area = shape.area
    perimeter = shape.length
    compactness = 4 * math.pi * area / perimeter ** 2 if perimeter > 0 else 0.0

    recorded = plot.get("recorded_area_sqm")
    ratio = float(recorded) / area if recorded is not None and area > 0 else FALLBACK_RATIO

    paid = plot.get("paid_until")
    registered = plot.get("registered_on")
    median = context.village_median.get(plot.get("village")) or context.overall_median

    values = {
        "area_sqm": area,
        "perimeter_m": perimeter,
        "compactness": compactness,
        "aspect_ratio": _aspect(shape),
        "vertex_count": _vertex_count(plot.get("geom")),
        "recorded_over_mapped": ratio,
        "years_since_tax_paid": _years_between(reference, paid) if isinstance(paid, date) else FALLBACK_TAX_YEARS,
        "years_since_registration": (_years_between(reference, registered) if isinstance(registered, date)
                                     else FALLBACK_REGISTRATION_YEARS),
        "neighbour_count": context.neighbour_count(plot["ulpin"]),
        "zone_distance_m": context.zone_distance(plot["ulpin"]),
        "area_vs_village_median": area / median if median else 1.0,
        "invalid_shape": 1.0 if invalid else 0.0,
    }
    return {name: float(values[name]) for name in FEATURE_NAMES}


def features_for_all(plots, zones, reference=config.REFERENCE_DATE):
    """Convenience for training and serving: the rows for every plot, as ([ulpin], [[numbers in FEATURE_NAMES order]])."""
    context = Context(plots, zones)
    ulpins = [p["ulpin"] for p in plots]
    rows = []
    for p in plots:
        values = plot_features(p, context, reference)
        rows.append([values[n] for n in FEATURE_NAMES])
    return ulpins, rows
