"""Logging setup + HTTP access log (observability layer).

Stdlib only, stdout only (12-factor): lines appear inline in the
uvicorn terminal. No prompts, answers, tokens, or secrets are ever
logged — user_id is the only identity field emitted.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

_SLOW_MS = 2000.0


def setup_logging(level: str = "INFO") -> None:
    """Configure root + uvicorn loggers once (safe on reload)."""
    lvl = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        )
        root.addHandler(handler)
    root.setLevel(lvl)
    # Silence uvicorn's own per-request access log (ours replaces it);
    # keep its error channel at the configured level.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(lvl)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """One line per request: method path -> status in Xms (+ user)."""

    async def dispatch(self, request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000.0
            logging.getLogger("app.access").exception(
                "%s %s -> 500 in %.0fms", request.method,
                request.url.path, elapsed,
            )
            raise
        elapsed = (time.perf_counter() - started) * 1000.0
        user = getattr(request.state, "user_id", None)
        line = (f"{request.method} {request.url.path} -> "
                f"{response.status_code} in {elapsed:.0f}ms")
        if user:
            line += f" user={user}"
        log = logging.getLogger("app.access")
        if elapsed >= _SLOW_MS:
            log.warning("%s (slow)", line)
        else:
            log.info(line)
        return response
