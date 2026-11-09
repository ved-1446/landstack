"""Passwords (argon2) and login tokens (JWT). No web code here, so scripts can use it too.

Rules: a plain password is never stored, logged or returned; the JWT secret comes only from the
environment / .env and the app refuses to start without a real one.
"""
import functools
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from . import config, db

_hasher = PasswordHasher()
# Used when the username does not exist, so "unknown user" takes as long as "wrong password".
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))


def hash_password(password: str) -> str:
    """Return an argon2 hash (it contains its own random salt). The password itself is not kept."""
    return _hasher.hash(password)


def verify_password(stored_hash: str | None, password: str) -> bool:
    """True only if the password matches. With no stored hash (unknown user) it still does the
    same amount of work, then answers False."""
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerificationError, InvalidHashError):
        return False


@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    token_minutes: int


def load_settings(env: dict | None = None) -> Settings:
    """Read the JWT settings. Raises RuntimeError (so the app will not start) if the secret is
    missing, still the placeholder, or too short."""
    env = db.read_env() if env is None else env
    secret = (env.get("JWT_SECRET") or "").strip()
    if not secret:
        raise RuntimeError(
            "JWT_SECRET is not set. Put a long random value in .env (or the environment), e.g. "
            'run: python -c "import secrets; print(secrets.token_urlsafe(48))"')
    if secret == config.JWT_SECRET_PLACEHOLDER or secret.lower().startswith("change-me"):
        raise RuntimeError("JWT_SECRET is still the placeholder from .env.example. Generate a real random value.")
    if len(secret) < config.JWT_SECRET_MIN_LENGTH:
        raise RuntimeError(f"JWT_SECRET is too short (needs at least {config.JWT_SECRET_MIN_LENGTH} characters).")

    raw_minutes = (env.get("JWT_EXPIRE_MINUTES") or "").strip()
    try:
        minutes = int(raw_minutes) if raw_minutes else config.JWT_DEFAULT_EXPIRE_MINUTES
    except ValueError:
        raise RuntimeError(f"JWT_EXPIRE_MINUTES must be a whole number, got {raw_minutes!r}.") from None
    if minutes <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be more than zero.")
    return Settings(secret, minutes)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def create_access_token(username: str, role: str, settings: Settings | None = None,
                        lifetime: timedelta | None = None) -> str:
    """A signed token that says who the user is. It is signed, not secret: anyone can read it."""
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    lifetime = lifetime if lifetime is not None else timedelta(minutes=settings.token_minutes)
    claims = {"sub": username, "role": role, "iat": now, "exp": now + lifetime}
    return jwt.encode(claims, settings.jwt_secret, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings | None = None) -> dict:
    """Check the signature and the expiry. Raises jwt.PyJWTError for anything wrong.
    Only HS256 is accepted, so a token that claims "no signature" is refused."""
    settings = settings or get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[config.JWT_ALGORITHM],
                      options={"require": ["exp", "sub"]})
