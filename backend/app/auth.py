"""Login, who-am-I, and the dependencies that protect endpoints.

Authentication = proving who you are (the token). Authorization = what that person may do (the role).
"""
import logging
from dataclasses import dataclass
from typing import Annotated, Literal

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from . import limits, security
from .db import get_conn

log = logging.getLogger("landstack.auth")

# Loaded when this module is imported, so the app REFUSES TO START without a real JWT_SECRET.
SETTINGS = security.get_settings()

NOT_LOGGED_IN = "Not authenticated"
BAD_TOKEN = "Invalid or expired token"
BAD_LOGIN = "Incorrect username or password"      # the same text for a wrong user and a wrong password
FORBIDDEN = "You do not have permission to do this."

bearer = HTTPBearer(auto_error=False, description="Log in at POST /auth/login and paste the access_token.")
Conn = Annotated[object, Depends(get_conn)]


class ErrorBody(BaseModel):
    detail: str


class UserInfo(BaseModel):
    username: str
    role: Literal["admin", "officer", "citizen"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int = Field(description="seconds until the token expires")
    user: UserInfo


@dataclass(frozen=True)
class User:
    username: str
    role: str


def _unauthorized(detail):
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    conn: Conn,
) -> User:
    """Check the token, then look the user up. The role comes from the database (not from the
    token), so a changed role or a deleted user takes effect straight away."""
    if credentials is None:
        raise _unauthorized(NOT_LOGGED_IN)
    try:
        claims = security.decode_access_token(credentials.credentials, SETTINGS)
    except jwt.PyJWTError:
        raise _unauthorized(BAD_TOKEN) from None
    row = conn.execute("SELECT role FROM users WHERE username = %s", (claims["sub"],)).fetchone()
    if row is None:
        raise _unauthorized(BAD_TOKEN)
    return User(claims["sub"], row[0])


def require_roles(*allowed):
    """Dependency factory: only the listed roles get through; everyone else gets 403."""
    def check(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=403, detail=FORBIDDEN)
        return user
    return check


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse,
             responses={401: {"model": ErrorBody}, 429: {"model": ErrorBody}})
@limits.per_ip_login
def login(request: Request, body: LoginRequest, conn: Conn):
    """Exchange a username and password for an access token (valid for the configured minutes)."""
    row = conn.execute("SELECT password_hash, role FROM users WHERE username = %s",
                       (body.username,)).fetchone()
    stored_hash = row[0] if row else None
    if not security.verify_password(stored_hash, body.password):
        # No username and no password in the log, only where the attempt came from.
        log.warning("failed login attempt from %s", limits.client_ip(request))
        raise _unauthorized(BAD_LOGIN)
    return {
        "access_token": security.create_access_token(body.username, row[1], SETTINGS),
        "token_type": "bearer",
        "expires_in": SETTINGS.token_minutes * 60,
        "user": {"username": body.username, "role": row[1]},
    }


@router.get("/me", response_model=UserInfo,
            responses={401: {"model": ErrorBody}, 429: {"model": ErrorBody}})
@limits.per_user
def me(request: Request, user: Annotated[User, Depends(current_user)]):
    """Who am I? (username and role from the database, for the logged-in token)"""
    return {"username": user.username, "role": user.role}
