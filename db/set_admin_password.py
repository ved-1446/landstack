"""Change ONLY the admin's password in the database that DATABASE_URL (or the POSTGRES_* settings) points at.

    $env:ADMIN_PASSWORD = "<typed by you, never written into a file>"
    python db/set_admin_password.py

The password is read from the ADMIN_PASSWORD environment variable only (never from an argument, so it stays out of the shell
history), is hashed with argon2 and is never printed or logged. Nothing else is touched: other users, plots and the audit log stay.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.app import db, security  # noqa: E402

MIN_LENGTH = 12


def set_admin_password(conn, password):
    """Update the admin's hash. Returns True if the admin user exists. Does not commit (the caller does)."""
    if not password or len(password) < MIN_LENGTH:
        raise ValueError(f"ADMIN_PASSWORD must be set and at least {MIN_LENGTH} characters long.")
    cur = conn.execute("UPDATE users SET password_hash = %s WHERE username = 'admin' AND role = 'admin'",
                       (security.hash_password(password),))
    return cur.rowcount == 1


def main():
    try:
        with db.connect() as conn:
            found = set_admin_password(conn, os.environ.get("ADMIN_PASSWORD", ""))
    except ValueError as err:
        raise SystemExit(str(err))
    if not found:
        raise SystemExit("There is no admin user in this database. Run db/seed_users.py first.")
    print("The admin password was changed. Nothing else was touched.")


if __name__ == "__main__":
    main()
