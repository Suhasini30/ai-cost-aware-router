"""Auth dependencies (Phase 10)."""

Two accepted credential kinds, dispatched on the unverified issuer:
- backend self-minted tokens (iss "cost-router") verify locally;
- anything else takes the Clerk JWKS path.
Both fail closed to HTTP 401.
"""

import logging

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.clerk import AuthError, verify_clerk_token
from app.core import config as config_module

log = logging.getLogger("app.auth")
_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return the verified Clerk user id, or 401 (fail closed)."""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not (credentials.credentials or "").strip()
    ):
        log.warning("auth failed: missing credentials")
        raise HTTPException(status_code=401, detail="Unauthorized")
    raw = credentials.credentials
    try:
        issuer = jwt.decode(
            raw, options={"verify_signature": False}
        ).get("iss")
    except Exception:
        issuer = None
    try:
        if issuer == LOCAL_ISSUER:
            user_id = verify_access_token(raw, config_module.settings)
        else:
            user_id = verify_clerk_token(raw, config_module.settings)
    except (TokenError, AuthError) as exc:
        # Server-side reason only; clients always see generic 401.
        log.warning("auth failed: %s", exc)
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
    request.state.user_id = user_id
    return user_id
