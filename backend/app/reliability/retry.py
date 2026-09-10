"""Retry policy (Phase 7): which provider errors are worth retrying.

Transport problems and server-side/rate-limit statuses are transient;
client errors (bad key, bad request, unknown model) will fail identically
on retry and must surface immediately.
"""

import httpx

# HTTP statuses worth one more attempt (408 is rare; kept for completeness).
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

# Client errors: retrying is pointless.
NON_RETRYABLE_STATUS = {400, 401, 403, 404}


def status_of(exc: BaseException) -> int | None:
    """Extract an HTTP status from an httpx error, if it carries one."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    return None


def is_retryable(exc: BaseException) -> bool:
    """True when another attempt against the same provider may succeed."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status in NON_RETRYABLE_STATUS:
            return False
        return status in RETRYABLE_STATUS or status >= 500
    # Timeouts, dropped connections, DNS failures: transient.
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


def backoff_delays(max_retries: int, base_s: float = 0.5) -> list[float]:
    """Exponential backoff waits between attempts (0.5, 1.0, 2.0, ...)."""
    return [base_s * (2**n) for n in range(max_retries)]
