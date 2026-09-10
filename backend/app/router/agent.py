"""Prompt classifier — structured analysis, never answers the prompt.

Uses the FIXED strongest classifier model from settings (accuracy first).
Cost-aware model selection is Phase 4 and must not leak in here:
this module never imports the registry selection helpers.

Provider calls go through the execution service (Phase 5): this module
contains no provider-specific code.

Failure policy: any live-call problem (no key, network error, bad JSON,
schema validation error) degrades to the deterministic keyword fallback
so the endpoint never 500s on classifier issues.
"""

import re
import time

from app.core.config import Settings, settings
from app.execution.base import traceable
from app.execution.service import execute_json
from app.router.schemas import RouterDecision


FALLBACK_MODEL = "fallback"

_SYSTEM_PROMPT = """You classify user prompts for a cost-aware model router.
Reply with JSON ONLY, exactly these keys:
{"task_type": "summarization|coding|math|general_qa|image|classification|extraction",
 "complexity": "low|high",
 "capability": "text|coding|reasoning|image",
 "quality_required": "standard|high",
 "confidence": <0.0-1.0>,
 "reason": "<one short sentence>"}"""

_IMAGE_RE = re.compile(r"\b(image|images|draw|drawing|paint|picture|photo|logo|illustration|diagram)\b")
_CODE_RE = re.compile(r"\b(code|coding|debug|function|class|bug|script|program|api|sql|refactor|compile|deploy)\b")
_MATH_RE = re.compile(r"\b(calculat|solve|equation|math|integral|derivative|algebra|statistic|percent|theorem|proof)\b")
_SUMMARY_RE = re.compile(r"\b(summar\w*|tldr|tl;dr|shorten\w*|condens\w*|recap)\b")
_CLASSIFY_RE = re.compile(r"\b(classif\w*|categor\w*|sentiment|spam|ham|label\b|labels|tag\b|tags)\b")
_EXTRACT_RE = re.compile(r"\b(extract\w*|entit\w*|keywords?|key phrases?|parse|line items?|fields?)\b")
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
    if _CLASSIFY_RE.search(text):
        return RouterDecision(
            task_type="classification",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt asks to classify or label content.",
        )
    if _EXTRACT_RE.search(text):
        return RouterDecision(
            task_type="extraction",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt asks to extract structured data.",
        )
    return RouterDecision(
        task_type="general_qa",
        complexity="low",
        capability="text",
        quality_required="standard",
        confidence=max(0.0, threshold - 0.15),
        reason="Fallback: no specific signals, treating as general question.",
    )


@traceable(name="router-classify")
def classify_prompt(
    prompt: str,
    app_settings: Settings | None = None,
) -> tuple[RouterDecision, str, float, int | None]:
    """Classify a prompt via the execution service.

    Returns (decision, model_used, latency_ms, tokens_used|None).
    `model_used` is the fixed classifier model, or "fallback".
    """
    cfg = app_settings or settings
    started = time.perf_counter()

    try:
        payload, result = execute_json(
            provider=cfg.classifier_provider or "",
            model_api_id=cfg.classifier_model,
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=300,  # classification budget (not the execution default)
            app_settings=cfg,
        )
        decision = RouterDecision(**payload)
        model_used, tokens = cfg.classifier_model, result.total_tokens
    except Exception:
        decision = fallback_classify(prompt, cfg.confidence_threshold)
        model_used, tokens = FALLBACK_MODEL, None

    latency_ms = (time.perf_counter() - started) * 1000.0
    return decision, model_used, latency_ms, tokens
