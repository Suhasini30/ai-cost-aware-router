"""Auth dependencies (Phase 10)."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.clerk import AuthError, verify_clerk_token
from app.core import config as config_module

_bearer = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Return the verified Clerk user id, or 401 (fail closed)."""
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not (credentials.credentials or "").strip()
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        return verify_clerk_token(
            credentials.credentials, config_module.settings
        )
    except AuthError as exc:
        raise HTTPException(status_code=401, detail="Unauthorized") from exc
