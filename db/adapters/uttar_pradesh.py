"""Uttar Pradesh: a nested JSON file in the style of a Khatauni (fake sample).

{"state": "Uttar Pradesh", "khatauni": [
  {"ulpin": "...",
   "land":     {"area_hectare": "0,18457"},
   "owners":   ["Ramesh Kulkarni", "Smt. Kamla Devi"],
   "registry": {"buyer": "Ramesh Kulkarni", "date": "22-Sep-2014"},
   "tax":      {"paid_until": "06-Jan-2026"}}, ...]}
- area is hectares written as a string with a COMMA as the decimal mark ("0,18457")
- owners is a list; the FIRST one is the main owner (the others are ignored)
- dates are DD-Mon-YYYY
"""
import json

from . import units
from .base import AdapterError, BaseAdapter, RowError
from .formats import clean_text, parse_dd_mon_yyyy, parse_number


def _section(raw, key):
    value = raw.get(key)
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RowError(f"'{key}' should be an object")
    return value


class UttarPradeshAdapter(BaseAdapter):
    state = "uttar_pradesh"

    def read_rows(self, path):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError) as err:
            raise AdapterError(f"cannot read the Uttar Pradesh file: {err}") from err
        except json.JSONDecodeError as err:
            raise AdapterError(f"the Uttar Pradesh file is not valid JSON: {err}") from err
        if not isinstance(data, dict) or not isinstance(data.get("khatauni"), list):
            raise AdapterError("the Uttar Pradesh file must be a JSON object with a 'khatauni' list")
        yield from enumerate(data["khatauni"], start=1)

    def convert(self, raw, row_number):
        if not isinstance(raw, dict):
            raise RowError("record is not a JSON object")
        land, registry, tax = _section(raw, "land"), _section(raw, "registry"), _section(raw, "tax")

        hectares = parse_number(land.get("area_hectare"), "area_hectare", comma_decimal=True)
        area = None if hectares is None else units.hectares_to_sqm(hectares)

        owners = raw.get("owners")
        if owners is None:
            owners = []
        if not isinstance(owners, list):
            raise RowError("'owners' should be a list")
        main_owner = None
        if owners:
            if not isinstance(owners[0], str):
                raise RowError("the first owner is not text")
            main_owner = clean_text(owners[0])

        return self.assemble(
            row_number,
            raw.get("ulpin"),
            main_owner,
            area,
            clean_text(registry.get("buyer")),
            parse_dd_mon_yyyy(registry.get("date"), "registration date"),
            parse_dd_mon_yyyy(tax.get("paid_until"), "tax paid-until date"),
        )
