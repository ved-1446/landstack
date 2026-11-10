"""The "Explain in plain words" feature (Phase 11, Part A).

WHAT IT DOES: rewrites the findings a plot ALREADY has into plain words. It never changes, adds or removes a finding and
never touches the score or the band: it only reads a passport and returns text.

WHAT LEAVES THIS MACHINE: only the finding types, points, a few numbers and words, and the band and score. Evidence text can
contain owner names, so it is NEVER sent: each type has a small allowlist of patterns (`FACT_PATTERNS`) that pull out just
the numbers. Nothing here sees an owner name, a ULPIN, a survey number or a village.

WHEN THE AI IS OFF, BUSY OR WRONG: a template written in code (`template_text`) gives the same facts in plain words. The AI's
text is also REJECTED (and the template used) if it contains a number we did not send, a web link or a ULPIN-looking id.
"""
import json
import logging
import re

from . import config, llm

log = logging.getLogger("landstack.explain")

AI_LABEL = "AI-written summary of the findings above"
TEMPLATE_LABEL = "Plain-words summary of the findings above (written by code, not by AI)"

NOTICES = {
    "off": "AI is off, so this summary was written by code.",
    "busy": "AI is busy right now, so this summary was written by code. Try again in a moment for an AI-written one.",
    "failed": "The AI could not write a summary this time, so this summary was written by code.",
}

PLAIN_NAME = {
    "boundary_overlap": "boundary overlap",
    "restricted_zone_clash": "restricted zone clash",
    "area_mismatch": "area mismatch",
    "owner_mismatch": "owner mismatch",
    "duplicate_survey_no": "duplicate survey number",
    "invalid_boundary": "invalid boundary",
    "tax_overdue": "tax overdue",
    "missing_record": "missing record",
    "unrecorded_construction": "unrecorded construction (SIMULATED)",
}

NUM = r"[\d,]+(?:\.\d+)?"


def _find(pattern, text):
    m = re.search(pattern, text)
    return m.groups() if m else None


def _facts_overlap(evidence):
    out = []
    for part in evidence.split("; "):
        if "inside this plot" in part:
            kind = "another plot lies completely inside this plot"
        elif "lies completely inside" in part:
            kind = "this plot lies completely inside another plot"
        elif "exactly the same boundary" in part:
            kind = "identical boundary to another plot"
        else:
            kind = "partly overlaps another plot"
        shared = _find(rf"({NUM}) sq m", part)
        percent = _find(r"(\d+)% of this plot", part)
        out.append({"kind": kind, "shared_sq_m": shared[0] if shared else None,
                    "percent_of_this_plot": percent[0] if percent else None})
    return {"overlaps": out}


def _facts_zone(evidence):
    g = _find(rf"({NUM}) sq m of ({NUM}) sq m \((\d+)%\) lies inside restricted zone: ([a-z_, ]+); limit is (\d+)%", evidence)
    if not g:
        return {}
    return {"inside_sq_m": g[0], "plot_sq_m": g[1], "percent_inside": g[2], "zone_kinds": g[3].replace("_", " "),
            "limit_percent": g[4]}


def _facts_area(evidence):
    g = _find(rf"record says ({NUM}) sq m but the mapped plot is ({NUM}) sq m \(([+-]?\d+)%\); limit is (\d+)%", evidence)
    if not g:
        return {}
    return {"recorded_sq_m": g[0], "mapped_sq_m": g[1], "difference_percent": g[2], "limit_percent": g[3]}


def _facts_owner(evidence):
    g = _find(r"name similarity ([\d.]+) \(needs ([\d.]+)\)", evidence)      # the names themselves are never read
    return {"name_similarity": g[0], "needed_to_match": g[1]} if g else {}


def _facts_tax(evidence):
    g = _find(r"which is (\d+) days \(([\d.]+) years\) before .*?; limit is (\d+) years", evidence)
    return {"days_overdue_since_reference_date": g[0], "years": g[1], "limit_years": g[2]} if g else {}


def _facts_missing(evidence):
    kinds = []
    for key, word in (("RoR record", "land record"), ("registration", "registration"), ("tax record", "tax record")):
        if key in evidence:
            kinds.append(word)
    return {"missing": kinds}


def _facts_construction(evidence):
    g = _find(rf"about ({NUM}) sq m .*?limit is ({NUM}) sq m", evidence)
    return {"new_building_sq_m": g[0], "limit_sq_m": g[1], "simulated": True} if g else {"simulated": True}


FACT_PATTERNS = {
    "boundary_overlap": _facts_overlap,
    "restricted_zone_clash": _facts_zone,
    "area_mismatch": _facts_area,
    "owner_mismatch": _facts_owner,
    "duplicate_survey_no": lambda evidence: {},        # the survey number and the other plot's id are never sent
    "invalid_boundary": lambda evidence: {},
    "tax_overdue": _facts_tax,
    "missing_record": _facts_missing,
    "unrecorded_construction": _facts_construction,
}


def build_facts(passport):
    """The ONLY thing that may be sent to the LLM: types, points, numbers, the band and the score."""
    findings = []
    for f in passport["findings"]:
        extract = FACT_PATTERNS.get(f["type"], lambda evidence: {})
        findings.append({"type": f["type"], "name": PLAIN_NAME.get(f["type"], f["type"]), "points": f["points"],
                         "facts": extract(f["evidence"])})
    return {"band": passport["band"], "score": passport["score"], "score_cap": config.SCORE_CAP, "findings": findings}


def _all_numbers(value):
    """Every number written anywhere inside a facts structure, as plain strings without commas."""
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", json.dumps(value))}


# ---------------------------------------------------------------- the template (always available)

def _sentence(finding):
    t, f, p = finding["type"], finding["facts"], finding["points"]
    if t == "boundary_overlap":
        parts = []
        for o in f.get("overlaps", []):
            size = f" (about {o['shared_sq_m']} sq m" + (f", {o['percent_of_this_plot']}% of this plot)" if o["percent_of_this_plot"] else ")") \
                if o["shared_sq_m"] else ""
            parts.append(o["kind"] + size)
        text = "The boundary clashes with a neighbour: " + "; ".join(parts) + "." if parts else "The boundary clashes with a neighbouring plot."
    elif t == "restricted_zone_clash":
        text = (f"About {f['inside_sq_m']} sq m of the plot ({f['percent_inside']}%) lies inside a restricted zone ({f['zone_kinds']}); "
                f"more than {f['limit_percent']}% is flagged.") if f else "Part of the plot lies inside a restricted zone."
    elif t == "area_mismatch":
        if f:
            direction = "more" if f["difference_percent"].lstrip("+").isdigit() else "less"
            text = (f"The area in the land record ({f['recorded_sq_m']} sq m) is {direction} than the area on the map "
                    f"({f['mapped_sq_m']} sq m), a difference of {f['difference_percent'].lstrip('+-')}%; more than {f['limit_percent']}% is flagged.")
        else:
            text = "The area in the land record does not match the area on the map."
    elif t == "owner_mismatch":
        text = ("The owner in the land record and the owner in the registration do not look like the same person "
                f"(name similarity {f['name_similarity']}; {f['needed_to_match']} or more counts as a match)."
                if f else "The owner in the land record and the owner in the registration do not look like the same person.")
    elif t == "duplicate_survey_no":
        text = "Another plot in the same village has the same survey number."
    elif t == "invalid_boundary":
        text = "The boundary shape is invalid (for example it crosses itself), so its area and overlaps cannot be trusted."
    elif t == "tax_overdue":
        text = (f"Property tax was last paid {f['years']} years before the reference date; more than {f['limit_years']} years is flagged."
                if f else "Property tax is overdue.")
    elif t == "missing_record":
        kinds = f.get("missing") or ["record"]
        text = "No " + " or ".join(kinds) + " was found for this plot."
    elif t == "unrecorded_construction":
        text = (f"SIMULATED: about {f['new_building_sq_m']} sq m of new building appears in the later snapshot but not in the earlier one "
                f"(flagged from {f['limit_sq_m']} sq m). This comes from generated demo data, not real imagery."
                if "new_building_sq_m" in f else "SIMULATED: a new building appears that is not in the records (generated demo data).")
    else:
        text = f"A {finding['name']} was found."
    return f"{text} (+{p} points)"


def template_text(facts):
    """The plain explanation written by code: same facts, no AI."""
    band_word = {"green": "low", "amber": "medium", "red": "high"}[facts["band"]]
    head = f"This plot has a {band_word} risk rating: score {facts['score']} out of {facts['score_cap']}, {facts['band']} band."
    if not facts["findings"]:
        return head + " No conflicts were found."
    lines = [head, f"{len(facts['findings'])} {'finding explains' if len(facts['findings']) == 1 else 'findings explain'} the score:"]
    lines += [f"- {_sentence(f)}" for f in facts["findings"]]
    lines.append(f"The points are added up and the total stops at {facts['score_cap']}.")
    return "\n".join(lines)


# ---------------------------------------------------------------- the AI version

SYSTEM_PROMPT = (
    "You rewrite land-record risk findings into plain, calm English for someone who is not an expert. "
    "Use ONLY the facts in the JSON the user sends. Rules: do not add, remove, merge or change any finding; "
    "do not mention any number that is not in the JSON; do not guess causes or give legal advice; "
    "do not invent names, places or ids; do not include links; keep it short (one or two sentences per finding, "
    "then one closing sentence about the score and band). If a finding says simulated, say clearly that it is simulated demo data. "
    "Write plain text only, no markdown."
)

_URL = re.compile(r"https?://|www\.|\]\(", re.I)
_ULPIN = re.compile(r"\b(?=[A-Z0-9]*\d)[A-Z0-9]{14}\b")


def check_ai_text(text, facts):
    """True if the AI's text is safe to show: it only uses numbers we sent, has no link and no id-like string."""
    if not text or len(text) > 1600 or (facts["findings"] and len(text) < 40):
        return False
    if _URL.search(text) or _ULPIN.search(text):
        return False
    allowed = _all_numbers(facts) | {str(i) for i in range(1, len(facts["findings"]) + 2)}
    return all(n in allowed for n in _all_numbers(text))


def explain(passport):
    """Explain a passport. Returns {"text", "source": "ai"|"template", "ai_status", "label", "notice"}; never raises."""
    facts = build_facts(passport)
    fallback = template_text(facts)
    try:
        text = llm.complete(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": "Facts:\n" + json.dumps(facts, ensure_ascii=True)}],
            max_tokens=450)
    except llm.LLMProblem as exc:
        log.info("explainer fell back to the template: %s", type(exc).__name__)
        status = exc.status
    except Exception:  # noqa: BLE001  (nothing may break the request)
        log.exception("explainer: unexpected error; using the template")
        status = "failed"
    else:
        if check_ai_text(text, facts):
            return {"text": text, "source": "ai", "ai_status": "on", "label": AI_LABEL, "notice": None}
        log.warning("explainer: the AI text was rejected (a number we did not send, a link, or an id)")
        status = "failed"
    return {"text": fallback, "source": "template", "ai_status": status, "label": TEMPLATE_LABEL, "notice": NOTICES[status]}
