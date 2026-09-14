"""Session endpoints: Clerk exchange, refresh rotation, logout.

Flow: POST /auth/exchange once with a valid Clerk JWT → access token
(JSON body, keep in memory) + httpOnly refresh cookie. Access lives
~15 min; POST /auth/refresh (cookie) mints a fresh pair with a new jti.
POST /auth/logout clears the cookie (client discards the access token).

No password storage anywhere: Clerk remains the identity source.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from app.auth.clerk import AuthError, verify_clerk_token
from app.core import config as config_module
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)

log = logging.getLogger("app.auth")

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


class TokenPair(BaseModel):
    access_token: str
    token_type: str = "bearer"


def _cookie_kwargs() -> dict:
    # Secure is honored on localhost by modern browsers; required with
    # SameSite=None for the :3000 -> :8000 cross-site flow.
    return {"httponly": True, "secure": True, "samesite": "none", "path": "/"}


def _creds(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not (credentials.credentials or "").strip()
    ):
        log.warning("auth failed: missing credentials")
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.credentials


@router.post("/exchange", response_model=TokenPair)
def exchange(token: str = Depends(_creds), response: Response = None) -> TokenPair:
    """Trade one valid Clerk JWT for a backend access + refresh pair."""
    cfg = config_module.settings
    try:
        user_id = verify_clerk_token(token, cfg)
    except AuthError as exc:
        log.warning("exchange failed: %s", exc)
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    try:
        access = create_access_token(user_id, cfg)
        refresh, _jti = create_refresh_token(user_id, cfg)
    except TokenError as exc:
        log.exception("exchange mint failed")
        raise HTTPException(status_code=500, detail="Token service unavailable") from exc
    max_age = cfg.jwt_refresh_days * 24 * 3600
    response.set_cookie(
        cfg.refresh_cookie_name, refresh, max_age=max_age, **_cookie_kwargs()
    )
    return TokenPair(access_token=access)


@router.post("/refresh", response_model=TokenPair)
def refresh(request: Request, response: Response) -> TokenPair:
    """Rotate the refresh cookie; returns a fresh access token."""
    cfg = config_module.settings
    raw = request.cookies.get(cfg.refresh_cookie_name)
    if not raw:
        log.warning("refresh failed: missing cookie")
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = verify_refresh_token(raw, cfg)
    except TokenError as exc:
        log.warning("refresh failed: %s", exc)
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    try:
        access = create_access_token(payload["sub"], cfg)
        rotated, _jti = create_refresh_token(payload["sub"], cfg)
    except TokenError as exc:
        log.exception("refresh mint failed")
        raise HTTPException(status_code=500, detail="Token service unavailable") from exc
    max_age = cfg.jwt_refresh_days * 24 * 3600
    response.set_cookie(
        cfg.refresh_cookie_name, rotated, max_age=max_age, **_cookie_kwargs()
    )
    return TokenPair(access_token=access)


@router.post("/logout", status_code=204)
def logout(response: Response) -> None:
    """Clear the refresh cookie (client discards its access token)."""
    cfg = config_module.settings
    response.delete_cookie(cfg.refresh_cookie_name, path="/",
                           samesite="none", secure=True)
    return None
