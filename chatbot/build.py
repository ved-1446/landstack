"""One command to build the Land Guide's corpus: scrape the listed public pages (politely, cached), then index.

    python -m chatbot.build                 # scrape what is not cached yet, then rebuild the chunks
    python -m chatbot.build --index-only    # no network at all: rebuild the chunks from what is already saved

A fresh clone has no corpus (the raw pages and the chunks are git-ignored). Until you run this, the Guide still works
from the original glossary alone. To start over, delete chatbot/raw/ and chatbot/chunks.jsonl first.
"""
import argparse
import sys

from chatbot import index, scrape


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index-only", action="store_true", help="skip the scraping step (no network)")
    args = ap.parse_args(argv)
    directory = index.data_dir()

    if not args.index_only:
        try:
            report = scrape.scrape(directory / "sources.json", directory / "raw")
        except scrape.Blocked as exc:
            print(f"STOPPED: {exc}. The site asked us to stop, so nothing more was requested. Saved pages are kept.")
            return 2
        print(f"scrape: {report['fetched']} fetched, {report['cached']} already cached, {len(report['skipped'])} skipped, "
              f"{len(report['failed'])} failed, {report['requests']} requests")
        for url, why in report["skipped"]:
            print(f"  skipped {url}: {why}")
        for url, status in report["failed"]:
            print(f"  failed  {url}: HTTP {status}")

    records = index.build_chunks(directory)
    index.write_chunks(records, directory)
    sources = {r["source"] for r in records}
    print(f"index: {len(records)} chunks from {len(sources)} sources written to {directory / 'chunks.jsonl'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
