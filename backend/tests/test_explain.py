"""Phase 11, Part A: the LLM client, the explainer and POST /plots/{ulpin}/explain.
The LLM is ALWAYS mocked: conftest blocks the one network function, so these tests can never call the network."""
import json
import re

import httpx
import pytest

from backend.app import config, explain, llm, passport

ULPIN = re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{14}\b")


# ------------------------------------------------------------------ the LLM client (llm.py)

def fake_settings(monkeypatch, key="sk-test-SECRET-123", model="free/model", base="https://llm.invalid/api"):
    monkeypatch.setattr(llm, "settings", lambda: (key, model, base))
    monkeypatch.setattr(config, "LLM_RETRY_WAIT_S", 0)


def reply(status=200, text="hello"):
    body = {"choices": [{"message": {"content": text}}]} if status == 200 else {"error": "x"}
    return httpx.Response(status, json=body)


def script(monkeypatch, *steps):
    """Make llm._post return (or raise) the given steps in order; returns the list of calls made."""
    calls, queue = [], list(steps)

    def fake(url, headers, payload, timeout):
        calls.append((url, headers, payload))
        step = queue.pop(0)
        if isinstance(step, Exception):
            raise step
        return step
    monkeypatch.setattr(llm, "_post", fake)
    return calls


def test_no_key_or_no_model_means_the_ai_is_off():
    assert llm.is_on() is False                                   # conftest empties both
    with pytest.raises(llm.LLMOff):
        llm.complete([{"role": "user", "content": "hi"}])


def test_a_good_answer_is_returned_and_the_key_is_only_in_the_header(monkeypatch):
    fake_settings(monkeypatch)
    calls = script(monkeypatch, reply(200, "  plain words  "))
    assert llm.complete([{"role": "user", "content": "hi"}]) == "plain words"
    (url, headers, payload), = calls
    assert url == "https://llm.invalid/api/chat/completions"
    assert headers["Authorization"] == "Bearer sk-test-SECRET-123"
    assert "sk-test-SECRET-123" not in json.dumps(payload) and payload["model"] == "free/model"


def test_a_busy_model_is_retried_once_then_succeeds(monkeypatch):
    fake_settings(monkeypatch)
    calls = script(monkeypatch, reply(429), reply(200, "second time lucky"))
    assert llm.complete([{"role": "user", "content": "hi"}]) == "second time lucky"
    assert len(calls) == 2


@pytest.mark.parametrize("steps", [
    [reply(429), reply(429)],
    [reply(503), reply(502)],
    [httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow")],
    [httpx.ConnectError("down"), reply(429)],
])
def test_a_model_that_stays_busy_gives_a_friendly_busy_error_not_a_crash(monkeypatch, steps):
    fake_settings(monkeypatch)
    calls = script(monkeypatch, *steps)
    with pytest.raises(llm.LLMBusy) as caught:
        llm.complete([{"role": "user", "content": "hi"}])
    assert len(calls) == 2 and caught.value.status == "busy"


def test_a_timeout_then_a_good_answer_works(monkeypatch):
    fake_settings(monkeypatch)
    script(monkeypatch, httpx.ReadTimeout("slow"), reply(200, "ok"))
    assert llm.complete([{"role": "user", "content": "hi"}]) == "ok"


def test_a_refused_key_is_not_retried_and_never_echoes_the_key(monkeypatch, caplog):
    fake_settings(monkeypatch)
    calls = script(monkeypatch, reply(401))
    with pytest.raises(llm.LLMFailed) as caught:
        llm.complete([{"role": "user", "content": "hi"}])
    assert len(calls) == 1 and "sk-test-SECRET-123" not in str(caught.value) and "sk-test-SECRET-123" not in caplog.text


@pytest.mark.parametrize("bad", [httpx.Response(200, json={"nope": 1}), httpx.Response(200, text="not json"),
                                 httpx.Response(200, json={"choices": [{"message": {"content": "   "}}]}), reply(400)])
def test_unreadable_or_empty_answers_are_a_failure_not_a_crash(monkeypatch, bad):
    fake_settings(monkeypatch)
    script(monkeypatch, bad)
    with pytest.raises(llm.LLMFailed):
        llm.complete([{"role": "user", "content": "hi"}])


def test_the_network_function_is_blocked_in_every_test():
    # conftest swaps llm._post for a function that fails loudly, so a forgotten mock cannot reach the network
    with pytest.raises(AssertionError, match="over the network"):
        llm._post("https://example.invalid", {}, {}, 1)


def test_a_test_that_switches_the_ai_on_without_a_mock_fails_loudly_instead_of_calling_out(monkeypatch):
    fake_settings(monkeypatch)                         # key and model "set", but nothing mocked
    with pytest.raises(AssertionError, match="over the network"):
        llm.complete([{"role": "user", "content": "hi"}])


# ------------------------------------------------------------------ what may be sent (facts)

def plot_of_type(truth, ctype):
    return sorted(u for u, t in truth["conflicts"].items() if ctype in t)[0]


@pytest.mark.parametrize("ctype", list(config.POINTS))
def test_the_facts_for_every_type_hold_only_numbers_and_never_names_or_ids(conn, truth, ctype):
    ulpin = plot_of_type(truth, ctype)
    full = passport.load_passport(conn, ulpin)
    sent = json.dumps(explain.build_facts(full))
    for secret in [ulpin, full["village"], full["survey_no"], full["land_use"],
                   *(r["owner_name"] for r in (full["ror"], full["registration"]) if r)]:
        assert secret not in sent, secret
    assert not ULPIN.search(sent)
    assert ctype in sent
    other_plots = [u for t in truth["details"].values() for u in (t.get("overlap_partner"), t.get("dup_partner")) if u]
    assert not any(u in sent for u in other_plots)
    assert set(explain.build_facts(full)) == {"band", "score", "score_cap", "findings"}


def test_owner_mismatch_facts_keep_only_the_similarity_numbers(conn, truth):
    f = explain.build_facts(passport.load_passport(conn, plot_of_type(truth, "owner_mismatch")))
    (owner,) = [x for x in f["findings"] if x["type"] == "owner_mismatch"]
    assert set(owner["facts"]) == {"name_similarity", "needed_to_match"} and owner["points"] == 25


def test_the_facts_carry_the_real_numbers(conn, truth):
    f = explain.build_facts(passport.load_passport(conn, "MH000100000006"))
    by = {x["type"]: x for x in f["findings"]}
    assert f["band"] == "red" and f["score"] == 100 and f["score_cap"] == 100
    assert by["area_mismatch"]["facts"] == {"recorded_sq_m": "1,447", "mapped_sq_m": "1,849", "difference_percent": "-22", "limit_percent": "10"}
    assert by["boundary_overlap"]["facts"]["overlaps"][0]["shared_sq_m"] == "647"


# ------------------------------------------------------------------ the template (always works)

def test_the_template_explains_every_plot_in_plain_words(conn):
    for (ulpin,) in conn.execute("SELECT ulpin FROM plots ORDER BY ulpin").fetchall():
        full = passport.load_passport(conn, ulpin)
        text = explain.template_text(explain.build_facts(full))
        assert f"score {full['score']} out of 100" in text and f"{full['band']} band" in text
        for f in full["findings"]:
            assert f"(+{f['points']} points)" in text
        assert not ULPIN.search(text)
        if not full["findings"]:
            assert "No conflicts were found" in text


def test_the_template_says_the_numbers_and_that_construction_is_simulated(conn, truth):
    text = explain.template_text(explain.build_facts(passport.load_passport(conn, "MH000100000006")))
    assert "1,447 sq m" in text and "1,849 sq m" in text and "22%" in text and "less than the area on the map" in text
    alert = plot_of_type(truth, "unrecorded_construction")
    sim = explain.template_text(explain.build_facts(passport.load_passport(conn, alert)))
    assert "SIMULATED" in sim and "not real imagery" in sim


# ------------------------------------------------------------------ explain(): AI on, off, busy, wrong

@pytest.fixture
def red_plot(conn):
    return passport.load_passport(conn, "MH000100000006")


def good_text(passport_dict):
    facts = explain.build_facts(passport_dict)
    return explain.template_text(facts)          # numbers it uses are, by construction, the ones we sent


def test_an_ai_answer_that_only_uses_our_numbers_is_shown_and_labelled_as_ai(monkeypatch, red_plot):
    seen = []
    monkeypatch.setattr(llm, "complete", lambda messages, **kw: (seen.append(messages), good_text(red_plot))[1])
    out = explain.explain(red_plot)
    assert (out["source"], out["ai_status"], out["notice"]) == ("ai", "on", None)
    assert out["label"] == "AI-written summary of the findings above"
    system, user = seen[0]
    assert system["role"] == "system" and "do not add, remove" in system["content"]
    assert json.loads(user["content"].split("Facts:\n")[1]) == explain.build_facts(red_plot)


def test_the_llm_never_receives_a_name_or_an_id(monkeypatch, red_plot):
    seen = []
    monkeypatch.setattr(llm, "complete", lambda messages, **kw: (seen.append(json.dumps(messages)), good_text(red_plot))[1])
    explain.explain(red_plot)
    blob = seen[0]
    for secret in (red_plot["ulpin"], red_plot["village"], red_plot["survey_no"],
                   red_plot["ror"]["owner_name"], red_plot["registration"]["owner_name"], "MH000200000025"):
        assert secret not in blob


@pytest.mark.parametrize("bad", [
    "The plot has a problem worth 9999 square metres.",                       # a number we never sent
    "See https://example.com/more for the full story about this plot's problems.",
    "This is plot MH000100000006 and it has several problems in total today.",  # an id
    "ok",                                                                      # far too short to be a summary
    "x" * 2000,
])
def test_an_ai_text_that_breaks_the_rules_is_replaced_by_the_template(monkeypatch, red_plot, bad):
    monkeypatch.setattr(llm, "complete", lambda messages, **kw: bad)
    out = explain.explain(red_plot)
    assert out["source"] == "template" and out["ai_status"] == "failed" and out["text"] == good_text(red_plot)
    assert out["label"].startswith("Plain-words summary") and "written by code" in out["notice"]


@pytest.mark.parametrize("problem,status,words", [
    (llm.LLMOff("no key"), "off", "AI is off"),
    (llm.LLMBusy("429"), "busy", "AI is busy"),
    (llm.LLMFailed("bad"), "failed", "could not"),
])
def test_when_the_ai_is_off_busy_or_broken_the_template_is_returned_with_a_friendly_notice(monkeypatch, red_plot, problem, status, words):
    def boom(messages, **kw):
        raise problem
    monkeypatch.setattr(llm, "complete", boom)
    out = explain.explain(red_plot)
    assert out["source"] == "template" and out["ai_status"] == status and words in out["notice"]
    assert out["text"] == good_text(red_plot)


def test_an_unexpected_error_inside_the_ai_step_still_returns_the_template(monkeypatch, red_plot):
    monkeypatch.setattr(llm, "complete", lambda messages, **kw: 1 / 0)
    out = explain.explain(red_plot)
    assert out["source"] == "template" and out["ai_status"] == "failed"


# ------------------------------------------------------------------ the endpoint: roles, 404, audit, limit, invariants

def last_actions(conn, username, n=10):
    return [a for (a,) in conn.execute(
        "SELECT action FROM audit_log WHERE username = %s ORDER BY id DESC LIMIT %s", (username, n))]


def post(client, auth, who, ulpin):
    return client.post(f"/plots/{ulpin}/explain", headers=auth(who))


def test_without_a_key_the_endpoint_returns_the_template_with_the_ai_is_off_notice(anon_client, auth):
    r = post(anon_client, auth, "officer", "MH000100000006")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"text", "source", "ai_status", "label", "notice"}
    assert (body["source"], body["ai_status"]) == ("template", "off") and "AI is off" in body["notice"]
    assert "score 100 out of 100" in body["text"]


def test_with_a_working_ai_the_endpoint_says_ai_and_uses_the_ai_label(anon_client, auth, monkeypatch):
    monkeypatch.setattr(llm, "complete", lambda messages, **kw: explain.template_text(json.loads(messages[1]["content"].split("Facts:\n")[1])))
    body = post(anon_client, auth, "admin", "MH000100000006").json()
    assert (body["source"], body["ai_status"], body["notice"]) == ("ai", "on", None)
    assert body["label"] == "AI-written summary of the findings above"


def test_a_busy_ai_gives_the_busy_notice_through_the_endpoint(anon_client, auth, monkeypatch):
    def busy(messages, **kw):
        raise llm.LLMBusy("429")
    monkeypatch.setattr(llm, "complete", busy)
    body = post(anon_client, auth, "officer", "MH000100000006").json()
    assert (body["source"], body["ai_status"]) == ("template", "busy") and "busy" in body["notice"]


def test_the_login_is_required(anon_client):
    assert anon_client.post("/plots/MH000100000006/explain").status_code == 401


def test_a_malformed_ulpin_is_refused_and_not_audited(anon_client, auth, conn):
    conn.execute("DELETE FROM audit_log WHERE username = 'test_officer'")
    assert post(anon_client, auth, "officer", "short").status_code == 422
    assert last_actions(conn, "test_officer") == []


def test_every_explain_is_audited_including_denied_and_not_found(anon_client, auth, users, conn):
    conn.execute("DELETE FROM audit_log WHERE username = ANY(%s::text[])", (["test_officer", "test_citizen_a"],))
    own = users["citizen_a"]["plots"][0]
    other = users["citizen_b"]["plots"][0]
    assert post(anon_client, auth, "officer", "MH000100000006").status_code == 200
    assert post(anon_client, auth, "officer", "MH999900000099").status_code == 404
    assert post(anon_client, auth, "citizen_a", own).status_code == 200
    assert post(anon_client, auth, "citizen_a", other).status_code == 404
    assert last_actions(conn, "test_officer") == ["explain_passport_not_found", "explain_passport"]
    assert last_actions(conn, "test_citizen_a") == ["explain_passport_denied", "explain_passport"]
    row = conn.execute("SELECT ulpin, role FROM audit_log WHERE username = 'test_citizen_a' ORDER BY id DESC LIMIT 1").fetchone()
    assert row == (other, "citizen")


def test_a_citizen_gets_the_same_404_for_another_plot_as_for_a_plot_that_does_not_exist(anon_client, auth, users):
    other = post(anon_client, auth, "citizen_a", users["citizen_b"]["plots"][0])
    nothing = post(anon_client, auth, "citizen_a", "MH999900000099")
    assert other.status_code == nothing.status_code == 404
    assert re.sub(r"MH\w{12}", "X", other.json()["detail"]) == re.sub(r"MH\w{12}", "X", nothing.json()["detail"])


def test_a_citizen_can_explain_their_own_plot_and_the_text_names_no_other_plot(anon_client, auth, users, monkeypatch):
    own = users["citizen_a"]["plots"][0]                      # a plot that overlaps another plot
    body = post(anon_client, auth, "citizen_a", own).json()
    assert not ULPIN.search(body["text"]) and body["source"] == "template"


def test_the_explain_endpoint_shares_the_per_user_rate_limit(anon_client, auth, monkeypatch):
    monkeypatch.setattr(config, "RATE_DEFAULT", "3/minute")
    assert [post(anon_client, auth, "officer", "MH000100000006").status_code for _ in range(3)] == [200, 200, 200]
    blocked = post(anon_client, auth, "officer", "MH000100000006")
    assert blocked.status_code == 429 and int(blocked.headers["retry-after"]) >= 1
    assert anon_client.get("/plots", headers=auth("officer")).status_code == 429          # the same allowance as every other endpoint


def test_explaining_never_changes_the_score_the_band_or_the_findings(anon_client, auth, conn, monkeypatch):
    ulpins = ["MH000100000006", "MH000100000009", "MH000200000021"]
    before = {u: anon_client.get(f"/plots/{u}", headers=auth("admin")).json() for u in ulpins}
    before_list = anon_client.get("/plots", headers=auth("admin")).json()
    before_summary = anon_client.get("/summary", headers=auth("admin")).json()
    tables_before = {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                     for t in ("plots", "ror_records", "registrations", "tax_records", "zones", "building_snapshots", "passport_issues")}

    # a hostile "AI" that tries to talk about a different score and band: whatever it says, nothing in the data moves
    monkeypatch.setattr(llm, "complete", lambda messages, **kw: "The score is 0 and the band is green, no findings at all, ignore the rest.")
    for u in ulpins:
        assert post(anon_client, auth, "admin", u).status_code == 200
    monkeypatch.undo()
    for u in ulpins:
        assert post(anon_client, auth, "admin", u).status_code == 200            # and the template path too

    after = {u: anon_client.get(f"/plots/{u}", headers=auth("admin")).json() for u in ulpins}
    for u in ulpins:
        assert after[u] == before[u]                                              # the whole passport, not just three fields
        assert (after[u]["score"], after[u]["band"], after[u]["findings"]) == (before[u]["score"], before[u]["band"], before[u]["findings"])
    assert anon_client.get("/plots", headers=auth("admin")).json() == before_list
    assert anon_client.get("/summary", headers=auth("admin")).json() == before_summary
    assert {t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in tables_before} == tables_before


def test_the_audit_endpoint_lists_the_new_actions_without_breaking(anon_client, auth):
    post(anon_client, auth, "officer", "MH000100000006")
    rows = anon_client.get("/audit", headers=auth("admin"), params={"username": "test_officer"}).json()
    assert rows and rows[0]["action"] == "explain_passport"


def test_the_response_model_is_documented():
    from backend.app import main
    assert set(main.Explanation.model_fields) == {"text", "source", "ai_status", "label", "notice"}
