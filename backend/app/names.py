"""Fuzzy owner-name matcher: normalise, TF-IDF character n-grams, cosine similarity."""
import re
import string

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import config

# Only ASCII punctuation is removed, so Devanagari letters and marks survive.
_PUNCT = re.compile(f"[{re.escape(string.punctuation)}]")


def normalise(name):
    """'Kulkarni, Ramesh S.' -> 'kulkarni ramesh' (lowercase, no punctuation,
    one-letter initials dropped, words sorted)."""
    words = _PUNCT.sub(" ", name.lower()).split()
    return " ".join(sorted(w for w in words if len(w) > 1))


def similarity(a, b):
    """Cosine similarity (0 to 1) of the two normalised names.

    TF-IDF is fitted on just these two names, so the score depends only on the
    pair (no hidden state, same answer every time).
    """
    na, nb = normalise(a), normalise(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
    m = vec.fit_transform([na, nb])
    return float(cosine_similarity(m[0], m[1])[0, 0])


def same_person(a, b):
    """Return (is_same_person, score)."""
    score = similarity(a, b)
    return score >= config.NAME_MATCH_THRESHOLD, score
