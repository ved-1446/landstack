"""Risk score. Plain addition done by code; no model or LLM ever changes it."""
from . import checks, config


def band_for(score):
    if score >= config.RED_FROM:
        return "red"
    if score >= config.AMBER_FROM:
        return "amber"
    return "green"


def score_plot(findings):
    """Add up the points, cap at 100, and name the band."""
    score = min(sum(f["points"] for f in findings), config.SCORE_CAP)
    return {"score": score, "band": band_for(score), "findings": list(findings)}


def run_all(conn):
    """Run every check and return {ulpin: score_plot(...)} for every plot."""
    by_plot = {ulpin: [] for (ulpin,) in conn.execute("SELECT ulpin FROM plots ORDER BY ulpin")}
    for finding in checks.run_checks(conn):
        by_plot[finding["ulpin"]].append(finding)
    return {ulpin: score_plot(fs) for ulpin, fs in by_plot.items()}
