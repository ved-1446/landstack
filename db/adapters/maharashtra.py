"""Maharashtra: a CSV in the style of a 7/12 extract (fake sample).

Columns: ulpin, owner_name, hectare, are, reg_owner_name, reg_date, tax_paid_until
- owner_name is written surname first ("Kulkarni Ramesh")
- area is split over two columns: hectares and ares (1 hectare = 100 ares). If one is blank it counts as 0.
- dates are DD/MM/YYYY
"""
import csv

from . import units
from .base import AdapterError, BaseAdapter
from .formats import clean_text, parse_dd_mm_yyyy, parse_number, surname_first_to_standard

COLUMNS = ["ulpin", "owner_name", "hectare", "are", "reg_owner_name", "reg_date", "tax_paid_until"]


class MaharashtraAdapter(BaseAdapter):
    state = "maharashtra"

    def read_rows(self, path):
        try:
            with open(path, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                missing = [c for c in COLUMNS if c not in (reader.fieldnames or [])]
                if missing:
                    raise AdapterError(f"Maharashtra CSV is missing column(s): {', '.join(missing)}")
                for number, row in enumerate(reader, start=1):
                    yield number, row
        except (OSError, UnicodeDecodeError, csv.Error) as err:
            raise AdapterError(f"cannot read the Maharashtra CSV: {err}") from err

    def convert(self, raw, row_number):
        hectare = parse_number(raw.get("hectare"), "hectare")
        are = parse_number(raw.get("are"), "are")
        area = None
        if hectare is not None or are is not None:
            area = units.hectares_ares_to_sqm(hectare or 0, are or 0)

        owner = clean_text(raw.get("owner_name"))
        reg_owner = clean_text(raw.get("reg_owner_name"))
        return self.assemble(
            row_number,
            raw.get("ulpin"),
            surname_first_to_standard(owner) if owner else None,
            area,
            surname_first_to_standard(reg_owner) if reg_owner else None,
            parse_dd_mm_yyyy(raw.get("reg_date"), "registration date"),
            parse_dd_mm_yyyy(raw.get("tax_paid_until"), "tax paid-until date"),
        )
