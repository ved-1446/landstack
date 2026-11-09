"""Name matcher tests (no database needed)."""
import pytest

from backend.app import config, names


def test_normalise():
    assert names.normalise("Kulkarni, Ramesh S.") == "kulkarni ramesh"
    assert names.normalise("Anita D Patil") == "anita patil"


def test_decoy_pairs_match(truth):
    assert len(truth["decoys"]) == 6
    for d in truth["decoys"]:
        same, score = names.same_person(d["ror_owner"], d["registration_owner"])
        assert same, (d, score)


def test_genuinely_different_owners_do_not_match():
    from backend.tests import conftest  # noqa: F401  (ensures paths)
    import seed
    data = seed.generate()
    ror = {r["ulpin"]: r["owner_name"] for r in data["rows"]["ror_records"]}
    reg = {r["ulpin"]: r["owner_name"] for r in data["rows"]["registrations"]}
    planted = [u for u, t in data["truth"]["conflicts"].items() if t == ["owner_mismatch"]]
    assert len(planted) == 4
    for u in planted:
        same, score = names.same_person(ror[u], reg[u])
        assert not same, (ror[u], reg[u], score)


def test_threshold_sits_between_decoys_and_mismatches():
    assert 0.2 < config.NAME_MATCH_THRESHOLD < 1.0


@pytest.mark.parametrize("a,b", [("", "Amit Pawar"), ("A.", "Amit Pawar")])
def test_empty_after_normalising_is_not_a_match(a, b):
    assert names.same_person(a, b) == (False, 0.0)
