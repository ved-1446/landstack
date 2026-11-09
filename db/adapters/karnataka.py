"""Karnataka: a JSON file in the style of an RTC (fake sample).

{"state": "Karnataka", "records": [
  {"ulpin": "...", "owner": "KULKARNI, RAMESH", "acres": 0, "guntas": 18.2,
   "reg_owner": "KULKARNI, RAMESH", "reg_date": "2014-09-22", "tax_paid_until": "2026-01-06"}, ...]}
- owners are written "SURNAME, GIVEN NAMES" in capitals
- area is acres and guntas (1 acre = 4046.8564224 sq m, 1 guntha = 101.17 sq m). A blank part counts as 0.
- dates are YYYY-MM-DD
"""
import json

from . import units
from .base import AdapterError, BaseAdapter, RowError
from .formats import clean_text, karnataka_to_standard, parse_iso_date, parse_number


class KarnatakaAdapter(BaseAdapter):
    state = "karnataka"

    def read_rows(self, path):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError) as err:
            raise AdapterError(f"cannot read the Karnataka file: {err}") from err
        except json.JSONDecodeError as err:
            raise AdapterError(f"the Karnataka file is not valid JSON: {err}") from err
        if not isinstance(data, dict) or not isinstance(data.get("records"), list):
            raise AdapterError("the Karnataka file must be a JSON object with a 'records' list")
        yield from enumerate(data["records"], start=1)

    def convert(self, raw, row_number):
        if not isinstance(raw, dict):
            raise RowError("record is not a JSON object")
        acres = parse_number(raw.get("acres"), "acres")
        guntas = parse_number(raw.get("guntas"), "guntas")
        area = None
        if acres is not None or guntas is not None:
            area = units.acres_guntas_to_sqm(acres or 0, guntas or 0)

        owner = clean_text(raw.get("owner"))
        reg_owner = clean_text(raw.get("reg_owner"))
        return self.assemble(
            row_number,
            raw.get("ulpin"),
            karnataka_to_standard(owner) if owner else None,
            area,
            karnataka_to_standard(reg_owner) if reg_owner else None,
            parse_iso_date(raw.get("reg_date"), "registration date"),
            parse_iso_date(raw.get("tax_paid_until"), "tax paid-until date"),
        )
