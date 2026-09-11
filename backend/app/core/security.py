"""Backend token sessions (access + refresh), HS256 self-minted.

Readable by design: one small function per operation, no cleverness.
- Access tokens: short-lived (default 15 min), sent as Bearer header.
- Refresh tokens: long-lived (default 7 days), carried in an httpOnly
  cookie, rotated on every use (old jti retired; see auth router).
- `typ` claim separates the two: a refresh token can NEVER verify as
  an access token and vice versa.
- Empty jwt_secret_key fails closed (nothing mints, nothing verifies).
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import Settings

ISSUER = "cost-router"
_ALGORITHM = "HS256"


class TokenError(Exception):
    """Any token mint/verify failure (maps to HTTP 401 upstream)."""


def _secret(app_settings: Settings) -> str:
    if not app_settings.jwt_secret_key:
        raise TokenError("token signing is not configured")
    return app_settings.jwt_secret_key


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, app_settings: Settings) -> str:
    """Mint a short-lived Bearer token for `user_id`."""
    exp = _now() + timedelta(minutes=app_settings.jwt_access_minutes)
    return jwt.encode(
        {"sub": user_id, "iss": ISSUER, "typ": "access", "exp": exp},
        _secret(app_settings),
        algorithm=_ALGORITHM,
    )


def create_refresh_token(user_id: str, app_settings: Settings) -> tuple[str, str]:
    """Mint a refresh token; returns (token, jti) for server tracking."""
    jti = uuid.uuid4().hex
    exp = _now() + timedelta(days=app_settings.jwt_refresh_days)
    token = jwt.encode(
        {"sub": user_id, "iss": ISSUER, "typ": "refresh", "jti": jti,
         "exp": exp},
        _secret(app_settings),
        algorithm=_ALGORITHM,
    )
    return token, jti


def _decode(token: str, expected_typ: str, app_settings: Settings) -> dict:
    try:
        payload = jwt.decode(
            token,
            key=_secret(app_settings),
            algorithms=[_ALGORITHM],
            issuer=ISSUER,
            options={"require": ["exp", "sub", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("token verification failed") from exc
    if payload.get("typ") != expected_typ:
        raise TokenError(f"wrong token type (expected {expected_typ})")
    if not payload.get("sub"):
        raise TokenError("token subject missing")
    return payload


def verify_access_token(token: str, app_settings: Settings) -> str:
    """Verify a Bearer access token; returns the user id."""
    return _decode(token, "access", app_settings)["sub"]


def verify_refresh_token(token: str, app_settings: Settings) -> dict:
    """Verify a refresh-cookie token; returns its payload (has jti)."""
    return _decode(token, "refresh", app_settings)
