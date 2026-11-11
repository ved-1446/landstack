"""The friendly web page for GET /verify/{doc_id}: what a phone shows after scanning the QR code on a printed passport.

The same URL still answers with JSON for programs. Which one you get depends on the Accept header: a browser asks for
text/html, a program asks for application/json (or */*).

The page is deliberately tiny and safe: no JavaScript, no external fonts, images or links, every value is HTML-escaped, and strict
headers (Content-Security-Policy, nosniff, no-store) are sent. It says ONLY whether the records still match what was printed, the
plot id and when the passport was issued: no names, no evidence, no score (the same as the JSON answer).
"""
from datetime import datetime
from html import escape

# Nothing may load from anywhere: only this page's own inline style. No scripts at all.
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
    "Referrer-Policy": "no-referrer",
}

_STYLE = """
body{margin:0;background:#f6f0e4;color:#0f1e3d;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif}
main{max-width:34rem;margin:0 auto;padding:1.5rem 1rem 3rem}
.brand{font-weight:600;letter-spacing:.02em}
.verdict{margin:1.25rem 0;padding:1rem 1.25rem;border:3px solid #0f1e3d;border-radius:12px;background:#fff}
.verdict.changed,.verdict.unknown{border-style:dashed}
.word{font-size:1.75rem;font-weight:700;letter-spacing:.04em;margin:0}
.verdict p{margin:.5rem 0 0}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.35rem 1rem;margin:1rem 0}
dt{color:#3e4a66}dd{margin:0;font-family:ui-monospace,Consolas,monospace;overflow-wrap:anywhere}
.small{font-size:.875rem;color:#3e4a66}
"""


def wants_html(accept):
    """True for a browser (it lists text/html), false for programs (application/json or */*) and for no header at all."""
    kinds = [part.split(";")[0].strip().lower() for part in (accept or "").split(",") if part.strip()]
    return "text/html" in kinds and kinds[0] != "application/json"


def _page(title, kind, word, sentence, rows=(), extra=""):
    detail = "".join(f"<dt>{escape(label)}</dt><dd>{escape(value)}</dd>" for label, value in rows)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{escape(title)}</title>
<style>{_STYLE}</style>
</head>
<body>
<main>
<p class="brand">LandStack &middot; document check</p>
<section class="verdict {escape(kind)}" aria-labelledby="verdict">
<h1 class="word" id="verdict">{escape(word)}</h1>
<p>{escape(sentence)}</p>
</section>
{f"<dl>{detail}</dl>" if detail else ""}{extra}
<p class="small">This page says only whether the records still match what was printed. It shows no names, no evidence and no score.</p>
<p class="small">LandStack is a demo. Its records are fictional demo data, so this is not an official record.</p>
</main>
</body>
</html>
"""


def found_page(doc_id, ulpin, issued_at, matches):
    when = issued_at.strftime("%Y-%m-%d %H:%M UTC") if isinstance(issued_at, datetime) else str(issued_at)
    rows = [("Plot (ULPIN)", ulpin), ("Issued", when), ("Document id", doc_id)]
    if matches:
        return _page("Document check: records match", "matches", "MATCHES",
                     "The records still match what was printed on this passport.", rows)
    return _page("Document check: records have changed", "changed", "HAS CHANGED",
                 "The records have changed since this passport was issued. Do not rely on the printed copy: ask for a new one.", rows)


def not_found_page():
    return _page("Document check: not found", "unknown", "NOT FOUND",
                 "No document was found with that id. Check the id printed on the passport, or scan its QR code again.")
