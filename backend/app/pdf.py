"""The printable land passport: one A4 page, drawn with ReportLab.

Everything is vector drawing (lines, rectangles, text), so it is sharp at any zoom and needs no map
tiles, no images and no internet. The QR code is drawn as little squares, not as a picture.
build_passport_pdf() is a pure function: passport data in, PDF bytes out (no database).
"""
import functools
import io
import math
import re
from datetime import timezone
from xml.sax.saxutils import escape

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from . import config, db

W, H = A4                      # 595 x 842 points (1 point = 1/72 inch)
M = 36                         # page margin
CW = W - 2 * M                 # content width

# Same colour-blind-friendly band colours as the map, plus the text colour that reads well on each.
BAND_FILL = {"green": colors.Color(0 / 255, 158 / 255, 115 / 255),
             "amber": colors.Color(240 / 255, 228 / 255, 66 / 255),
             "red": colors.Color(213 / 255, 94 / 255, 0 / 255)}
BAND_TEXT = {"green": colors.white, "amber": colors.black, "red": colors.white}
GREY = colors.Color(0.38, 0.38, 0.38)

DEMO_NOTICE = "DEMO DATA, NOT AN OFFICIAL RECORD"
DISCLAIMER = ("DEMO DATA. This passport was generated from fictional records for demonstration only. "
              "It is not an official land record and has no legal value.",
              "To check that the records still match what was printed, scan the QR code or open the verify link.")


# ---------- settings ----------

def public_base_url(env=None):
    """PUBLIC_BASE_URL from .env / the environment (default http://localhost:8000), without a trailing slash.
    This is the web address the QR code points at."""
    env = db.read_env() if env is None else env
    value = (env.get("PUBLIC_BASE_URL") or "").strip() or config.DEFAULT_PUBLIC_BASE_URL
    if not re.match(r"^https?://[^\s/]+", value):
        raise RuntimeError(f"PUBLIC_BASE_URL must start with http:// or https:// (got {value!r})")
    return value.rstrip("/")


@functools.lru_cache(maxsize=1)
def get_public_base_url():
    return public_base_url()


def verify_url(base_url, doc_id):
    return f"{base_url.rstrip('/')}/verify/{doc_id}"


def pretty(text):
    """boundary_overlap -> Boundary overlap"""
    text = text.replace("_", " ")
    return text[:1].upper() + text[1:]


# ---------- small drawing helpers ----------

def _text(c, x, y, text, font="Helvetica", size=10, color=colors.black, align="left"):
    c.setFont(font, size)
    c.setFillColor(color)
    {"left": c.drawString, "right": c.drawRightString, "center": c.drawCentredString}[align](x, y, text)


def _draw_header(c, ulpin):
    _text(c, M, H - 52, "LandStack Land Passport", "Helvetica-Bold", 21)
    _text(c, M, H - 75, "ULPIN", "Helvetica-Bold", 10, GREY)
    _text(c, M + 42, H - 76, ulpin, "Courier-Bold", 17)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.setFillColor(colors.Color(0.92, 0.92, 0.92))
    c.rect(M, H - 114, CW, 26, stroke=1, fill=1)
    _text(c, W / 2, H - 105, DEMO_NOTICE, "Helvetica-Bold", 12, align="center")


def _draw_facts_and_badge(c, p, y_top):
    _text(c, M, y_top, "PLOT FACTS", "Helvetica-Bold", 8, GREY)
    area = p["area_sqm"]
    facts = [("Village", p["village"]), ("Land use", p["land_use"]), ("Survey number", p["survey_no"]),
             ("Mapped area", "Not available" if area is None else f"{round(area):,} m²")]
    for i, (label, value) in enumerate(facts):
        y = y_top - 20 - i * 22
        _text(c, M, y, label, "Helvetica", 9, GREY)
        _text(c, M + 95, y, value, "Helvetica-Bold", 11)

    band = p["band"]
    top, height, width = y_top - 100, 62, 250
    c.setFillColor(BAND_FILL[band])
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    c.roundRect(M, top - height, width, height, 6, stroke=1, fill=1)
    _text(c, M + 14, top - 44, str(p["score"]), "Helvetica-Bold", 34, BAND_TEXT[band])
    _text(c, M + 90, top - 26, f"{band.upper()} RISK BAND", "Helvetica-Bold", 14, BAND_TEXT[band])   # the band, in words
    _text(c, M + 90, top - 43, "Risk score out of 100", "Helvetica", 9, BAND_TEXT[band])


def _to_metres(ring):
    lat0 = sum(lat for _, lat in ring) / len(ring)
    lon0 = sum(lon for lon, _ in ring) / len(ring)
    kx = 111_320 * math.cos(math.radians(lat0))
    return [((lon - lon0) * kx, (lat - lat0) * 110_574) for lon, lat in ring]


def _nice_length(limit):
    for length in (100, 50, 25, 20, 10, 5, 2, 1):
        if length <= limit:
            return length
    return None


def _draw_boundary(c, p, x, y, w, h):
    """Draw the plot outline from its coordinates, scaled to fit the box (x, y = bottom-left)."""
    _text(c, x, y + h + 8, "PLOT BOUNDARY", "Helvetica-Bold", 8, GREY)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)
    c.setFillColor(colors.white)
    c.rect(x, y, w, h, stroke=1, fill=1)

    invalid = any(f["type"] == "invalid_boundary" for f in p["findings"])
    pts = _to_metres(p["geometry"]["coordinates"][0])
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    bw, bh = (max(xs) - min(xs)) or 1, (max(ys) - min(ys)) or 1
    pad_side, pad_top, pad_bottom = 18, 26, 46
    scale = min((w - 2 * pad_side) / bw, (h - pad_top - pad_bottom) / bh)
    ox = x + (w - bw * scale) / 2 - min(xs) * scale
    oy = y + pad_bottom + (h - pad_top - pad_bottom - bh * scale) / 2 - min(ys) * scale
    pts_pdf = [(ox + px * scale, oy + py * scale) for px, py in pts]

    path = c.beginPath()
    path.moveTo(*pts_pdf[0])
    for q in pts_pdf[1:-1]:
        path.lineTo(*q)
    path.close()
    c.setLineWidth(2)
    if invalid:
        c.setDash(5, 3)
        c.drawPath(path, stroke=1, fill=0)
        c.setDash()
    else:
        c.setFillColor(colors.Color(0.88, 0.88, 0.88))
        c.drawPath(path, stroke=1, fill=1)
    c.setFillColor(colors.black)
    for q in pts_pdf[:-1]:
        c.circle(q[0], q[1], 1.8, stroke=0, fill=1)

    caption = "INVALID BOUNDARY (the outline crosses itself)" if invalid else "Plot outline, drawn from its coordinates"
    _text(c, x + w / 2, y + 26, caption, "Helvetica-Bold" if invalid else "Helvetica", 8.5, align="center")

    # scale bar (bottom-left) and north arrow (top-right)
    length = _nice_length(0.4 * w / scale)
    if length:
        bar = length * scale
        c.setStrokeColor(colors.black)
        c.setLineWidth(1.2)
        c.line(x + 12, y + 12, x + 12 + bar, y + 12)
        c.line(x + 12, y + 9, x + 12, y + 15)
        c.line(x + 12 + bar, y + 9, x + 12 + bar, y + 15)
        _text(c, x + 12 + bar + 5, y + 9.5, f"{length} m", "Helvetica", 8)
    ax, ay = x + w - 16, y + h - 12
    c.setFillColor(colors.black)
    tri = c.beginPath()
    tri.moveTo(ax, ay)
    tri.lineTo(ax - 4, ay - 11)
    tri.lineTo(ax + 4, ay - 11)
    tri.close()
    c.drawPath(tri, stroke=0, fill=1)
    _text(c, ax, ay - 21, "N", "Helvetica-Bold", 8, align="center")


def _findings_table(findings, size):
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=size, leading=size + 2)
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold")
    rows = [[Paragraph("Type", head), Paragraph("Points", head), Paragraph("Evidence", head)]]
    for f in findings:
        rows.append([Paragraph(escape(pretty(f["type"])), ParagraphStyle("t", parent=cell, fontName="Helvetica-Bold")),
                     Paragraph(f"+{f['points']}", cell), Paragraph(escape(f["evidence"]), cell)])
    table = Table(rows, colWidths=[112, 38, CW - 150], repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.45, 0.45, 0.45)),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _draw_findings(c, findings, y_label, y_floor):
    """The findings table, shrunk (and as a last resort cut short) so it always fits above y_floor.
    Returns the y of the bottom edge of what it drew, so the next section can start right under it."""
    _text(c, M, y_label, f"FINDINGS ({len(findings)})", "Helvetica-Bold", 8, GREY)
    top = y_label - 8
    avail = top - y_floor
    if not findings:
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.8)
        c.setFillColor(colors.white)
        c.rect(M, top - 30, CW, 30, stroke=1, fill=1)
        _text(c, M + 10, top - 20, "No conflicts found", "Helvetica-Bold", 12)
        return top - 30
    shown, hidden = list(findings), 0
    while True:
        for size in (8.5, 8, 7.5, 7, 6.5):
            table = _findings_table(shown, size)
            _, height = table.wrapOn(c, CW, avail)
            if height <= avail:
                table.drawOn(c, M, top - height)
                if hidden:
                    _text(c, M, top - height - 10, f"+ {hidden} more finding(s) not shown. See the digital passport.",
                          "Helvetica-Oblique", 7.5, GREY)
                    return top - height - 14
                return top - height
        shown, hidden = shown[:-1], hidden + 1
        avail = top - y_floor - 12 if hidden else avail


def _wrapped(c, x, y, text, font, size, width, max_lines=2):
    lines = simpleSplit(text, font, size, width)[:max_lines]
    for i, line in enumerate(lines):
        _text(c, x, y - i * 11.5, line, font, size)


def _draw_records(c, p, y_top, y_bottom):
    _text(c, M, y_top + 8, "RECORDS", "Helvetica-Bold", 8, GREY)
    gap = 10
    bw = (CW - 2 * gap) / 3
    boxes = [("Land record (RoR)", p["ror"], [("Owner", lambda r: r["owner_name"]),
                                            ("Recorded area", lambda r: f"{round(r['recorded_area_sqm']):,} m²")]),
             ("Registration", p["registration"], [("Owner", lambda r: r["owner_name"]),
                                                  ("Registered on", lambda r: str(r["registered_on"]))]),
             ("Tax record", p["tax"], [("Paid until", lambda r: str(r["paid_until"]))])]
    for i, (title, record, fields) in enumerate(boxes):
        x = M + i * (bw + gap)
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.8)
        c.setFillColor(colors.Color(0.93, 0.93, 0.93) if record is None else colors.white)
        c.rect(x, y_bottom, bw, y_top - y_bottom, stroke=1, fill=1)
        _text(c, x + 8, y_top - 14, title, "Helvetica-Bold", 9.5)
        if record is None:
            _text(c, x + 8, y_top - 44, "Missing", "Helvetica-Bold", 16)
            _text(c, x + 8, y_top - 58, "no record on file", "Helvetica", 8, GREY)
            continue
        y = y_top - 30
        for label, getter in fields:
            _text(c, x + 8, y, label, "Helvetica", 7.5, GREY)
            _wrapped(c, x + 8, y - 12, getter(record), "Helvetica-Bold", 10, bw - 16)
            y -= 36 if label == "Owner" else 30


def _draw_qr(c, data, x, y, size):
    """The QR code as vector squares. x, y = bottom-left of the code (the quiet border is drawn around it)."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    cell = size / n
    c.setFillColor(colors.white)
    c.rect(x - 6, y - 6, size + 12, size + 12, stroke=0, fill=1)
    c.setFillColor(colors.black)
    for r, row in enumerate(matrix):
        for col, dark in enumerate(row):
            if dark:
                c.rect(x + col * cell, y + size - (r + 1) * cell, cell + 0.15, cell + 0.15, stroke=0, fill=1)


def _draw_issue_block(c, doc_id, issued_at, issued_to, issued_role, url, top):
    """QR code + document id + who/when, hanging down from y = top (about 112 points tall)."""
    qr_size = 92
    _draw_qr(c, url, M + 6, top - 6 - qr_size, qr_size)
    _text(c, M + 6 + qr_size / 2, top - 6 - qr_size - 14, "Scan to verify", "Helvetica", 7.5, GREY, align="center")
    x = M + qr_size + 36
    _text(c, x, top - 10, "DOCUMENT ID", "Helvetica-Bold", 8, GREY)
    _text(c, x, top - 28, doc_id, "Courier-Bold", 16)
    _text(c, x, top - 50, f"Generated: {issued_at:%Y-%m-%d %H:%M} UTC", "Helvetica", 9.5)
    _text(c, x, top - 64, f"Generated by: {issued_to} ({issued_role})", "Helvetica", 9.5)
    _text(c, x, top - 82, "Verify this document:", "Helvetica-Bold", 8.5)
    for i, line in enumerate(simpleSplit(url, "Courier", 8, W - M - x)[:2]):
        _text(c, x, top - 93 - i * 10, line, "Courier", 8)


def _draw_footer(c, ulpin, doc_id):
    c.setStrokeColor(GREY)
    c.setLineWidth(0.6)
    c.line(M, 80, W - M, 80)
    for i, line in enumerate(DISCLAIMER):
        _text(c, M, 68 - i * 10, line, "Helvetica", 7.5, GREY)
    _text(c, M, 40, f"LandStack Land Passport  |  {ulpin}  |  {doc_id}", "Helvetica", 7.5, GREY)
    _text(c, W - M, 40, "Page 1 of 1", "Helvetica", 7.5, GREY, align="right")


def build_passport_pdf(passport, *, doc_id, issued_at, issued_to, issued_role, url):
    """Return the finished PDF as bytes. `passport` is the dict the JSON passport endpoint returns
    (already redacted for citizens). `issued_at` is a timezone-aware datetime (shown in UTC)."""
    issued_at = issued_at.astimezone(timezone.utc)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"LandStack Land Passport {passport['ulpin']}")
    c.setAuthor("LandStack (demo data)")
    c.setSubject("Demo land passport. Not an official record.")

    y_top = H - 130
    _draw_header(c, passport["ulpin"])
    _draw_facts_and_badge(c, passport, y_top)
    _draw_boundary(c, passport, M + 270, y_top - 166, CW - 270, 160)

    # Below the drawing the sections follow each other, so a short table leaves no hole in the middle.
    # The floor keeps the worst case (a long findings table) from running into the QR block and footer.
    bottom = _draw_findings(c, passport["findings"], y_top - 182, y_floor=338)
    records_top = bottom - 30
    records_bottom = records_top - 86
    _draw_records(c, passport, records_top, records_bottom)
    _draw_issue_block(c, doc_id, issued_at, issued_to, issued_role, url, top=records_bottom - 22)
    _draw_footer(c, passport["ulpin"], doc_id)
    c.showPage()
    c.save()
    return buffer.getvalue()
