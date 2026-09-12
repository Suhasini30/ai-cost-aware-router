"""Clerk JWT verification (Phase 10). Isolated: no router/execution imports.

Verifies RS256 short-lived session tokens against Clerk's JWKS endpoint.
Fail-closed: any problem (unconfigured, network, bad signature, wrong
issuer, expired, missing claims) raises AuthError, which the dependency
maps to HTTP 401. Nothing here ever returns an anonymous identity.
"""

import time

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm

from app.core.config import Settings

_ALGORITHMS = ["RS256"]

# url -> (fetched_at_epoch, {kid: cryptography_key})
_jwks_cache: dict[str, tuple[float, dict]] = {}


class AuthError(Exception):
    """Any authentication failure (message kept generic for clients)."""


def clear_jwks_cache() -> None:
    """Test hook: drop cached JWKS keys."""
    _jwks_cache.clear()


def _http_get_json(url: str) -> dict:
    """GET JSON (separate helper so tests can stub JWKS transport)."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _fetch_jwks(jwks_url: str, ttl_s: float) -> dict:
    now = time.monotonic()
    cached = _jwks_cache.get(jwks_url)
    if cached is not None and now - cached[0] < ttl_s:
        return cached[1]
    try:
        keys = {
            entry["kid"]: RSAAlgorithm.from_jwk(entry)
            for entry in _http_get_json(jwks_url).get("keys", [])
            if entry.get("kid")
        }
    except Exception as exc:
        raise AuthError("cannot retrieve signing keys") from exc
    if not keys:
        raise AuthError("no signing keys available")
    _jwks_cache[jwks_url] = (now, keys)
    return keys


def verify_clerk_token(token: str, app_settings: Settings) -> str:
    """Verify a Clerk JWT and return the user id (sub claim).

    Raises:
        AuthError: unconfigured auth, malformed/expired/invalid token,
            unknown key id, wrong issuer, or JWKS retrieval failure.
    """
    if not app_settings.clerk_jwks_url or not app_settings.clerk_issuer:
        raise AuthError("authentication is not configured")
    if not token or not token.strip():
        raise AuthError("empty token")
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except Exception as exc:
        raise AuthError("malformed token") from exc
    if not kid:
        raise AuthError("token key id missing")
    keys = _fetch_jwks(app_settings.clerk_jwks_url,
                       app_settings.clerk_jwks_cache_ttl_s)
    key = keys.get(kid)
    if key is None:
        raise AuthError("unknown signing key")
    configured_issuer = app_settings.clerk_issuer.rstrip("/")
    try:
        payload = jwt.decode(
            token,
            key=key,
            algorithms=_ALGORITHMS,
            issuer=(configured_issuer, f"{configured_issuer}/"),
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("token expired") from exc
    except jwt.InvalidIssuerError as exc:
        raise AuthError("token issuer mismatch") from exc
    except jwt.PyJWTError as exc:
        raise AuthError("token verification failed") from exc
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("token subject missing")
    return user_id
