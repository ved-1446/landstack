"""Chunking and BM25 search for the Land Guide (Phase 11, Part B). Everything here is plain Python and runs in memory.

The pipeline: raw pages (git-ignored) + the original glossary -> chunks (chatbot/chunks.jsonl, git-ignored) -> a BM25 index
rebuilt in memory from those chunks. BM25 is a classic word-matching score: a passage ranks high when it contains the
question's rarer words, often. There is no AI and no embedding in this step.
"""
import json
import os
import re
from pathlib import Path

from rank_bm25 import BM25Plus

DATA_DIR = Path(__file__).resolve().parent
GLOSSARY_FILE = DATA_DIR / "glossary.md"
GLOSSARY_TITLE = "LandStack glossary"
MAX_WORDS = 160          # a chunk is at most this many words (the overlap included)
OVERLAP_WORDS = 25       # when a long text must be cut, the next chunk repeats this many words of the last one

STOPWORDS = frozenset(
    "a an and are as at be but by can do does for from has have how i if in is it its me my of on or so than that the their "
    "them then there these they this to was we what when where which who why will with you your".split())


def data_dir():
    """chatbot/ unless CHATBOT_DATA_DIR says otherwise (the tests point it at a temporary folder)."""
    return Path(os.environ.get("CHATBOT_DATA_DIR") or DATA_DIR)


def tokenize(text):
    """Lowercase words and numbers, no stop words, a plural 's' removed (so 'records' finds 'record')."""
    out = []
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in STOPWORDS:
            continue
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.append(word)
    return out


# ---------------------------------------------------------------- chunking

def _split_long(words, max_words, overlap):
    """Cut a too-long run of words into windows of max_words that overlap by `overlap` words."""
    step = max(1, max_words - overlap)
    pieces, start = [], 0
    while start < len(words):
        pieces.append(words[start:start + max_words])
        if start + max_words >= len(words):
            break
        start += step
    return pieces


def chunk_text(text, max_words=MAX_WORDS, overlap=OVERLAP_WORDS):
    """Split text into chunks of at most `max_words` words. Blank lines separate paragraphs; whole paragraphs are packed
    together, and one that is too long is cut into overlapping windows. Deterministic. Empty text gives []."""
    paragraphs = [p.split() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    chunks, current = [], []
    for words in paragraphs:
        if len(words) > max_words:
            if current:
                chunks.append(current)
                current = []
            chunks += _split_long(words, max_words, overlap)
        elif len(current) + len(words) > max_words:
            chunks.append(current)
            current = list(words)
        else:
            current += words
    if current:
        chunks.append(current)
    return [" ".join(c) for c in chunks]


def chunk_document(text, title, url, retrieved=None, prefix="doc"):
    """A whole document -> chunk records. Headings ('## Name' lines) start a new section, and every chunk remembers
    which section it came from, so an answer can say where it found something."""
    records = []
    sections = re.split(r"(?m)^(?=#{1,3} )", text)
    for section in sections:
        section = section.strip()
        if not section:
            continue
        heading = None
        match = re.match(r"#{1,3} (.+)", section)
        body = section
        if match:
            heading = match.group(1).strip()
            body = section[match.end():].strip()
        for piece in chunk_text(body):
            records.append({
                "id": f"{prefix}-{len(records):03d}",
                "source": title, "title": f"{title}: {heading}" if heading and heading != title else title,
                "url": url, "retrieved": retrieved, "text": (f"{heading}. " if heading else "") + piece,
            })
    return records


def _embedded_article(html):
    """Some sites (Vikaspedia is a Next.js site) ship the article as JSON inside the page instead of as visible HTML. If the
    page has that, return the article's HTML; otherwise None. This reads the page we already have: no extra request."""
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        content = data["props"]["pageProps"]["ssrPageContent"]["content"]
    except (ValueError, KeyError, TypeError):
        return None
    return content if isinstance(content, str) and content.strip() else None


def html_to_text(html):
    """The readable text of a web page: headings become '## ...' lines, short menu-like lines are dropped."""
    from bs4 import BeautifulSoup
    html = _embedded_article(html) or html
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "form", "aside", "noscript", "svg", "iframe", "button"]):
        tag.decompose()
    lines = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = " ".join(el.get_text(" ", strip=True).split())
        if not text:
            continue
        if el.name in ("h1", "h2", "h3"):
            lines.append(f"\n## {text}\n")
        elif len(text.split()) >= 5:                       # menu items and button labels are short; sentences are not
            lines.append(text + "\n")
    out, seen = [], set()
    for line in lines:                                     # a page repeats some lines (menus, footers): keep the first only
        key = line.strip()
        if key in seen and not key.startswith("##"):
            continue
        seen.add(key)
        out.append(line)
    return "\n".join(out)


def build_chunks(directory=None):
    """Chunk the original glossary and every cached page listed in sources.json. Returns a list of chunk records."""
    directory = Path(directory) if directory else data_dir()
    records = []
    glossary = directory / "glossary.md"
    if glossary.is_file():
        records += chunk_document(glossary.read_text(encoding="utf-8"), GLOSSARY_TITLE, None, None, "glossary")
    sources_file = directory / "sources.json"
    raw = directory / "raw"
    if sources_file.is_file() and raw.is_dir():
        from chatbot import scrape
        for source in json.loads(sources_file.read_text(encoding="utf-8")).get("sources", []):
            page = raw / (scrape.cache_key(source["url"]) + ".html")
            if source.get("status") != "ok" or not page.is_file():
                continue
            text = html_to_text(page.read_text(encoding="utf-8", errors="replace"))
            records += chunk_document(text, source.get("title") or source["url"], source["url"],
                                      source.get("retrieved"), f"web{len(records):04d}")
    return records


def write_chunks(records, directory=None):
    directory = Path(directory) if directory else data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / "chunks.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_chunks(directory=None):
    path = (Path(directory) if directory else data_dir()) / "chunks.jsonl"
    if not path.is_file():
        return None
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ---------------------------------------------------------------- BM25

class Index:
    """An in-memory BM25 index over chunk records. BM25Plus, a standard BM25 variant, is used because plain BM25 gives a word that
    appears in every passage a NEGATIVE weight, so a tiny corpus (or a fresh clone with only the glossary) would find nothing. delta=0 keeps a passage that shares no word with
    the question at exactly zero."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        corpus = [tokenize(c["title"] + " " + c["text"]) for c in self.chunks]
        self._bm25 = BM25Plus(corpus, delta=0.0) if self.chunks and any(corpus) else None

    def __len__(self):
        return len(self.chunks)

    def search(self, query, k=4, min_score=0.0):
        """The best-matching chunks as [(chunk, score)], best first. A chunk must score at least `min_score` and share a
        word with the question; ties keep the corpus order so results are repeatable."""
        tokens = tokenize(query)
        if not tokens or self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokens)
        order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
        return [(self.chunks[i], float(scores[i])) for i in order[:k] if scores[i] > 0 and scores[i] >= min_score]


def load_index(directory=None):
    """The index the API uses: the saved chunks if they exist, otherwise just the glossary (a fresh clone still works)."""
    chunks = read_chunks(directory)
    if chunks is None:
        chunks = build_chunks(directory)
    return Index(chunks)
