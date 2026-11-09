"""Load a state's raw file into the database as standard records.

    python -m db.adapters.ingest --state maharashtra --file db/adapters/samples/maharashtra_sample.csv
    python -m db.adapters.ingest --state karnataka --file <path> --dry-run

- Only ulpins that already exist in `plots` are loaded; unknown ones are reported and skipped.
- Rejected rows (bad date, negative area...) are reported, and the good rows still load.
- Safe to run twice: each record is matched by ulpin. A record that is new is inserted, one that
  differs is updated, one that is identical is left alone. Running it again changes nothing.
- A record the file does not mention is never deleted.
- --dry-run does all the reading and checking and prints what WOULD happen, but writes nothing.
"""
import argparse
import sys
from dataclasses import dataclass, field

from .base import AdapterError, UnknownStateError

# table -> (select existing, update, insert, how to read a record's values)
_TABLES = {
    "ror_records": {
        "label": "land records (ror_records)",
        "existing": "SELECT ulpin, owner_name, recorded_area_sqm FROM ror_records WHERE ulpin = ANY(%s::text[])",
        "update": "UPDATE ror_records SET owner_name = %s, recorded_area_sqm = %s WHERE ulpin = %s",
        "insert": "INSERT INTO ror_records (owner_name, recorded_area_sqm, ulpin) VALUES (%s, %s, %s)",
        "values": lambda r: (r.owner_name, r.recorded_area_sqm),
    },
    "registrations": {
        "label": "registrations",
        "existing": "SELECT ulpin, owner_name, registered_on FROM registrations WHERE ulpin = ANY(%s::text[])",
        "update": "UPDATE registrations SET owner_name = %s, registered_on = %s WHERE ulpin = %s",
        "insert": "INSERT INTO registrations (owner_name, registered_on, ulpin) VALUES (%s, %s, %s)",
        "values": lambda r: (r.owner_name, r.registered_on),
    },
    "tax_records": {
        "label": "tax records (tax_records)",
        "existing": "SELECT ulpin, paid_until FROM tax_records WHERE ulpin = ANY(%s::text[])",
        "update": "UPDATE tax_records SET paid_until = %s WHERE ulpin = %s",
        "insert": "INSERT INTO tax_records (paid_until, ulpin) VALUES (%s, %s)",
        "values": lambda r: (r.paid_until,),
    },
}
_RECORD_OF = {"ror_records": "ror", "registrations": "registration", "tax_records": "tax"}


@dataclass
class IngestReport:
    state: str
    path: str
    dry_run: bool
    rows_read: int
    rejected: list = field(default_factory=list)       # RejectedRow
    unknown_ulpins: list = field(default_factory=list)  # (row_number, ulpin)
    counts: dict = field(default_factory=dict)          # table -> {"new": n, "updated": n, "unchanged": n}
    plots_loaded: int = 0


def _same(new, old):
    """Compare a new value with a stored one (areas to the cent)."""
    if isinstance(new, float):
        return abs(new - float(old)) < 0.005
    return new == old


def ingest(conn, adapter, path, dry_run=False):
    """Run the adapter and load the result using `conn`. Never commits: the caller decides.
    With dry_run=True it only reads from the database."""
    result = adapter.parse(path)
    report = IngestReport(adapter.state, str(path), dry_run, result.rows_read, list(result.rejected))

    ulpins = [row.ulpin for row in result.rows]
    known = {u for (u,) in conn.execute("SELECT ulpin FROM plots WHERE ulpin = ANY(%s::text[])", (ulpins,))}
    report.unknown_ulpins = [(row.row_number, row.ulpin) for row in result.rows if row.ulpin not in known]
    rows = [row for row in result.rows if row.ulpin in known]
    report.plots_loaded = len(rows)

    for table, spec in _TABLES.items():
        records = [getattr(row, _RECORD_OF[table]) for row in rows]
        records = [r for r in records if r is not None]

        existing = {}
        for ulpin, *values in conn.execute(spec["existing"], ([r.ulpin for r in records],)):
            existing.setdefault(ulpin, []).append(values)

        to_insert, to_update, unchanged = [], [], 0
        for record in records:
            new_values = spec["values"](record)
            old_rows = existing.get(record.ulpin)
            if not old_rows:
                to_insert.append(new_values + (record.ulpin,))
            elif all(all(_same(n, o) for n, o in zip(new_values, old)) for old in old_rows):
                unchanged += 1
            else:
                to_update.append(new_values + (record.ulpin,))

        report.counts[table] = {"new": len(to_insert), "updated": len(to_update), "unchanged": unchanged}
        if not dry_run:
            with conn.cursor() as cur:
                cur.executemany(spec["update"], to_update)
                cur.executemany(spec["insert"], to_insert)
    return report


def format_report(report):
    lines = []
    if report.dry_run:
        lines.append("DRY RUN: nothing will be changed in the database.")
    lines.append(f"State: {report.state}    File: {report.path}")
    lines.append(f"Rows read: {report.rows_read}  |  good: {report.rows_read - len(report.rejected)}"
                 f"  |  rejected: {len(report.rejected)}")
    if report.rejected:
        lines.append("Rejected rows (not loaded):")
        lines += [f"  data row {r.row_number}: {r.reason}" for r in report.rejected]
    if report.unknown_ulpins:
        lines.append(f"Unknown ulpins (not in plots, skipped): {len(report.unknown_ulpins)}")
        lines += [f"  data row {n}: {u}" for n, u in report.unknown_ulpins]
    verb = ("would be", "were")[not report.dry_run]
    lines.append(f"Plots matched to the database: {report.plots_loaded}")
    for table, spec in _TABLES.items():
        c = report.counts[table]
        lines.append(f"  {spec['label']}: {c['new']} new, {c['updated']} updated, {c['unchanged']} unchanged")
    if report.dry_run:
        lines.append("Dry run finished. Nothing was written.")
    else:
        lines.append(f"Done. Records {verb} saved; running this again will change nothing.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m db.adapters.ingest",
                                     description="Load a state's raw land-record file into the database.")
    parser.add_argument("--state", required=True, help="maharashtra, karnataka or uttar_pradesh")
    parser.add_argument("--file", required=True, help="path to the raw file")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen; change nothing")
    args = parser.parse_args(argv)

    from backend.app.db import connect
    from . import get_adapter

    try:
        adapter = get_adapter(args.state)
        with connect() as conn:
            report = ingest(conn, adapter, args.file, dry_run=args.dry_run)
            if args.dry_run:
                conn.rollback()
    except (UnknownStateError, AdapterError) as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    except Exception as err:  # noqa: BLE001  (e.g. the database is down)
        print(f"ERROR: could not load the file: {type(err).__name__}: {err}", file=sys.stderr)
        return 1
    print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
