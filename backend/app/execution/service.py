"""Execution service — single entry point for all LLM calls."""

import json

from app.core.config import Settings, settings
from app.execution.base import ExecutionResult, traceable
from app.execution.factory import get_adapter


@traceable(name="execution-run")
def execute(
    *,
    provider: str,
    model_api_id: str,
    prompt: str,
    system_prompt: str | None = None,
    json_mode: bool = False,
    max_tokens: int | None = None,
    app_settings: Settings | None = None,
) -> ExecutionResult:
    """Run one provider call through the factory-resolved adapter."""
    cfg = app_settings or settings
    adapter = get_adapter(provider, cfg)
    if max_tokens is not None:
        adapter.max_tokens = max_tokens
    return adapter.execute(
        model_api_id=model_api_id,
        prompt=prompt,
        system_prompt=system_prompt,
        json_mode=json_mode,
    )


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
