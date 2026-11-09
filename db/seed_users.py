"""Create the DEMO users: one admin, one officer and two citizens (3 plots each).

    python db/seed_users.py

The passwords below are DEMO ONLY (they are in the README on purpose). Never use them anywhere real.
Only argon2 hashes go into the database. Safe to run again: it updates the same four users and
re-assigns their plots. Run it after db/seed.py (it picks plots from db/planted_truth.json).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.app import db, security  # noqa: E402

TRUTH_PATH = Path(__file__).resolve().parent / "planted_truth.json"

# DEMO-ONLY passwords. Real passwords never go in code.
DEMO_USERS = [
    ("admin", "admin", "AdminDemo#2026"),
    ("officer", "officer", "OfficerDemo#2026"),
    ("citizen1", "citizen", "Citizen1Demo#2026"),
    ("citizen2", "citizen", "Citizen2Demo#2026"),
]
# What each citizen's 3 plots should contain: these problem types first, then clean plots.
CITIZEN_WISHES = {
    "citizen1": (["boundary_overlap", "missing_record"], 1),   # 2 problem plots + 1 clean
    "citizen2": (["restricted_zone_clash"], 2),                # 1 problem plot + 2 clean
}


def choose_plots(plot_ulpins, truth):
    """Pick 3 plots per citizen, each with at least one planted problem. Deterministic."""
    existing = set(plot_ulpins)
    conflicts = {u: t for u, t in truth["conflicts"].items() if u in existing}
    decoys = {d["ulpin"] for d in truth["decoys"]}
    clean = [u for u in sorted(existing) if u not in conflicts and u not in decoys]
    spare_problems = sorted(conflicts)
    if not spare_problems:
        raise SystemExit("There are no planted problem plots to give the citizens. Run db/seed.py first.")

    used, chosen = set(), {}
    for username, (wanted_types, n_clean) in CITIZEN_WISHES.items():
        plots = []
        for ctype in wanted_types:
            pick = next((u for u in sorted(conflicts) if conflicts[u] == [ctype] and u not in used), None)
            pick = pick or next((u for u in spare_problems if u not in used), None)
            used.add(pick)
            plots.append(pick)
        for _ in range(n_clean):
            pick = next(u for u in clean if u not in used)
            used.add(pick)
            plots.append(pick)
        chosen[username] = plots
    return chosen


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
    print("Demo users created (passwords are in the README, demo only):")
    for u in users:
        owns = f"owns {', '.join(u['plots'])}" if u["plots"] else "sees everything its role allows"
        print(f"  {u['username']:<9} {u['role']:<8} {owns}")


if __name__ == "__main__":
    main()
