"""Devanagari (Hindi, Marathi) text for the printable passport (Phase 11b).

WHY THIS EXISTS: ReportLab draws text one letter at a time and does no "shaping". Devanagari needs shaping: a short "i" sign
is written BEFORE its consonant, letters join into conjuncts (क्ष, ज्ञ, द्व), a "reph" hops above the next letter. Drawn
plainly, हिन्दी comes out as हन्िदी. So Devanagari is handled here:

  1. HarfBuzz (the `uharfbuzz` package, the same engine browsers use) shapes the text into the right glyphs in the right places;
  2. each glyph's outline is read from the bundled Noto Sans Devanagari font and drawn as a vector path with the NON-ZERO fill
     rule (ReportLab's default even-odd rule would punch small holes where a letter's outlines overlap).

Everything else in the PDF stays plain Helvetica. If the font or the shaper is missing, or the font has no glyph for a letter
(it would show as an empty box), the Devanagari part is replaced by a visible note instead. Empty boxes are never printed.

The font is Noto Sans Devanagari (c) The Noto Project Authors, SIL Open Font License 1.1: see fonts/OFL.txt and fonts/README.md.
"""
import functools
import re
import unicodedata
from pathlib import Path

from reportlab.lib.utils import simpleSplit  # noqa: F401  (kept importable for callers that wrap plain text)
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable

FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_FILES = {False: "NotoSansDevanagari-Regular.ttf", True: "NotoSansDevanagari-Bold.ttf"}
PLACEHOLDER = "(Devanagari text: see the digital passport)"
FILL_NON_ZERO = 1                       # reportlab's name for the non-zero winding rule

_DEVA = re.compile("[ऀ-ॿ꣠-ꣿ‌‍]")     # Devanagari, Devanagari Extended, ZWNJ and ZWJ


def has_devanagari(text):
    return bool(text) and bool(_DEVA.search(text))


def _is_deva(ch):
    return bool(_DEVA.match(ch))


def runs(text):
    """Split into [(is_devanagari, piece)] runs: Devanagari letters together, everything else together."""
    out = []
    for ch in text:
        flag = _is_deva(ch)
        if out and out[-1][0] == flag:
            out[-1] = (flag, out[-1][1] + ch)
        else:
            out.append((flag, ch))
    return out


# ---------------------------------------------------------------- the font and the shaper (loaded once, only when needed)

class _Face:
    def __init__(self, path):
        import uharfbuzz as hb
        from fontTools.ttLib import TTFont
        self.hb = hb
        self.font = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
        self.tt = TTFont(str(path))
        self.glyph_set = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upem = self.tt["head"].unitsPerEm
        self._outlines = {}

    def shape(self, text, lang="hi"):
        buf = self.hb.Buffer()
        buf.add_str(text)
        buf.script, buf.language = "Deva", lang
        buf.direction = "ltr"
        self.hb.shape(self.font, buf, {"kern": True, "liga": True, "ccmp": True, "locl": True})
        return list(zip(buf.glyph_infos, buf.glyph_positions))

    def outline(self, glyph_id):
        """The glyph's outline as a list of ('m'|'l'|'c'|'z', points...), cubic curves only. Cached."""
        if glyph_id not in self._outlines:
            from fontTools.pens.basePen import BasePen
            ops = []

            class Recorder(BasePen):
                def _moveTo(self, pt): ops.append(("m", pt))
                def _lineTo(self, pt): ops.append(("l", pt))
                def _curveToOne(self, a, b, c): ops.append(("c", a, b, c))      # quadratic curves arrive here as cubics
                def _closePath(self): ops.append(("z",))

            self.glyph_set[self.order[glyph_id]].draw(Recorder(self.glyph_set))
            self._outlines[glyph_id] = ops
        return self._outlines[glyph_id]


@functools.lru_cache(maxsize=2)
def _face(bold):
    path = FONT_DIR / FONT_FILES[bool(bold)]
    if not path.is_file():
        return None
    try:
        return _Face(path)
    except Exception:  # noqa: BLE001  (uharfbuzz or fonttools missing, or a damaged font file: fall back to the placeholder)
        return None


def available():
    """True if Devanagari can be drawn properly (both font files and the shaping libraries are there)."""
    return _face(False) is not None and _face(True) is not None


def shaped_glyphs(text, bold=False, lang="hi"):
    """[(glyph id, glyph name, x advance in font units)] after shaping: the order is the order they are DRAWN in (visual order)."""
    face = _face(bold)
    if face is None:
        raise RuntimeError("the Devanagari font or the shaping library is not available")
    return [(info.codepoint, face.order[info.codepoint], pos.x_advance) for info, pos in face.shape(text, lang)]


def missing_glyphs(text, bold=False):
    """True if the font cannot draw some letter of `text` (it would show as an empty box, the .notdef glyph)."""
    return any(gid == 0 for gid, _name, _adv in shaped_glyphs(text, bold))


# ---------------------------------------------------------------- making text safe to draw

def _latin_safe(text):
    """Helvetica draws Windows-1252 letters. Anything else would print as an odd mark, so it becomes '?'."""
    return text.encode("cp1252", errors="replace").decode("cp1252")


def prepare(text, bold=False):
    """The text as it will be drawn: Devanagari kept when it can be drawn properly, otherwise the visible placeholder;
    other letters Helvetica cannot draw become '?'. Never an empty box."""
    if not text:
        return text
    pieces, last_placeholder = [], False
    for is_deva, piece in runs(text):
        if is_deva and (not available() or missing_glyphs(piece, bold)):
            if not last_placeholder:
                pieces.append(PLACEHOLDER)
            last_placeholder = True
        else:
            pieces.append(piece if is_deva else _latin_safe(piece))
            last_placeholder = False
    out = "".join(pieces)
    # words separated only by spaces or punctuation (रमेश कुलकर्णी) were replaced one by one: show the note once
    note = re.escape(PLACEHOLDER)
    return re.sub(rf"({note})(?:[\s,;:'\"-]*{note})+", lambda m: m.group(1), out)


# ---------------------------------------------------------------- measuring, drawing, wrapping

def _is_bold(font):
    return "Bold" in font


def width(text, size, font="Helvetica"):
    """Width in points of `text` drawn by draw() (Devanagari runs shaped, the rest in `font`)."""
    total = 0.0
    for is_deva, piece in runs(text):
        if is_deva:
            face = _face(_is_bold(font))
            total += sum(pos.x_advance for _i, pos in face.shape(piece)) * size / face.upem
        else:
            total += stringWidth(piece, font, size)
    return total


def _draw_deva(c, x, y, text, size, bold):
    face = _face(bold)
    scale = size / face.upem
    pen_x = 0
    for info, pos in face.shape(text):
        ops = face.outline(info.codepoint)
        if ops:
            path = c.beginPath()
            for op in ops:
                if op[0] == "m":
                    path.moveTo(*op[1])
                elif op[0] == "l":
                    path.lineTo(*op[1])
                elif op[0] == "c":
                    path.curveTo(*op[1], *op[2], *op[3])
                else:
                    path.close()
            c.saveState()
            c.translate(x + (pen_x + pos.x_offset) * scale, y + pos.y_offset * scale)
            c.scale(scale, scale)
            c.drawPath(path, stroke=0, fill=1, fillMode=FILL_NON_ZERO)
            c.restoreState()
        pen_x += pos.x_advance
    return pen_x * scale


def draw(c, x, y, text, size, font="Helvetica", color=None, align="left"):
    """Draw one line of mixed Latin and Devanagari text. The fill colour is whatever the canvas has (or `color`)."""
    text = prepare(text, _is_bold(font))
    if color is not None:
        c.setFillColor(color)
    total = width(text, size, font)
    if align == "right":
        x -= total
    elif align == "center":
        x -= total / 2
    for is_deva, piece in runs(text):
        if is_deva:
            x += _draw_deva(c, x, y, piece, size, _is_bold(font))
        else:
            c.setFont(font, size)
            c.drawString(x, y, piece)
            x += stringWidth(piece, font, size)
    return total


def _clusters(word):
    """The word cut into pieces that must stay together: a letter with its combining signs, and anything joined by a virama."""
    out = []
    for ch in word:
        joins = out and (unicodedata.category(ch) in ("Mn", "Mc", "Me") or ch in "‌‍" or out[-1][-1] in ("्", "‍"))
        if joins:
            out[-1] += ch
        else:
            out.append(ch)
    return out


def wrap(text, size, max_width, font="Helvetica"):
    """Break `text` into lines no wider than max_width (at spaces; a single over-long word is cut between letter clusters)."""
    text = prepare(text, _is_bold(font))
    lines, current = [], ""
    for word in text.split(" "):
        trial = f"{current} {word}" if current else word
        if width(trial, size, font) <= max_width:
            current = trial
            continue
        if current:
            lines.append(current)
            current = ""
        if width(word, size, font) <= max_width:
            current = word
            continue
        piece = ""                                                   # a word wider than the whole line
        for cluster in _clusters(word):
            if piece and width(piece + cluster, size, font) > max_width:
                lines.append(piece)
                piece = ""
            piece += cluster
        current = piece
    if current:
        lines.append(current)
    return lines or [""]


class MixedParagraph(Flowable):
    """A paragraph for table cells that may hold Devanagari (ReportLab's Paragraph cannot shape it)."""

    def __init__(self, text, size, font="Helvetica", leading=None):
        super().__init__()
        self.text, self.size, self.font = text, size, font
        self.leading = leading or size + 2
        self.lines = [text]

    def wrap(self, avail_width, avail_height):
        self.lines = wrap(self.text, self.size, max(avail_width - 2, 1), self.font)
        self.width, self.height = avail_width, self.leading * len(self.lines)
        return self.width, self.height

    def draw(self):
        for i, line in enumerate(self.lines):
            draw(self.canv, 0, self.height - self.size - i * self.leading + 1.5, line, self.size, self.font)
