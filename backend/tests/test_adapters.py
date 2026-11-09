"""State adapters and ingest.

Pure tests need no database. Tests that use the database (round trip, ingest) run on the live
Docker database and skip if it is down. Anything that writes happens in a transaction that is
rolled back, and the tests check the tables afterwards, so planted_truth.json still matches.
"""
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from backend.app import db as appdb
from db.adapters import AdapterError, BaseAdapter, UnknownStateError, available_states, get_adapter
from db.adapters import make_samples as ms
from db.adapters.ingest import format_report, ingest

ROOT = Path(__file__).resolve().parents[2]
STATES = ["maharashtra", "karnataka", "uttar_pradesh"]
WRITERS = {"maharashtra": ms.write_maharashtra, "karnataka": ms.write_karnataka,
           "uttar_pradesh": ms.write_uttar_pradesh}
TO_RAW = {"maharashtra": ms.to_raw_maharashtra, "karnataka": ms.to_raw_karnataka,
          "uttar_pradesh": ms.to_raw_uttar_pradesh}

P1 = ms.OriginalPlot("MH000100000002", "Ramesh Kulkarni", 1845.65, "Ramesh Kulkarni",
                     date(2014, 9, 22), date(2026, 1, 6))
P2 = ms.OriginalPlot("MH000100000003", "Anita Patil", 1500.0, "Anita D Patil",
                     date(2020, 3, 1), date(2025, 12, 31))
P3 = ms.OriginalPlot("MH000100000004", "Amit Pawar", 900.5, "Amit Pawar",
                     date(2011, 7, 15), date(2026, 6, 30))


def write_raw(state, raw_rows, path):
    WRITERS[state](raw_rows, path)
    return path


# ======================= registry and contract =======================

def test_registry_knows_three_states():
    assert available_states() == ["karnataka", "maharashtra", "uttar_pradesh"]
    for state in STATES:
        assert get_adapter(state).state == state


def test_registry_accepts_friendly_spellings():
    assert get_adapter("Uttar Pradesh").state == "uttar_pradesh"
    assert get_adapter(" MAHARASHTRA ").state == "maharashtra"


def test_unknown_state_gives_a_clear_error():
    with pytest.raises(UnknownStateError) as err:
        get_adapter("goa")
    assert "Unknown state 'goa'" in str(err.value)
    assert "karnataka, maharashtra, uttar_pradesh" in str(err.value)


def test_base_class_cannot_be_used_directly():
    with pytest.raises(TypeError):
        BaseAdapter()

    class HalfDone(BaseAdapter):
        state = "x"
    with pytest.raises(TypeError):
        HalfDone()


# ======================= reading hand-written raw files =======================
# These raw files are written by hand (not by make_samples), with answers worked out by hand.

def test_maharashtra_hand_written(tmp_path):
    f = tmp_path / "m.csv"
    f.write_text(
        "ulpin,owner_name,hectare,are,reg_owner_name,reg_date,tax_paid_until\n"
        "MH000100000002,Kulkarni Ramesh,0,18.4565,Kulkarni Ramesh,22/09/2014,06/01/2026\n"
        "MH000100000003,Patil Anita,1,50,Patil Anita,01/03/2020,31/12/2025\n",
        encoding="utf-8")
    result = get_adapter("maharashtra").parse(f)
    assert result.rejected == []
    first, second = result.rows
    assert first.ror.owner_name == "Ramesh Kulkarni"
    assert first.ror.recorded_area_sqm == 1845.65
    assert first.registration.registered_on == date(2014, 9, 22)
    assert first.tax.paid_until == date(2026, 1, 6)
    assert second.ror.recorded_area_sqm == 15_000.0  # 1 hectare + 50 ares


def test_karnataka_hand_written(tmp_path):
    f = tmp_path / "k.json"
    f.write_text(json.dumps({"records": [{
        "ulpin": "MH000100000002", "owner": "KULKARNI, RAMESH", "acres": 1, "guntas": 10,
        "reg_owner": "PAWAR, AMIT", "reg_date": "2014-09-22", "tax_paid_until": "2026-01-06"}]}))
    row = get_adapter("karnataka").parse(f).rows[0]
    assert row.ror.owner_name == "Ramesh Kulkarni"
    assert row.ror.recorded_area_sqm == 5058.56       # 4046.8564224 + 10 * 101.17
    assert row.registration.owner_name == "Amit Pawar"  # a different person: stays different
    assert row.registration.registered_on == date(2014, 9, 22)


def test_uttar_pradesh_hand_written_uses_first_owner(tmp_path):
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"khatauni": [{
        "ulpin": "MH000100000002", "land": {"area_hectare": "0,1846"},
        "owners": ["Ramesh Kulkarni", "Smt. Kamla Devi"],
        "registry": {"buyer": "Ramesh Kulkarni", "date": "22-Sep-2014"},
        "tax": {"paid_until": "06-JAN-2026"}}]}))
    row = get_adapter("uttar_pradesh").parse(f).rows[0]
    assert row.ror.owner_name == "Ramesh Kulkarni"
    assert row.ror.recorded_area_sqm == 1846.0
    assert row.registration.registered_on == date(2014, 9, 22)
    assert row.tax.paid_until == date(2026, 1, 6)


@pytest.mark.parametrize("state", STATES)
def test_missing_records_come_back_as_none(state, tmp_path):
    empty = ms.OriginalPlot("MH000100000009", None, None, None, None, None)
    path = write_raw(state, [TO_RAW[state](empty), TO_RAW[state](P1)], tmp_path / "f")
    result = get_adapter(state).parse(path)
    assert result.rejected == []
    gone, present = result.rows
    assert (gone.ror, gone.registration, gone.tax) == (None, None, None)
    assert present.ror and present.registration and present.tax


# ======================= bad rows are collected, good rows still load =======================

CORRUPTIONS = {
    "maharashtra": {
        "bad_date": lambda r: r.update(reg_date="31/02/2024"),
        "negative_area": lambda r: r.update(hectare="-1"),
        "zero_area": lambda r: r.update(hectare="0", are="0"),
        "missing_ulpin": lambda r: r.update(ulpin=""),
        "unreadable_number": lambda r: r.update(are="12abc"),
        "owner_without_area": lambda r: r.update(hectare="", are=""),
    },
    "karnataka": {
        "bad_date": lambda r: r.update(reg_date="2024-02-31"),
        "negative_area": lambda r: r.update(acres=-2),
        "zero_area": lambda r: r.update(acres=0, guntas=0),
        "missing_ulpin": lambda r: r.update(ulpin=None),
        "unreadable_number": lambda r: r.update(guntas="ten"),
        "owner_without_area": lambda r: r.update(acres=None, guntas=None),
    },
    "uttar_pradesh": {
        "bad_date": lambda r: r["registry"].update(date="31-Feb-2024"),
        "negative_area": lambda r: r["land"].update(area_hectare="-0,5"),
        "zero_area": lambda r: r["land"].update(area_hectare="0,0"),
        "missing_ulpin": lambda r: r.pop("ulpin"),
        "unreadable_number": lambda r: r["land"].update(area_hectare="0,18,5"),
        "owner_without_area": lambda r: r["land"].update(area_hectare=""),
    },
}
REASON = {
    "bad_date": "not a real calendar date",
    "negative_area": "negative",
    "zero_area": "more than zero",
    "missing_ulpin": "ulpin is missing",
    "unreadable_number": "is not a number",
    "owner_without_area": "owner name but no area",
}


@pytest.mark.parametrize("kind", sorted(REASON))
@pytest.mark.parametrize("state", STATES)
def test_bad_row_is_rejected_and_good_rows_still_load(state, kind, tmp_path):
    good_before, bad, good_after = TO_RAW[state](P1), TO_RAW[state](P2), TO_RAW[state](P3)
    CORRUPTIONS[state][kind](bad)
    result = get_adapter(state).parse(write_raw(state, [good_before, bad, good_after], tmp_path / "f"))

    assert result.rows_read == 3
    assert [r.ulpin for r in result.rows] == [P1.ulpin, P3.ulpin]   # the good rows around it loaded
    assert [r.row_number for r in result.rows] == [1, 3]
    assert len(result.rejected) == 1
    assert result.rejected[0].row_number == 2
    assert REASON[kind] in result.rejected[0].reason


@pytest.mark.parametrize("state", STATES)
def test_malformed_ulpin_and_duplicate_ulpin_are_rejected(state, tmp_path):
    short = TO_RAW[state](P2)
    short["ulpin"] = "MH123"
    dup = TO_RAW[state](P1)
    result = get_adapter(state).parse(write_raw(state, [TO_RAW[state](P1), short, dup], tmp_path / "f"))
    assert [r.ulpin for r in result.rows] == [P1.ulpin]
    assert "not a 14-character ULPIN" in result.rejected[0].reason
    assert "already appears on data row 1" in result.rejected[1].reason


def test_unusual_rows_never_crash(tmp_path):
    f = tmp_path / "k.json"
    f.write_text(json.dumps({"records": ["not an object", 42, None, {"ulpin": "MH000100000002", "acres": 1e30,
                                                                     "guntas": 0, "owner": "A B"}]}))
    result = get_adapter("karnataka").parse(f)
    assert result.rows == []
    assert len(result.rejected) == 4
    assert "not a JSON object" in result.rejected[0].reason
    assert "unrealistically large" in result.rejected[3].reason


@pytest.mark.parametrize("state,text,reason", [
    ("maharashtra", "ulpin,owner_name\nMH000100000002,X Y\n", "missing column"),
    ("karnataka", "{not json", "not valid JSON"),
    ("karnataka", '{"rows": []}', "'records' list"),
    ("uttar_pradesh", "[1, 2]", "'khatauni' list"),
])
def test_unusable_files_give_one_clear_error(state, text, reason, tmp_path):
    f = tmp_path / "bad"
    f.write_text(text)
    with pytest.raises(AdapterError, match=reason):
        get_adapter(state).parse(f)


def test_missing_file_gives_a_clear_error(tmp_path):
    with pytest.raises(AdapterError, match="file not found"):
        get_adapter("maharashtra").parse(tmp_path / "nope.csv")


# ======================= round trip (database -> raw style -> adapter -> standard) =======================

@pytest.fixture(scope="module")
def originals(conn):
    found = ms.fetch_originals(conn)
    assert len(found) == ms.SAMPLE_PLOTS == 20
    return found


@pytest.mark.parametrize("state", STATES)
def test_round_trip_equals_the_original_records(state, originals, tmp_path):
    paths = ms.export_all(originals, tmp_path)
    result = get_adapter(state).parse(paths[state])

    assert result.rows_read == 20 and result.rejected == []
    by_ulpin = {row.ulpin: row for row in result.rows}
    assert set(by_ulpin) == {p.ulpin for p in originals}
    worst = 0.0
    for p in originals:
        row = by_ulpin[p.ulpin]
        if p.area_sqm is None:
            assert row.ror is None
        else:
            assert row.ror.owner_name == p.ror_owner
            worst = max(worst, abs(row.ror.recorded_area_sqm - p.area_sqm))
        if p.reg_owner is None:
            assert row.registration is None
        else:
            assert (row.registration.owner_name, row.registration.registered_on) == (p.reg_owner, p.registered_on)
        assert (row.tax.paid_until if row.tax else None) == p.paid_until
    assert worst <= 0.5            # the requirement
    assert worst <= 0.011          # in practice it is exact to the cent


def test_the_sample_set_contains_a_missing_record_and_a_decoy_name(originals):
    assert any(p.area_sqm is None for p in originals)                 # a plot with no land record
    assert any(p.ror_owner != p.reg_owner for p in originals)         # a same-person-spelled-differently pair


def test_uttar_pradesh_sample_really_has_co_owners(tmp_path, originals):
    path = ms.export_all(originals, tmp_path)["uttar_pradesh"]
    owners = [r["owners"] for r in json.loads(path.read_text(encoding="utf-8"))["khatauni"]]
    assert any(len(o) == 2 for o in owners)


def test_samples_are_deterministic_and_up_to_date(originals, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    pa, pb = ms.export_all(originals, a), ms.export_all(originals, b)
    for state in STATES:
        assert pa[state].read_bytes() == pb[state].read_bytes()
        committed = ms.SAMPLES_DIR / pa[state].name
        assert committed.read_bytes() == pa[state].read_bytes(), "samples/ is stale: run make_samples"


# ======================= ingest =======================

TABLES = ["plots", "ror_records", "registrations", "tax_records", "zones"]


def snapshot(connection):
    return {t: connection.execute(f"SELECT * FROM {t} ORDER BY 1, 2, 3").fetchall() for t in TABLES[1:4]} | {
        "plots": connection.execute("SELECT ulpin FROM plots ORDER BY ulpin").fetchall()}


@pytest.fixture
def tx(conn):
    """A second connection with a real transaction that is ALWAYS rolled back at the end."""
    connection = appdb.connect()
    yield connection
    connection.rollback()
    connection.close()


@pytest.fixture
def messy_file(originals, tmp_path):
    """A Maharashtra file with: 1 new land record, 1 changed area, 1 unknown ulpin, 1 bad row, rest unchanged."""
    first, second, third, *rest = originals
    assert first.area_sqm is None                    # the plot that has no land record in the database
    new_ror = ms.OriginalPlot(first.ulpin, "Test Owner", 2000.0, first.reg_owner, first.registered_on, first.paid_until)
    changed = ms.OriginalPlot(second.ulpin, second.ror_owner, second.area_sqm + 100, second.reg_owner,
                              second.registered_on, second.paid_until)
    stranger = ms.OriginalPlot("MH999999999999", "Nobody Known", 500.0, "Nobody Known",
                               date(2020, 1, 1), date(2026, 1, 1))
    raws = [ms.to_raw_maharashtra(p) for p in [new_ror, changed, third, *rest, stranger]]
    bad = ms.to_raw_maharashtra(third)
    bad["ulpin"] = "MH000100000099"
    bad["reg_date"] = "99/99/2020"
    raws.append(bad)
    return write_raw("maharashtra", raws, tmp_path / "messy.csv"), changed


def test_ingest_of_an_unchanged_sample_changes_nothing(tx, conn):
    before = snapshot(conn)
    report = ingest(tx, get_adapter("karnataka"), ms.SAMPLES_DIR / "karnataka_sample.json")
    assert report.rejected == [] and report.unknown_ulpins == []
    assert report.counts["ror_records"] == {"new": 0, "updated": 0, "unchanged": 19}
    assert report.counts["registrations"] == {"new": 0, "updated": 0, "unchanged": 20}
    assert report.counts["tax_records"] == {"new": 0, "updated": 0, "unchanged": 20}
    assert snapshot(tx) == before


def test_ingest_reports_new_updated_unknown_and_rejected(tx, messy_file):
    path, changed = messy_file
    report = ingest(tx, get_adapter("maharashtra"), path)
    assert report.counts["ror_records"] == {"new": 1, "updated": 1, "unchanged": 18}
    assert report.counts["registrations"] == {"new": 0, "updated": 0, "unchanged": 20}
    assert report.rows_read == 22                      # 3 + 17 untouched + 1 stranger + 1 bad row
    assert report.unknown_ulpins == [(21, "MH999999999999")]
    assert [r.row_number for r in report.rejected] == [22]
    assert "not a real calendar date" in report.rejected[0].reason
    area = tx.execute("SELECT recorded_area_sqm FROM ror_records WHERE ulpin = %s", (changed.ulpin,)).fetchone()[0]
    assert float(area) == pytest.approx(changed.area_sqm, abs=0.01)
    assert tx.execute("SELECT count(*) FROM plots WHERE ulpin = 'MH999999999999'").fetchone()[0] == 0


def test_ingest_twice_gives_no_duplicates(tx, conn, messy_file):
    path, _ = messy_file
    before = snapshot(conn)
    ingest(tx, get_adapter("maharashtra"), path)
    after_first = snapshot(tx)
    second = ingest(tx, get_adapter("maharashtra"), path)
    assert snapshot(tx) == after_first                                   # nothing changed the second time
    assert all(c["new"] == 0 and c["updated"] == 0 for c in second.counts.values())
    assert len(after_first["ror_records"]) == len(before["ror_records"]) + 1   # one new record, not two
    assert len({r[1] for r in after_first["ror_records"]}) == len(after_first["ror_records"])  # one per ulpin
    tx.rollback()
    assert snapshot(conn) == before                                      # the database is back as it was


def test_dry_run_changes_nothing_but_reports_what_would_happen(tx, conn, messy_file):
    path, _ = messy_file
    before = snapshot(conn)
    report = ingest(tx, get_adapter("maharashtra"), path, dry_run=True)
    assert report.dry_run
    assert report.counts["ror_records"] == {"new": 1, "updated": 1, "unchanged": 18}
    assert snapshot(tx) == before
    text = format_report(report)
    assert "DRY RUN" in text and "Nothing was written" in text and "1 new, 1 updated, 18 unchanged" in text
    tx.rollback()
    assert snapshot(conn) == before


def _run_cli(*args):
    return subprocess.run([sys.executable, "-m", "db.adapters.ingest", *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)


def test_cli_dry_run(conn):
    before = snapshot(conn)
    done = _run_cli("--state", "uttar_pradesh", "--file", str(ms.SAMPLES_DIR / "uttar_pradesh_sample.json"), "--dry-run")
    assert done.returncode == 0, done.stderr
    assert "DRY RUN" in done.stdout and "0 new, 0 updated" in done.stdout
    assert snapshot(conn) == before


def test_cli_errors_are_plain_messages_not_tracebacks(conn):
    unknown = _run_cli("--state", "goa", "--file", "x", "--dry-run")
    assert unknown.returncode == 1 and "Unknown state 'goa'" in unknown.stderr
    missing = _run_cli("--state", "karnataka", "--file", "no_such_file.json", "--dry-run")
    assert missing.returncode == 1 and "file not found" in missing.stderr
    assert "Traceback" not in unknown.stderr + missing.stderr
