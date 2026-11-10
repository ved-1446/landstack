"""Phase 11b: Devanagari (Hindi, Marathi) in the printable passport. No database, no network.

The point of these tests: Devanagari must be SHAPED (letters reordered, conjuncts joined), drawn with the right fill rule, and must
never come out as an empty box: if it cannot be drawn properly it is replaced by a visible note."""
import copy
import io
from datetime import datetime, timezone

import pytest
from pypdf import PdfReader

from backend.app import devanagari, pdf

HINDI = "हिन्दी भाषा में भूमि अभिलेख"
MARATHI = "मराठी भाषेत जमीन अभिलेख"
OWNERS = "रमेश कुलकर्णी, संजय देशपांडे"
CONJUNCTS = "क्षत्रिय ज्ञान श्री द्वारका प्रार्थना"
VOWEL_SIGNS = "कि की कु कू के कै को कौ कं कः"
REPH = "धर्म कर्म सूर्य पूर्वी निर्मल"
SAMPLES = [HINDI, MARATHI, OWNERS, CONJUNCTS, VOWEL_SIGNS, REPH]
MISSING_LETTER = "꣥"          # a Vedic mark the committed font subset does not contain: it would print as an empty box
PLACEHOLDER = devanagari.PLACEHOLDER


# ------------------------------------------------------------------ the font, the licence and the shaper

def test_the_font_files_are_small_and_carry_their_licence():
    for name in devanagari.FONT_FILES.values():
        path = devanagari.FONT_DIR / name
        assert path.is_file() and path.stat().st_size < 250_000, name         # Regular and Bold only, kept small
    licence = (devanagari.FONT_DIR / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL OPEN FONT LICENSE Version 1.1" in licence and "The Noto Project Authors" in licence
    assert (devanagari.FONT_DIR / "README.md").is_file()


def test_devanagari_can_be_drawn_in_this_environment():
    assert devanagari.available()


def test_detecting_and_splitting_devanagari():
    assert devanagari.has_devanagari("Owner रमेश") and not devanagari.has_devanagari("Owner Ramesh m²") and not devanagari.has_devanagari("")
    assert devanagari.runs("Owner रमेश कुलकर्णी: 12") == [(False, "Owner "), (True, "रमेश"), (False, " "), (True, "कुलकर्णी"), (False, ": 12")]
    assert devanagari.has_devanagari("क‍ष")                              # a joiner is part of the word


def names(text, bold=False):
    return [name for _gid, name, _adv in devanagari.shaped_glyphs(text, bold)]


def test_the_short_i_sign_is_moved_before_its_consonant():
    # plain left-to-right drawing would put the sign AFTER the letter (हन्िदी). Shaping draws the sign first.
    ki = names("कि")
    assert ki[0].startswith("uni093F") and ki[1] == "uni0915"                  # i-sign, then ka
    hindi = names("हिन्दी")
    assert hindi[0].startswith("uni093F") and hindi[1] == "uni0939"            # i-sign, then ha
    assert names("कि") != [f"uni{ord(c):04X}" for c in "कि"]                   # not just one glyph per character


def test_conjuncts_become_one_glyph_and_the_reph_is_its_own_glyph():
    assert names("क्ष") == ["uni0915094D0937"] and names("ज्ञ") == ["uni091C094D091E"]
    assert len(names("द्वारका")) < len("द्वारका")                               # द्व is joined
    assert names("धर्म")[-1] == "uni0930094D"                                  # the reph is drawn last, then placed above by the font


@pytest.mark.parametrize("text", SAMPLES)
@pytest.mark.parametrize("bold", [False, True])
def test_no_glyph_is_the_empty_box_for_hindi_and_marathi_samples(text, bold):
    # like the real code, look at the Devanagari runs only (spaces and commas are drawn by Helvetica, not by this font)
    for is_deva, piece in devanagari.runs(text):
        if is_deva:
            assert not devanagari.missing_glyphs(piece, bold)
            assert all(gid != 0 for gid, _n, _a in devanagari.shaped_glyphs(piece, bold))     # glyph 0 is .notdef, the empty box
    assert devanagari.prepare(text, bold) == text


def test_a_letter_the_font_lacks_is_detected_as_an_empty_box():
    assert devanagari.missing_glyphs(MISSING_LETTER)
    assert devanagari.has_devanagari(MISSING_LETTER)


# ------------------------------------------------------------------ the safe fallback (never boxes)

def test_a_letter_the_font_cannot_draw_becomes_the_visible_note_not_a_box():
    out = devanagari.prepare(f"Owner {MISSING_LETTER} रमेश")
    assert PLACEHOLDER in out and MISSING_LETTER not in out and "रमेश" in out        # only the bad run is replaced
    assert devanagari.prepare(f"{MISSING_LETTER} x {MISSING_LETTER}").count(PLACEHOLDER) == 2


def test_without_the_font_or_the_shaper_all_devanagari_becomes_the_note(monkeypatch):
    monkeypatch.setattr(devanagari, "_face", lambda bold: None)
    assert not devanagari.available()
    assert devanagari.prepare("Owner: रमेश कुलकर्णी") == f"Owner: {PLACEHOLDER}"
    assert devanagari.prepare("रमेश") == PLACEHOLDER
    assert devanagari.prepare("रमेश कुलकर्णी, संजय देशपांडे") == PLACEHOLDER           # words separated by spaces or commas: one note
    assert devanagari.prepare("Owner रमेश and सुनीता") == f"Owner {PLACEHOLDER} and {PLACEHOLDER}"   # real words between: two notes
    assert devanagari.prepare("plain text") == "plain text"


def test_other_letters_helvetica_cannot_draw_become_a_question_mark_not_a_box():
    assert devanagari.prepare("Owner தமிழ்") == "Owner ?????"                          # one '?' for each of the 5 characters
    assert devanagari.prepare("Village Pünjab m²") == "Village Pünjab m²"             # Windows-1252 letters are fine


# ------------------------------------------------------------------ drawing

class Recorder:
    """A tiny stand-in for the ReportLab canvas that remembers how paths were filled."""
    def __init__(self):
        self.fills, self.strings, self.paths = [], [], 0

    def beginPath(self):
        self.paths += 1
        return type("P", (), {"moveTo": lambda *a: None, "lineTo": lambda *a: None, "curveTo": lambda *a: None, "close": lambda *a: None})()

    def drawPath(self, path, stroke=1, fill=0, fillMode=None):
        self.fills.append((stroke, fill, fillMode))

    def drawString(self, x, y, text):
        self.strings.append(text)

    def __getattr__(self, name):                 # saveState, translate, scale, restoreState, setFont, setFillColor...
        return lambda *a, **k: None


def test_every_glyph_is_filled_with_the_non_zero_rule_and_no_outline():
    c = Recorder()
    devanagari.draw(c, 10, 10, OWNERS, 12, "Helvetica-Bold")
    assert c.fills and all(stroke == 0 and fill == 1 and mode == devanagari.FILL_NON_ZERO == 1 for stroke, fill, mode in c.fills)


def test_latin_parts_of_a_mixed_line_are_drawn_as_normal_text_and_devanagari_as_paths():
    c = Recorder()
    devanagari.draw(c, 0, 0, "owner 'रमेश' vs 12 sq m", 10, "Helvetica")
    assert c.strings == ["owner '", "' vs 12 sq m"] and len(c.fills) > 0


def test_width_is_the_sum_of_the_parts_and_alignment_uses_it():
    w_latin, w_deva = devanagari.width("abc ", 10, "Helvetica"), devanagari.width("रमेश", 10, "Helvetica")
    assert devanagari.width("abc रमेश", 10, "Helvetica") == pytest.approx(w_latin + w_deva)
    assert w_deva > 0 and devanagari.width("रमेश", 20, "Helvetica") == pytest.approx(2 * w_deva)
    assert devanagari.width("रमेश", 10, "Helvetica-Bold") != devanagari.width("रमेश", 10, "Helvetica")      # bold has its own font


def test_wrapping_keeps_lines_inside_the_width_and_never_splits_a_letter_from_its_signs():
    text = "record owner रमेश कुलकर्णी vs registration owner सुनीता देशपांडे name similarity 0.05"
    lines = devanagari.wrap(text, 9, 150, "Helvetica")
    assert len(lines) > 1 and all(devanagari.width(ln, 9, "Helvetica") <= 150 + 0.01 for ln in lines)
    assert " ".join(lines) == text
    # a single word wider than the line is cut between letter clusters: no line may start with a vowel sign or a virama
    long_word = "कुलकर्णीकुलकर्णीकुलकर्णीकुलकर्णी"
    pieces = devanagari.wrap(long_word, 12, 60, "Helvetica")
    assert len(pieces) > 1 and "".join(pieces) == long_word
    assert not any(ln[0] in "ािीुूृेैोौंः्‍" for ln in pieces)
    assert devanagari.wrap("", 9, 100) == [""]


def test_the_table_cell_flowable_wraps_and_reports_a_height():
    cell = devanagari.MixedParagraph("record owner रमेश कुलकर्णी vs registration owner सुनीता देशपांडे", 8.5, "Helvetica", 10.5)
    w, h = cell.wrap(200, 1000)
    assert w == 200 and h == 10.5 * len(cell.lines) and len(cell.lines) >= 2


# ------------------------------------------------------------------ the whole passport

def passport_with(owner_ror, owner_reg, village, evidence_extra=""):
    findings = [{"type": "owner_mismatch", "points": 25,
                 "evidence": f"record owner '{owner_ror}' vs registration owner '{owner_reg}'; name similarity 0.05 (needs 0.60){evidence_extra}"}]
    return {
        "ulpin": "MH000100000006", "village": village, "land_use": "industrial", "survey_no": "105/8", "area_sqm": 1848.6,
        "geometry": {"type": "Polygon", "coordinates": [[[73.806, 18.550], [73.8063, 18.550], [73.8063, 18.5503], [73.806, 18.5503], [73.806, 18.550]]]},
        "ror": {"owner_name": owner_ror, "recorded_area_sqm": 1447.1},
        "registration": {"owner_name": owner_reg, "registered_on": "2014-01-26"},
        "tax": {"paid_until": "2026-12-10"}, "score": 25, "band": "amber", "findings": findings, "unusual": None,
    }


def build(p):
    return pdf.build_passport_pdf(p, doc_id="ABCD-EFGH-JKLM", issued_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
                                  issued_to="admin", issued_role="admin", url="http://localhost:8000/verify/ABCD-EFGH-JKLM")


def text_of(data):
    reader = PdfReader(io.BytesIO(data))
    return len(reader.pages), " ".join(reader.pages[0].extract_text().split())


def test_a_marathi_owner_name_village_and_evidence_make_one_good_page():
    data = build(passport_with("रमेश कुलकर्णी", "सुनीता देशपांडे", "हिंजेवाडी"))
    pages, text = text_of(data)
    assert data.startswith(b"%PDF") and pages == 1
    assert PLACEHOLDER not in text                                      # it could be drawn properly, so no note
    assert "record owner '" in text and "name similarity 0.05" in text   # the Latin parts of the mixed sentence are real text
    # the Devanagari is drawn as shaped vector shapes, not as characters a reader could mis-extract
    assert "रमेश" not in text and "हन्िदी" not in text


def test_the_pdf_with_devanagari_differs_from_the_english_one_and_stays_english_otherwise():
    plain = build(passport_with("Ramesh Kulkarni", "Sunita Deshpande", "Hinjewadi"))
    marathi = build(passport_with("रमेश कुलकर्णी", "सुनीता देशपांडे", "हिंजेवाडी"))
    assert plain != marathi
    _p, text = text_of(marathi)
    for english in ("LandStack Land Passport", "DEMO DATA, NOT AN OFFICIAL RECORD", "Owner mismatch", "PLOT FACTS", "RECORDS"):
        assert english in text


def test_without_the_font_the_passport_shows_the_visible_note_and_never_boxes(monkeypatch):
    monkeypatch.setattr(devanagari, "_face", lambda bold: None)
    pages, text = text_of(build(passport_with("रमेश कुलकर्णी", "सुनीता देशपांडे", "हिंजेवाडी")))
    assert pages == 1 and PLACEHOLDER in text
    assert "(Devanagari text: see the digital passport)" in text


def test_a_letter_the_font_lacks_gives_the_note_in_the_pdf():
    pages, text = text_of(build(passport_with(f"रमेश {MISSING_LETTER}", "Sunita Deshpande", "Hinjewadi")))
    assert pages == 1 and PLACEHOLDER in text


def test_a_long_devanagari_evidence_still_fits_on_one_page():
    p = passport_with("रमेश कुलकर्णी", "सुनीता देशपांडे", "हिंजेवाडी")
    extra = "; " + "; ".join(f"overlaps plot MH0002000000{n:02d} by {500 + n} sq m (35% of this plot)" for n in range(10, 16))
    p["findings"][0]["evidence"] += extra
    pages, _text = text_of(build(p))
    assert pages == 1


def test_ascii_text_does_not_load_the_devanagari_font(monkeypatch):
    calls = []
    monkeypatch.setattr(devanagari, "_face", lambda bold: calls.append(bold))
    build(passport_with("Ramesh Kulkarni", "Sunita Deshpande", "Hinjewadi"))
    assert calls == []                                                   # plain English passports never touch the shaper


def test_the_existing_passport_data_is_not_modified_by_building_a_pdf():
    p = passport_with("रमेश कुलकर्णी", "सुनीता देशपांडे", "हिंजेवाडी")
    before = copy.deepcopy(p)
    build(p)
    assert p == before
