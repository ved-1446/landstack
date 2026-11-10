"""Phase 9: the `unusual` field on the passport, the PDF note, and the proof that it changes no score."""
import io
import re

import pytest
from pypdf import PdfReader

from backend.app import main, passport, unusual
from ml import make_dataset, train_unusual

ULPIN_IN_TEXT = re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{14}\b")


@pytest.fixture(scope="module")
def small_bundle():
    _ids, matrix, _labels = make_dataset.build(plots=400, rate=0.08, seed_value=4)
    return train_unusual.fit(matrix, seed=1)


@pytest.fixture
def model_off():
    unusual.use_bundle(None)
    yield
    unusual.use_bundle(None)


@pytest.fixture
def model_on(small_bundle):
    unusual.use_bundle(dict(small_bundle))
    yield
    unusual.use_bundle(None)


@pytest.fixture
def everything_flagged(small_bundle):
    unusual.use_bundle({**small_bundle, "threshold": -1.0})     # every plot is "unusual"
    yield
    unusual.use_bundle(None)


@pytest.fixture
def nothing_flagged(small_bundle):
    unusual.use_bundle({**small_bundle, "threshold": 99.0})
    yield
    unusual.use_bundle(None)


def get(client, auth, who, ulpin):
    r = client.get(f"/plots/{ulpin}", headers=auth(who))
    assert r.status_code == 200, r.text
    return r.json()


def pdf_text(client, auth, who, ulpin):
    r = client.get(f"/plots/{ulpin}/passport.pdf", headers=auth(who))
    assert r.status_code == 200
    return PdfReader(io.BytesIO(r.content)).pages[0].extract_text()


def test_the_test_run_starts_with_no_model(conn):
    assert unusual.model_dir().name == "landstack-no-model-here"
    assert unusual.load_model() is False and not unusual.is_loaded()


def test_no_model_means_null_and_the_api_works_normally(anon_client, auth, truth, model_off):
    ulpin = sorted(truth["conflicts"])[0]
    body = get(anon_client, auth, "officer", ulpin)
    assert body["unusual"] is None
    assert body["score"] > 0 and body["findings"]
    assert "Statistical note" not in pdf_text(anon_client, auth, "officer", ulpin)


def test_with_a_model_the_field_has_the_documented_shape(anon_client, auth, truth, model_on):
    seen_flag = seen_ok = 0
    for ulpin in sorted(truth["conflicts"])[:12]:
        u = get(anon_client, auth, "officer", ulpin)["unusual"]
        assert set(u) == {"flag", "percentile", "reasons"}
        assert isinstance(u["flag"], bool) and 0 <= u["percentile"] <= 100
        assert isinstance(u["reasons"], list) and len(u["reasons"]) <= 3
        assert bool(u["reasons"]) == u["flag"]                    # reasons only when flagged
        seen_flag += u["flag"]
        seen_ok += not u["flag"]
    assert seen_flag + seen_ok == 12


def test_scores_bands_and_findings_are_identical_with_and_without_the_model(anon_client, auth, conn, small_bundle):
    unusual.use_bundle(None)
    without_list = anon_client.get("/plots", headers=auth("admin")).json()
    ulpins = [f["properties"]["ulpin"] for f in without_list["features"]][:25]
    without = {u: get(anon_client, auth, "admin", u) for u in ulpins}
    without_summary = anon_client.get("/summary", headers=auth("admin")).json()
    full_without = {u: passport.load_passport(conn, u) for u in ulpins}

    unusual.use_bundle({**small_bundle, "threshold": -1.0})       # as many badges as possible
    try:
        with_list = anon_client.get("/plots", headers=auth("admin")).json()
        with_model = {u: get(anon_client, auth, "admin", u) for u in ulpins}
        with_summary = anon_client.get("/summary", headers=auth("admin")).json()
        full_with = {u: passport.load_passport(conn, u) for u in ulpins}
    finally:
        unusual.use_bundle(None)

    assert with_list == without_list and with_summary == without_summary
    for u in ulpins:
        a = {k: v for k, v in without[u].items() if k != "unusual"}
        b = {k: v for k, v in with_model[u].items() if k != "unusual"}
        assert a == b                                                     # score, band, findings, records: all equal
        assert with_model[u]["unusual"]["flag"] is True and without[u]["unusual"] is None
        assert "unusual" not in full_with[u]                              # never part of what is hashed
        assert passport.content_hash(full_with[u]) == passport.content_hash(full_without[u])


def test_an_old_printed_passport_still_verifies_after_the_model_changes(anon_client, auth, truth, small_bundle):
    ulpin = sorted(truth["conflicts"])[0]
    unusual.use_bundle(None)
    r = anon_client.get(f"/plots/{ulpin}/passport.pdf", headers=auth("officer"))
    doc_id = re.search(r"[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}", PdfReader(io.BytesIO(r.content)).pages[0].extract_text()).group(0)
    unusual.use_bundle({**small_bundle, "threshold": -1.0})
    try:
        assert anon_client.get(f"/verify/{doc_id}").json()["status"] == "matches"
    finally:
        unusual.use_bundle(None)


def test_the_pdf_note_only_appears_when_flagged(anon_client, auth, truth, everything_flagged):
    ulpin = sorted(truth["conflicts"])[0]
    text = pdf_text(anon_client, auth, "officer", ulpin)
    assert "Statistical note: unusual compared with other plots; not a conflict; adds no points." in text.replace("\n", " ")
    assert "Page 1 of 1" in text


def test_no_pdf_note_when_not_flagged(anon_client, auth, truth, nothing_flagged):
    ulpin = sorted(truth["conflicts"])[0]
    assert get(anon_client, auth, "officer", ulpin)["unusual"]["flag"] is False
    assert "Statistical note" not in pdf_text(anon_client, auth, "officer", ulpin)


def test_a_citizens_copy_never_mentions_other_plots(anon_client, auth, users, everything_flagged):
    a = users["citizen_a"]
    own = set(a["plots"])
    for ulpin in a["plots"]:
        body = get(anon_client, auth, "citizen_a", ulpin)
        assert body["unusual"]["flag"] is True
        blob = " ".join(body["unusual"]["reasons"])
        assert not ULPIN_IN_TEXT.findall(blob)
        text = pdf_text(anon_client, auth, "citizen_a", ulpin)
        assert "Statistical note" in text
        assert set(ULPIN_IN_TEXT.findall(text)) <= own                 # only the citizen's own plot id is printed


def test_a_citizen_still_gets_404_for_other_plots_with_the_model_on(anon_client, auth, users, model_on):
    other = users["citizen_b"]["plots"][0]
    assert anon_client.get(f"/plots/{other}", headers=auth("citizen_a")).status_code == 404


def test_a_failure_inside_the_model_code_never_breaks_the_passport(anon_client, auth, truth, small_bundle, monkeypatch):
    ulpin = sorted(truth["conflicts"])[0]
    unusual.use_bundle(dict(small_bundle))
    monkeypatch.setattr(unusual.features, "features_for_all", lambda *a, **k: 1 / 0)
    try:
        body = get(anon_client, auth, "officer", ulpin)
    finally:
        unusual.use_bundle(None)
    assert body["unusual"] is None and body["score"] > 0


def test_a_corrupt_model_file_is_ignored_at_load_time(small_bundle, tmp_path):
    train_unusual.save(small_bundle, tmp_path)
    (tmp_path / "unusual.joblib").write_bytes(b"this is not a model")
    assert unusual.load_model(tmp_path) is False and not unusual.is_loaded()
    assert unusual.load_model(tmp_path / "empty") is False


def test_a_good_model_file_loads_once_and_serves(small_bundle, tmp_path):
    train_unusual.save(small_bundle, tmp_path)
    try:
        assert unusual.load_model(tmp_path) is True and unusual.is_loaded()
    finally:
        unusual.use_bundle(None)


def test_the_response_model_documents_the_field():
    schema = main.Passport.model_json_schema()
    assert "unusual" in schema["properties"]
    assert set(main.Unusual.model_fields) == {"flag", "percentile", "reasons"}
