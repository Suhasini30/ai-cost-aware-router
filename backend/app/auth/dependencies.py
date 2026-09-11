"""Auth dependencies (Phase 10 + backend token sessions).

Two accepted credential kinds, dispatched on the unverified issuer:
- backend self-minted tokens (iss "cost-router") verify locally;
- anything else takes the Clerk JWKS path.
Both fail closed to HTTP 401.
"""

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.clerk import AuthError, verify_clerk_token
from app.core import config as config_module
from app.core.security import ISSUER as LOCAL_ISSUER
from app.core.security import TokenError, verify_access_token

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return the verified user id from either credential kind, or 401."""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not (credentials.credentials or "").strip()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    raw = credentials.credentials
    try:
        issuer = jwt.decode(
            raw, options={"verify_signature": False}
        ).get("iss")
    except Exception:
        issuer = None
    if issuer == LOCAL_ISSUER:
        try:
            return verify_access_token(raw, config_module.settings)
        except TokenError as exc:
            raise HTTPException(status_code=401, detail="Unauthorized") from exc
    try:
        return verify_clerk_token(raw, config_module.settings)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
