"""The fixed Hindi and Marathi sentences (chatbot/strings.json: one file, so a native speaker can review everything in one place).

The server uses only two of them (the "not legal advice" note and "I don't know from my sources."). Those are written by a
person, not machine-translated per request, so they are returned as they are, with no AI call. The rest are used by the UI.
"""
import json
from functools import lru_cache
from pathlib import Path

STRINGS_FILE = Path(__file__).resolve().parent / "strings.json"
LANGUAGES = ("en", "hi", "mr")


@lru_cache(maxsize=1)
def _data():
    return json.loads(STRINGS_FILE.read_text(encoding="utf-8"))


def get(key, language="en"):
    """The fixed text for `key` in `language` (English if that language is missing)."""
    entry = _data()["strings"][key]
    return entry.get(language) or entry["en"]


def fixed_translation(english_text, language):
    """If `english_text` is one of the fixed sentences, its reviewed Hindi/Marathi text; otherwise None."""
    if language == "en":
        return None
    for entry in _data()["strings"].values():
        if entry["en"] == english_text and language in entry:
            return entry[language]
    return None
