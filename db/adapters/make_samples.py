"""Write demo files: the records of the first 20 plots in the database, shown in three state styles.

    python -m db.adapters.make_samples

This is a FORMAT DEMO: the same 20 plots appear in a Maharashtra CSV, a Karnataka JSON and an
Uttar Pradesh JSON, so you can see how the raw styles differ. It is deterministic: the same
database content always produces byte-for-byte identical files. These are made-up formats
inspired by the real documents, not copies of them.
"""
import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import units
from .formats import (format_dd_mm_yyyy, format_dd_mon_yyyy, format_iso_date, standard_to_karnataka,
                      standard_to_surname_first)
from .maharashtra import COLUMNS as MAHARASHTRA_COLUMNS

SAMPLE_PLOTS = 20
SAMPLES_DIR = Path(__file__).resolve().parent / "samples"
CO_OWNER = "Smt. Kamla Devi"  # added to every 3rd plot in the Uttar Pradesh sample, to show "use the first owner"


@dataclass(frozen=True)
class OriginalPlot:
    """What the database holds for one plot. None = that record is missing."""
    ulpin: str
    ror_owner: str | None
    area_sqm: float | None
    reg_owner: str | None
    registered_on: date | None
    paid_until: date | None


def fetch_originals(conn, limit=SAMPLE_PLOTS):
    rows = conn.execute(
        """
        SELECT p.ulpin, r.owner_name, r.recorded_area_sqm, g.owner_name, g.registered_on, t.paid_until
        FROM (SELECT ulpin FROM plots ORDER BY ulpin LIMIT %s) p
        LEFT JOIN ror_records r ON r.ulpin = p.ulpin
        LEFT JOIN registrations g ON g.ulpin = p.ulpin
        LEFT JOIN tax_records t ON t.ulpin = p.ulpin
        ORDER BY p.ulpin
        """,
        (limit,),
    ).fetchall()
    return [OriginalPlot(u, ro, None if a is None else float(a), go, d, t) for u, ro, a, go, d, t in rows]


# ---- one plot -> one raw row, per state style ----

def to_raw_maharashtra(p):
    hectare = are = ""
    if p.area_sqm is not None:
        h, a = units.sqm_to_hectares_ares(p.area_sqm)
        hectare, are = str(h), f"{a:.4f}"
    return {
        "ulpin": p.ulpin,
        "owner_name": standard_to_surname_first(p.ror_owner) if p.ror_owner else "",
        "hectare": hectare,
        "are": are,
        "reg_owner_name": standard_to_surname_first(p.reg_owner) if p.reg_owner else "",
        "reg_date": format_dd_mm_yyyy(p.registered_on) if p.registered_on else "",
        "tax_paid_until": format_dd_mm_yyyy(p.paid_until) if p.paid_until else "",
    }


def to_raw_karnataka(p):
    acres = guntas = None
    if p.area_sqm is not None:
        acres, guntas = units.sqm_to_acres_guntas(p.area_sqm)
        guntas = round(guntas, 4)
    return {
        "ulpin": p.ulpin,
        "owner": standard_to_karnataka(p.ror_owner) if p.ror_owner else None,
        "acres": acres,
        "guntas": guntas,
        "reg_owner": standard_to_karnataka(p.reg_owner) if p.reg_owner else None,
        "reg_date": format_iso_date(p.registered_on) if p.registered_on else None,
        "tax_paid_until": format_iso_date(p.paid_until) if p.paid_until else None,
    }


def to_raw_uttar_pradesh(p, with_co_owner=False):
    owners = [p.ror_owner] if p.ror_owner else []
    if owners and with_co_owner:
        owners.append(CO_OWNER)
    area = "" if p.area_sqm is None else f"{units.sqm_to_hectares(p.area_sqm):.6f}".replace(".", ",")
    return {
        "ulpin": p.ulpin,
        "land": {"area_hectare": area},
        "owners": owners,
        "registry": {"buyer": p.reg_owner or "",
                     "date": format_dd_mon_yyyy(p.registered_on) if p.registered_on else ""},
        "tax": {"paid_until": format_dd_mon_yyyy(p.paid_until) if p.paid_until else ""},
    }


# ---- raw rows -> a file ----

def write_maharashtra(raw_rows, path):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAHARASHTRA_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(raw_rows)


def _write_json(document, path):
    Path(path).write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_karnataka(raw_rows, path):
    _write_json({"state": "Karnataka", "source": "RTC style (fake sample)", "records": raw_rows}, path)


def write_uttar_pradesh(raw_rows, path):
    _write_json({"state": "Uttar Pradesh", "source": "Khatauni style (fake sample)", "khatauni": raw_rows}, path)


def export_all(originals, out_dir=SAMPLES_DIR):
    """Write the three sample files. Returns {state: path}."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "maharashtra": out_dir / "maharashtra_sample.csv",
        "karnataka": out_dir / "karnataka_sample.json",
        "uttar_pradesh": out_dir / "uttar_pradesh_sample.json",
    }
    write_maharashtra([to_raw_maharashtra(p) for p in originals], paths["maharashtra"])
    write_karnataka([to_raw_karnataka(p) for p in originals], paths["karnataka"])
    write_uttar_pradesh(
        [to_raw_uttar_pradesh(p, with_co_owner=(i % 3 == 2)) for i, p in enumerate(originals)],
        paths["uttar_pradesh"])
    return paths


def main():
    from backend.app.db import connect
    with connect() as conn:
        originals = fetch_originals(conn)
    paths = export_all(originals)
    print(f"Wrote samples for {len(originals)} plots:")
    for state, path in paths.items():
        print(f"  {state:<14} {path}")


if __name__ == "__main__":
    main()
