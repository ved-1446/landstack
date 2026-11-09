"""Open a psycopg connection using the settings in .env (no ORM)."""
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]


def read_env():
    """Real environment variables win; .env fills in the rest."""
    env = {}
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    env.update(os.environ)
    return env


def connect():
    env = read_env()
    return psycopg.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=env.get("POSTGRES_PORT", "5432"),
        user=env.get("POSTGRES_USER", "landstack"),
        password=env["POSTGRES_PASSWORD"],
        dbname=env.get("POSTGRES_DB", "landstack"),
    )


def get_conn():
    """FastAPI dependency: one database connection per request, always closed afterwards."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
