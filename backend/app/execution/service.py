"""Execution service — single entry point for all LLM calls.

Phase 7 reliability lives here (not in a parallel layer): every call
gets same-provider retries with backoff, then failover to a capable
alternative provider. Callers (including the Phase 6 pipeline) change
nothing — they just gain resilience. Quality verdicts are untouched:
this layer reacts to transport errors only, never to answer content.
"""

import json
import time
from collections.abc import Callable

from app.core.config import Settings, settings
from app.execution.base import (
    ExecutionResult,
    ProviderUnavailableError,
    traceable,
)
from app.execution.factory import get_adapter
from app.reliability.fallback import alternatives
from app.reliability.retry import backoff_delays, is_retryable


@traceable(name="execution-run")
def execute(
    *,
    provider: str,
    model_api_id: str,
    prompt: str,
    system_prompt: str | None = None,
    json_mode: bool = False,
    max_tokens: int | None = None,
    capability: str | None = None,
    tier: str | None = None,
    max_retries: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
    app_settings: Settings | None = None,
) -> ExecutionResult:
    """Run one provider call with retries + capable-provider failover.

    `capability`/`tier` hints select the failover pool (same tier +
    capability tags, different provider); without them only the primary
    provider is retried. Raises ProviderUnavailableError when every
    compatible target fails.
    """
    cfg = app_settings or settings
    budget = cfg.reliability_max_retries if max_retries is None else max_retries
    delays = backoff_delays(budget, cfg.reliability_backoff_base_s)

    targets = [(provider, model_api_id)]
    if capability is not None:
        targets += [
            (m.provider.value, m.api_id)
            for m in alternatives(
                capability=capability,
                tier=tier,
                exclude_provider=(provider or "").lower() or None,
            )
        ]

    errors: list[str] = []
    slept = 0
    tried: list[str] = []
    for index, (tgt_provider, tgt_model) in enumerate(targets):
        if tgt_provider not in tried:
            tried.append(tgt_provider)
        try:
            adapter = get_adapter(tgt_provider, cfg)
        except ValueError as exc:
            # Missing key / unknown provider: skip to the next compatible
            # target instead of aborting the whole failover loop.
            errors.append(f"{type(exc).__name__}")
            continue
        if max_tokens is not None:
            adapter.max_tokens = max_tokens
        attempt = 0
        while True:
            try:
                result = adapter.execute(
                    model_api_id=tgt_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    json_mode=json_mode,
                )
                result.retry_count = slept
                if index > 0:
                    result.fallback_used = True
                    result.provider = tgt_provider
                    result.model_api_id = tgt_model
                    result.fallback_reason = (
                        f"{provider} failed ({errors[0]}); "
                        f"fell back to {tgt_provider}/{tgt_model}"
                    )
                return result
            except Exception as exc:  # noqa: BLE001 — classified below
                errors.append(f"{type(exc).__name__}")
                if is_retryable(exc) and attempt < budget:
                    sleep_fn(delays[attempt])
                    slept += 1
                    attempt += 1
                    continue
                if not is_retryable(exc):
                    # Deterministic client error (bad request, bad key,
                    # unknown model): retrying or fanning out to other
                    # providers cannot fix it — stop immediately.
                    raise
                break  # next target (or terminal raise below)

    raise ProviderUnavailableError(
        f"All compatible providers failed: {'; '.join(errors)}",
        attempts=slept + len(errors),
        providers_tried=tried,
    ) from None


def execute_json(
    *,
    provider: str,
    model_api_id: str,
    prompt: str,
    system_prompt: str | None = None,
    max_tokens: int | None = None,
    app_settings: Settings | None = None,
) -> tuple[dict, ExecutionResult]:
    """Execute with JSON mode and parse the response body.

    Raises json.JSONDecodeError on non-JSON output (callers decide
    fallback policy).
    """
    result = execute(
        provider=provider,
        model_api_id=model_api_id,
        prompt=prompt,
        system_prompt=system_prompt,
        json_mode=True,
        max_tokens=max_tokens,
        app_settings=app_settings,
    )
    return json.loads(result.text), result
