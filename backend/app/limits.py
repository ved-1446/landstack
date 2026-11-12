"""Rate limits (slowapi). Logins: per IP address. Everything else: per logged-in user.

The limits are read from config.py on every request, so tests (or you) can change them.
"""
import ipaddress
import math
import time

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import config, db, security


def _read_hops() -> int:
    raw = (db.read_env().get("TRUSTED_PROXY_HOPS") or "0").strip()
    if not raw.isdigit() or int(raw) > 5:
        raise RuntimeError(f"TRUSTED_PROXY_HOPS must be a whole number from 0 to 5 (got {raw!r})")
    return int(raw)


# How many proxies of YOURS sit between the internet and this app (0 = none: use the connection's own address, ignore X-Forwarded-For).
# Behind a host such as Render set it to the number of proxies that append to X-Forwarded-For (see docs/DEPLOY.md).
TRUSTED_PROXY_HOPS = _read_hops()


def client_ip(request: Request) -> str:
    """The real visitor address, safely.

    Each trusted proxy ADDS the address it saw to the RIGHT end of X-Forwarded-For. A visitor can write anything they like on the
    LEFT, so the left side is never believed: with N trusted proxies the visitor is the Nth entry counting from the right.
    If the header is missing, too short or not an address, the connection's own address is used (everyone behind one proxy then
    shares a limit, which is safe, never a free pass).
    """
    direct = get_remote_address(request)
    hops = TRUSTED_PROXY_HOPS
    if hops <= 0:
        return direct
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(parts) < hops:
        return direct
    candidate = parts[-hops]
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return direct


def user_or_ip(request: Request) -> str:
    """Who is making the request? The user in a valid token; otherwise the IP address.
    The token signature is checked, so nobody can dodge a limit by inventing a username."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        try:
            return "user:" + security.decode_access_token(header[7:].strip())["sub"]
        except (jwt.PyJWTError, KeyError):
            pass
    return "ip:" + client_ip(request)


# key_style="endpoint": one counter per endpoint, NOT per URL. slowapi's default counts each distinct URL
# separately, so /verify/AAAA and /verify/BBBB would each get a fresh allowance and guessing ids would never be limited.
limiter = Limiter(key_func=user_or_ip, key_style="endpoint")

# ONE allowance per user shared by every endpoint (scope="api"), not a separate one per endpoint.
per_user = limiter.shared_limit(lambda: config.RATE_DEFAULT, scope="api")
per_ip_login = limiter.limit(lambda: config.RATE_LOGIN, key_func=client_ip)
per_ip_verify = limiter.limit(lambda: config.RATE_VERIFY, key_func=client_ip)   # public endpoint


def too_many_requests(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """429 with a plain JSON message and a Retry-After header (whole seconds)."""
    wait = 60
    try:
        item, args = request.state.view_rate_limit
        reset_at, _remaining = limiter.limiter.get_window_stats(item, *args)
        wait = max(1, math.ceil(reset_at - time.time()))
    except Exception:  # noqa: BLE001  (fall back to the length of the limit window)
        try:
            wait = max(1, int(exc.limit.limit.get_expiry()))
        except Exception:  # noqa: BLE001
            pass
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(wait)},
        content={"detail": f"Too many requests. Please wait {wait} seconds and try again."},
    )
