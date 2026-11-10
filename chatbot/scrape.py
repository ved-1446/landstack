"""A polite scraper for the Land Guide's public sources (Phase 11, Part B).

Rules it follows (all tested with a fake network):
- It reads ONLY the URLs listed in chatbot/sources.json. It never follows links and never crawls.
- A descriptive User-Agent, a pause of at least 4 seconds between requests (or the site's Crawl-delay, if larger).
- It checks each host's robots.txt first and skips any page the site disallows for us.
- A cache: a page that is already in chatbot/raw/ is never fetched again (delete that folder to start fresh).
- At most 30 pages per run.
- On any 403 or 429 it STOPS AT ONCE and says so (Blocked), instead of trying again.
- It stores the URL, the page title and the retrieval date in sources.json (committed). The raw pages themselves go in
  chatbot/raw/ (git-ignored): they are other people's text and are not part of this repository.
"""
import hashlib
import json
import re
import time
import urllib.robotparser
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import httpx

USER_AGENT = "LandStackGuideBot/0.1 (student project; polite and cached; reads a short list of public pages)"
MIN_DELAY_S = 4.0
MAX_PAGES = 30
TIMEOUT_S = 30


class Blocked(Exception):
    """The site answered 403 or 429: stop immediately and report."""


def cache_key(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _http_get(url):
    """The ONLY network call in the scraper: (status code, text). Tests replace this."""
    response = httpx.get(url, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT_S, follow_redirects=True)
    return response.status_code, response.text


def _title_of(html):
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return " ".join(re.sub(r"<[^>]+>", " ", match.group(1)).split()) if match else None


def load_sources(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_sources(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def scrape(sources_path, raw_dir, *, get=None, sleep=time.sleep, today=None, max_pages=MAX_PAGES, min_delay=MIN_DELAY_S):
    """Fetch every listed page that is not cached yet. Updates sources.json. Returns a report dict.
    Raises Blocked on 403/429 (after saving what was gathered so far)."""
    get = get or _http_get
    today = (today or date.today()).isoformat()
    raw = Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    data = load_sources(sources_path)
    robots, delays, report = {}, {}, {"fetched": 0, "cached": 0, "skipped": [], "failed": [], "requests": 0}
    last_request = [None]

    def polite_get(url, delay):
        if last_request[0] is not None:
            sleep(delay)                                      # the pause goes between requests, never before the first
        last_request[0] = time.monotonic()
        report["requests"] += 1
        return get(url)

    def parser_for(host_url):
        parts = urlsplit(host_url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in robots:
            status, text = polite_get(f"{host}/robots.txt", min_delay)
            rp = urllib.robotparser.RobotFileParser()
            # a missing robots.txt (or an HTML page standing in for one) sets no rules: nothing is disallowed
            looks_real = status == 200 and "user-agent" in text.lower() and "<html" not in text[:300].lower()
            if status in (401, 403, 429):
                raise Blocked(f"{host} answered {status} for robots.txt")
            rp.parse(text.splitlines() if looks_real else [])
            robots[host] = rp
            delays[host] = max(min_delay, float(rp.crawl_delay(USER_AGENT) or rp.crawl_delay("*") or 0))
        return robots[host], delays[host]

    try:
        for source in data["sources"]:
            url = source["url"]
            page = raw / (cache_key(url) + ".html")
            if page.is_file() and source.get("status") == "ok":
                report["cached"] += 1                         # already have it: never fetched again
                continue
            if report["fetched"] >= max_pages:
                report["skipped"].append((url, "page limit reached"))
                continue
            rp, delay = parser_for(url)
            if not rp.can_fetch(USER_AGENT, url):
                source.update(status="skipped: robots.txt disallows this page", retrieved=None)
                report["skipped"].append((url, "robots.txt"))
                continue
            status, text = polite_get(url, delay)
            if status in (403, 429):
                raise Blocked(f"{url} answered {status}")
            if status != 200:
                source.update(status=f"failed: HTTP {status}", retrieved=None)
                report["failed"].append((url, status))
                continue
            page.write_text(text, encoding="utf-8")
            source.update(title=_title_of(text) or source.get("title") or url, retrieved=today, status="ok")
            report["fetched"] += 1
    finally:
        save_sources(sources_path, data)                      # keep whatever was learned, even when stopping early
    return report
