"""The adapter contract.

An adapter reads ONE state's raw file and returns our standard records, plus a list of rows
it had to reject (with a row number and a plain reason). Bad rows never crash the run.

Standard records mirror the three record tables:
    RorRecord          -> ror_records(ulpin, owner_name, recorded_area_sqm)
    RegistrationRecord -> registrations(ulpin, owner_name, registered_on)
    TaxRecord          -> tax_records(ulpin, paid_until)
Areas are always square metres. A raw row can leave any of the three out (a missing record).

"Row number" means the Nth data row of the file, counting from 1 (the CSV header is not a row).
"""
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ULPIN_RE = re.compile(r"^[A-Z0-9]{14}$")
MAX_AREA_SQM = 1_000_000_000  # 100,000 hectares; anything bigger is a typo (and would not fit the table)


class RowError(Exception):
    """One raw row is bad. The message is the plain-words reason shown to the user."""


class AdapterError(Exception):
    """The whole file is unusable (missing, not valid JSON, wrong columns...)."""


class UnknownStateError(ValueError):
    """get_adapter() was asked for a state that has no adapter."""


@dataclass(frozen=True)
class RorRecord:
    ulpin: str
    owner_name: str
    recorded_area_sqm: float


@dataclass(frozen=True)
class RegistrationRecord:
    ulpin: str
    owner_name: str
    registered_on: date


@dataclass(frozen=True)
class TaxRecord:
    ulpin: str
    paid_until: date


@dataclass(frozen=True)
class RejectedRow:
    row_number: int
    reason: str


@dataclass(frozen=True)
class StandardRow:
    """Everything one raw row said about one plot. Any record may be None (missing)."""
    row_number: int
    ulpin: str
    ror: RorRecord | None
    registration: RegistrationRecord | None
    tax: TaxRecord | None


@dataclass
class AdapterResult:
    state: str
    rows_read: int
    rows: list[StandardRow] = field(default_factory=list)
    rejected: list[RejectedRow] = field(default_factory=list)

    @property
    def ror_records(self):
        return [r.ror for r in self.rows if r.ror]

    @property
    def registrations(self):
        return [r.registration for r in self.rows if r.registration]

    @property
    def tax_records(self):
        return [r.tax for r in self.rows if r.tax]


class BaseAdapter(ABC):
    """Subclasses only say how to READ rows and how to CONVERT one raw row.
    The loop, the rejecting and the shared checks live here, so every state behaves the same."""

    state: str  # e.g. "maharashtra"

    @abstractmethod
    def read_rows(self, path: Path):
        """Yield (row_number, raw_row) for every data row. Raise AdapterError if the file is unusable."""

    @abstractmethod
    def convert(self, raw, row_number: int) -> StandardRow:
        """Turn one raw row into a StandardRow (use self.assemble). Raise RowError if it is bad."""

    def parse(self, path) -> AdapterResult:
        path = Path(path)
        if not path.is_file():
            raise AdapterError(f"file not found: {path}")
        rows, rejected, first_seen = [], [], {}
        count = 0
        for count, raw in self.read_rows(path):
            try:
                row = self.convert(raw, count)
                if row.ulpin in first_seen:
                    raise RowError(f"ulpin {row.ulpin} already appears on data row {first_seen[row.ulpin]}")
                first_seen[row.ulpin] = count
                rows.append(row)
            except RowError as err:
                rejected.append(RejectedRow(count, str(err)))
            except Exception as err:  # noqa: BLE001  (a surprise in one row must not stop the others)
                rejected.append(RejectedRow(count, f"unexpected problem ({type(err).__name__}): {err}"))
        return AdapterResult(self.state, count, rows, rejected)

    @staticmethod
    def assemble(row_number, ulpin, ror_owner, area_sqm, reg_owner, registered_on, paid_until):
        """Shared checks. Values are already converted (area in sq m, dates as date objects).
        A part with nothing in it is simply a missing record; a half-filled part is an error."""
        ulpin = (ulpin or "").strip().upper()
        if not ulpin:
            raise RowError("ulpin is missing")
        if not ULPIN_RE.match(ulpin):
            raise RowError(f"ulpin '{ulpin}' is not a 14-character ULPIN (letters and digits)")

        ror = None
        if ror_owner or area_sqm is not None:
            if not ror_owner:
                raise RowError("land record has an area but no owner name")
            if area_sqm is None:
                raise RowError("land record has an owner name but no area")
            area = round(area_sqm, 2)
            if area <= 0:
                raise RowError(f"area must be more than zero (got {area_sqm:g} sq m)")
            if area > MAX_AREA_SQM:
                raise RowError(f"area {area_sqm:,.0f} sq m is unrealistically large")
            ror = RorRecord(ulpin, ror_owner, area)

        registration = None
        if reg_owner or registered_on:
            if not reg_owner:
                raise RowError("registration has a date but no owner name")
            if not registered_on:
                raise RowError("registration has an owner name but no date")
            registration = RegistrationRecord(ulpin, reg_owner, registered_on)

        tax = TaxRecord(ulpin, paid_until) if paid_until else None
        return StandardRow(row_number, ulpin, ror, registration, tax)
