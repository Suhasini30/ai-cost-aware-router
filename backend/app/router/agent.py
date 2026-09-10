"""Prompt classifier — structured analysis, never answers the prompt.

Uses the FIXED strongest classifier model from settings (accuracy first).
Cost-aware model selection is Phase 4 and must not leak in here:
this module never imports the registry selection helpers.

Failure policy: any live-call problem (no key, network error, bad JSON,
schema validation error) degrades to the deterministic keyword fallback
so the endpoint never 500s on classifier issues.
"""

import json
import re
import time
from typing import Any, Callable

import httpx

from app.core.config import Settings, settings
from app.router.schemas import RouterDecision

try:  # langsmith is optional at runtime; tests/dev work without it
    from langsmith import traceable
except ImportError:  # pragma: no cover - exercised when langsmith missing

    def traceable(*args: Any, **kwargs: Any) -> Callable:
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]

        def wrap(fn: Callable) -> Callable:
            return fn

        return wrap


FALLBACK_MODEL = "fallback"

_SYSTEM_PROMPT = """You classify user prompts for a cost-aware model router.
Reply with JSON ONLY, exactly these keys:
{"task_type": "summarization|coding|math|general_qa|image",
 "complexity": "low|high",
 "capability": "text|coding|reasoning|image",
 "quality_required": "standard|high",
 "confidence": <0.0-1.0>,
 "reason": "<one short sentence>"}"""

_IMAGE_RE = re.compile(r"\b(image|images|draw|drawing|paint|picture|photo|logo|illustration|diagram)\b")
_CODE_RE = re.compile(r"\b(code|coding|debug|function|class|bug|script|program|api|sql|refactor|compile|deploy)\b")
_MATH_RE = re.compile(r"\b(calculat|solve|equation|math|integral|derivative|algebra|statistic|percent|theorem|proof)\b")
_SUMMARY_RE = re.compile(r"\b(summar\w*|tldr|tl;dr|shorten\w*|condens\w*|recap)\b")
_COMPLEX_RE = re.compile(r"\b(complex|algorithm|architect|optimiz|distributed|concurren|production|critical)\b")


def fallback_classify(prompt: str, threshold: float = 0.75) -> RouterDecision:
    """Deterministic keyword heuristic (offline/dev safe)."""
    text = prompt.lower()
    if _IMAGE_RE.search(text):
        return RouterDecision(
            task_type="image",
            complexity="high",
            capability="image",
            quality_required="high",
            confidence=max(0.0, threshold - 0.1),
            reason="Fallback: prompt mentions image/visual content.",
        )
    if _CODE_RE.search(text):
        complex_ = bool(_COMPLEX_RE.search(text) or len(prompt) > 200)
        return RouterDecision(
            task_type="coding",
            complexity="high" if complex_ else "low",
            capability="coding",
            quality_required="high" if complex_ else "standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt contains code-related keywords.",
        )
    if _MATH_RE.search(text) or (
        re.search(r"\d", text) and re.search(r"[+\-*/=^]", text)
    ):
        complex_ = bool(_COMPLEX_RE.search(text) or len(prompt) > 200)
        return RouterDecision(
            task_type="math",
            complexity="high" if complex_ else "low",
            capability="reasoning",
            quality_required="high" if complex_ else "standard",
            confidence=max(0.0, threshold - 0.1),
            reason="Fallback: prompt looks like a math problem.",
        )
    if _SUMMARY_RE.search(text):
        return RouterDecision(
            task_type="summarization",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt asks for a summary.",
        )
    return RouterDecision(
        task_type="general_qa",
        complexity="low",
        capability="text",
        quality_required="standard",
        confidence=max(0.0, threshold - 0.15),
        reason="Fallback: no specific signals, treating as general question.",
    )


def _call_mistral(prompt: str, app_settings: Settings) -> tuple[dict, int | None]:
    """Call the fixed Mistral classifier; returns (parsed JSON, tokens|None)."""
    with httpx.Client(timeout=app_settings.classifier_timeout_s) as client:
        resp = client.post(
            "https://api.mistral.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {app_settings.mistral_api_key}"},
            json={
                "model": app_settings.classifier_model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        body = resp.json()
    content = body["choices"][0]["message"]["content"]
    usage = (body.get("usage") or {}).get("total_tokens")
    return json.loads(content), usage


def _call_gemini(prompt: str, app_settings: Settings) -> tuple[dict, int | None]:
    """Call the fixed Gemini classifier; returns (parsed JSON, tokens|None)."""
    model = app_settings.classifier_model
    with httpx.Client(timeout=app_settings.classifier_timeout_s) as client:
        resp = client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": app_settings.gemini_api_key or ""},
            json={
                "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": 300,
                    "responseMimeType": "application/json",
                },
            },
        )
        resp.raise_for_status()
        body = resp.json()
    text = body["candidates"][0]["content"]["parts"][0]["text"]
    tokens = (body.get("usageMetadata") or {}).get("totalTokenCount")
    return json.loads(text), tokens


@traceable(name="router-classify")
def classify_prompt(
    prompt: str,
    app_settings: Settings | None = None,
) -> tuple[RouterDecision, str, float, int | None]:
    """Classify a prompt.

    Returns (decision, model_used, latency_ms, tokens_used|None).
    `model_used` is the fixed classifier model, or "fallback".
    """
    cfg = app_settings or settings
    started = time.perf_counter()
    provider = (cfg.classifier_provider or "").lower()

    try:
        if provider == "mistral" and cfg.mistral_api_key:
            payload, tokens = _call_mistral(prompt, cfg)
        elif provider == "gemini" and cfg.gemini_api_key:
            payload, tokens = _call_gemini(prompt, cfg)
        else:
            raise RuntimeError("no provider key for classifier")
        decision = RouterDecision(**payload)
        model_used = cfg.classifier_model
    except Exception:
        decision = fallback_classify(prompt, cfg.confidence_threshold)
        model_used, tokens = FALLBACK_MODEL, None

    latency_ms = (time.perf_counter() - started) * 1000.0
    return decision, model_used, latency_ms, tokens
