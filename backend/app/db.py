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


def database_url(env):
    """DATABASE_URL (one address, for a hosted database such as Neon), with sslmode=require added when the address does not say.
    Returns None when it is not set, so the local POSTGRES_* variables are used."""
    url = (env.get("DATABASE_URL") or "").strip()
    if not url:
        return None
    if not url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL must start with postgresql:// (copy the connection string from your database host)")
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    return url


def connect_args(env):
    """What to hand to psycopg.connect(): a DATABASE_URL if there is one, else the POSTGRES_* variables (the local Docker flow).
    The default database name and user ("landstack") match docker-compose.yml and .env.example."""
    url = database_url(env)
    if url:
        return (url,), {}
    return (), dict(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=env.get("POSTGRES_PORT", "5432"),
        user=env.get("POSTGRES_USER", "landstack"),
        password=env["POSTGRES_PASSWORD"],
        dbname=env.get("POSTGRES_DB", "landstack"),
    )


def connect():
    args, kwargs = connect_args(read_env())
    return psycopg.connect(*args, **kwargs)


def get_conn():
    """FastAPI dependency: one database connection per request, always closed afterwards."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
