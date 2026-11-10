"""Why is a plot unusual? A plain-English answer from the three features that pushed its score the most.

SHAP (TreeExplainer) splits one plot's score into a contribution per feature. The features that pushed it
furthest towards "unusual" are the reasons. If the `shap` package is not installed this falls back to
z-scores: how many standard deviations each feature is from the training median. The answer says which
method it used in `Explainer.method`.

A reason only ever names a feature and its value, never another plot's id.
"""
import numpy as np

from ml import features

def _n(value, digits=0):
    return f"{value:,.{digits}f}"


def _vs(value, typical):
    return "higher" if value > typical else "lower"


# One sentence per feature. Each gets the plot's value and the training median ("typical").
SENTENCES = {
    "area_sqm": lambda v, t: f"The mapped area is {_n(v)} sq m, {_vs(v, t)} than typical ({_n(t)} sq m)",
    "perimeter_m": lambda v, t: f"The boundary is {_n(v)} m long, {_vs(v, t)} than typical ({_n(t)} m)",
    "compactness": lambda v, t: (f"The shape is {'less' if v < t else 'more'} compact than typical "
                                 f"({v:.2f} against {t:.2f}; 1.00 is a circle)"),
    "aspect_ratio": lambda v, t: f"The plot is {v:.1f} times longer than wide, {_vs(v, t)} than typical ({t:.1f})",
    "vertex_count": lambda v, t: f"The boundary has {_n(v)} corners, {_vs(v, t)} than typical ({_n(t)})",
    "recorded_over_mapped": lambda v, t: (f"The recorded area is {v:.0%} of the mapped area "
                                          f"(typical {t:.0%})"),
    "years_since_tax_paid": lambda v, t: (
        f"Tax is paid only up to {v:.1f} years before the reference date (typical {t:.1f})" if v >= 0
        else f"Tax is paid {-v:.1f} years ahead of the reference date (typical {t:.1f} years before)"),
    "years_since_registration": lambda v, t: (f"It was registered {v:.1f} years ago, "
                                              f"{_vs(v, t)} than typical ({t:.1f})"),
    "neighbour_count": lambda v, t: (f"It overlaps or touches {_n(v)} other "
                                     f"{'plot' if round(v) == 1 else 'plots'} (typical {_n(t)})"),
    "zone_distance_m": lambda v, t: ("It lies inside or touches a restricted zone" if v <= 0.5
                                     else f"It is {_n(v)} m from the nearest restricted zone (typical {_n(t)} m)"),
    "area_vs_village_median": lambda v, t: (f"Its area is {v:.1f} times the median plot in its village "
                                            f"(typical {t:.1f})"),
    "invalid_shape": lambda v, t: "The boundary is an invalid shape (it crosses itself or is empty)",
}


class Explainer:
    def __init__(self, bundle):
        self.bundle = bundle
        self.medians = bundle["medians"]
        self.spread = bundle["spread"]
        try:                            # shap is optional (the API and the tests work without it) and slow to import
            import shap
            self._shap = shap.TreeExplainer(bundle["model"])
            self.method = "shap"
        except ImportError:             # pragma: no cover (depends on the environment)
            self._shap = None
            self.method = "z-score"

    def contributions(self, rows):
        """How strongly each feature pushes each row towards "unusual" (higher = more). Shape: rows x features."""
        X = np.asarray(rows, dtype=float)
        if self._shap is not None:
            return -np.asarray(self._shap.shap_values(X))    # SHAP explains "normality"; flip it to "unusualness"
        return np.abs((X - np.asarray(self.medians)) / np.asarray(self.spread))

    def top_features(self, row, n=3):
        """The n feature names that push this row most towards unusual (SHAP: only positive pushes)."""
        c = self.contributions([row])[0]
        order = [int(i) for i in np.argsort(-c)[:n] if c[i] > 0]
        return [features.FEATURE_NAMES[i] for i in order]

    def reasons(self, row, n=3):
        """Plain-English reasons, strongest first (at most n)."""
        out = []
        for name in self.top_features(row, n):
            i = features.FEATURE_NAMES.index(name)
            out.append(SENTENCES[name](float(row[i]), self.medians[i]))
        return out
