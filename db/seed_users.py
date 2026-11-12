"""Create the DEMO users: one admin, one officer and two citizens (3 plots each).

    python db/seed_users.py

The citizen and officer passwords below are DEMO ONLY (they are in the README on purpose). Never use them anywhere real.
The admin password is the local default below ONLY when the ADMIN_PASSWORD environment variable is not set. For any public
deployment set ADMIN_PASSWORD (for that one command only) so the admin password is private and never in a file.
Only argon2 hashes go into the database. Safe to run again: it updates the same four users and
re-assigns their plots. Run it after db/seed.py (it picks plots from db/planted_truth.json).
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app import config, db, security  # noqa: E402

TRUTH_PATH = Path(__file__).resolve().parent / "planted_truth.json"

# DEMO-ONLY passwords. Real passwords never go in code.
DEMO_USERS = [
    ("admin", "admin", os.environ.get("ADMIN_PASSWORD") or "AdminDemo#2026"),   # local default; ADMIN_PASSWORD overrides it
    ("officer", "officer", "OfficerDemo#2026"),
    ("citizen1", "citizen", "Citizen1Demo#2026"),
    ("citizen2", "citizen", "Citizen2Demo#2026"),
]
def score_of(problems):
    """The risk score a plot with these planted problems gets (same points and cap as the real scoring)."""
    return min(sum(config.POINTS[t] for t in problems), config.SCORE_CAP)


def choose_plots(plot_ulpins, truth):
    """Pick 3 plots per citizen, each with at least one planted problem. Deterministic.
    citizen1 owns a RED plot that overlaps another plot (so the privacy demo is real: the other plot's id is hidden
    from the citizen), a single missing-record plot, and a clean plot. citizen2 owns a restricted-zone plot and 2 clean."""
    existing = set(plot_ulpins)
    conflicts = {u: t for u, t in truth["conflicts"].items() if u in existing}
    details = truth.get("details", {})
    decoys = {d["ulpin"] for d in truth["decoys"]}
    touching = {u for pair in truth.get("touching_pairs", []) for u in pair}
    clean = [u for u in sorted(existing) if u not in conflicts and u not in decoys and u not in touching]
    if not conflicts:
        raise SystemExit("There are no planted problem plots to give the citizens. Run db/seed.py first.")

    def first(candidates, used):
        return next((u for u in candidates if u not in used), None)

    only = lambda ctype: [u for u in sorted(conflicts) if conflicts[u] == [ctype]]  # noqa: E731
    red = [u for u in sorted(conflicts) if score_of(conflicts[u]) >= config.RED_FROM]
    red_overlap = [u for u in red if "boundary_overlap" in conflicts[u]
                   and details.get(u, {}).get("overlap_relation") == "overlaps"]
    used = set()

    def take(candidates):
        """The first candidate not yet given away (or, failing that, any planted problem plot)."""
        pick = next((u for u in candidates if u not in used), None) or next(u for u in sorted(conflicts) if u not in used)
        used.add(pick)
        return pick

    def take_clean():
        pick = next(u for u in clean if u not in used)
        used.add(pick)
        return pick

    return {   # evaluated left to right, so the order below is the order plots are handed out
        "citizen1": [take(red_overlap or red), take(only("missing_record")), take_clean()],
        "citizen2": [take(only("restricted_zone_clash")), take_clean(), take_clean()],
    }


def build_demo_users(plot_ulpins, truth):
    """Returns [{username, role, password_hash, plots}]. The plain password is hashed here and goes no further."""
    plots_for = choose_plots(plot_ulpins, truth)
    return [{"username": name, "role": role, "password_hash": security.hash_password(password),
             "plots": plots_for.get(name, [])}
            for name, role, password in DEMO_USERS]


def load_users(conn, users):
    """Write the users and who owns what. Does not commit (the caller does)."""
    names = [u["username"] for u in users]
    for u in users:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) "
            "ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role",
            (u["username"], u["password_hash"], u["role"]))
    conn.execute("DELETE FROM user_plots WHERE username = ANY(%s::text[])", (names,))
    for u in users:
        for ulpin in u["plots"]:
            conn.execute("INSERT INTO user_plots (username, ulpin) VALUES (%s, %s)", (u["username"], ulpin))


def main():
    if not TRUTH_PATH.exists():
        raise SystemExit(f"{TRUTH_PATH} not found. Run python db/seed.py first.")
    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    with db.connect() as conn:
        plot_ulpins = [u for (u,) in conn.execute("SELECT ulpin FROM plots ORDER BY ulpin")]
        users = build_demo_users(plot_ulpins, truth)
        load_users(conn, users)
    print("Demo users created (citizen and officer passwords are in the README, demo only; the admin password is never printed):")
    for u in users:
        owns = f"owns {', '.join(u['plots'])}" if u["plots"] else "sees everything its role allows"
        print(f"  {u['username']:<9} {u['role']:<8} {owns}")


if __name__ == "__main__":
    main()
