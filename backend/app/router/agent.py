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

import logging
import time

from app.core.config import Settings, settings
from app.execution.base import traceable
from app.execution.service import execute_json
from app.router.rules import (
    compile_category_patterns,
    compile_complexity_pattern,
    looks_like_math_expression,
    match_rules,
)
from app.router.schemas import RouterDecision

log = logging.getLogger("app.router")


FALLBACK_MODEL = "fallback"

_SYSTEM_PROMPT = """You classify user prompts for a cost-aware model router.
Reply with JSON ONLY, exactly these keys:
{"task_type": "summarization|coding|math|general_qa|image|classification|extraction",
 "complexity": "low|high",
 "capability": "text|coding|reasoning|image",
 "quality_required": "standard|high",
 "confidence": <0.0-1.0>,
 "reason": "<one short sentence>"}"""


def rule_classify_prompt(prompt: str,
                         app_settings: Settings | None = None,
                         ) -> RouterDecision | None:
    """Deterministic fast-router for obvious task patterns (0 API calls).

    Matches against the data-driven rule table; thresholds come from
    settings. Returns None for ambiguous prompts (LLM fallback follows).
    """
    cfg = app_settings or settings
    text = prompt.strip().lower()
    rule = match_rules(
        text,
        max_simple_qa_chars=cfg.router_rule_max_simple_qa_chars,
    )
    if rule is None:
        return None
    return RouterDecision(
        task_type=rule["task_type"],
        complexity=rule["complexity"],
        capability=rule["capability"],
        quality_required=rule["quality_required"],
        confidence=1.0,
        reason=rule["reason"],
        needs_verification=False,
        is_rule_classified=True,
    )


def fallback_classify(prompt: str, threshold: float = 0.75,
                        app_settings: Settings | None = None,
                        ) -> RouterDecision:
    """Deterministic keyword heuristic (offline/dev safe).

    Patterns come from the rules table; the complexity keyword list and
    the long-prompt cutoff come from settings (env-configurable).
    """
    cfg = app_settings or settings
    pats = compile_category_patterns()
    complex_pat = compile_complexity_pattern(
        cfg.high_complexity_keyword_list())
    long_n = cfg.router_complexity_long_prompt_chars
    text = prompt.lower()
    if pats["image"].search(text):
        return RouterDecision(
            task_type="image",
            complexity="high",
            capability="image",
            quality_required="high",
            confidence=max(0.0, threshold - 0.1),
            reason="Fallback: prompt mentions image/visual content.",
            needs_verification=True,
        )
    if pats["code"].search(text):
        complex_ = bool(complex_pat.search(text) or len(prompt) > long_n)
        return RouterDecision(
            task_type="coding",
            complexity="high" if complex_ else "low",
            capability="coding",
            quality_required="high" if complex_ else "standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt contains code-related keywords.",
            needs_verification=complex_,
        )
    if pats["math"].search(text) or looks_like_math_expression(text):
        complex_ = bool(complex_pat.search(text) or len(prompt) > long_n)
        return RouterDecision(
            task_type="math",
            complexity="high" if complex_ else "low",
            capability="reasoning",
            quality_required="high" if complex_ else "standard",
            confidence=max(0.0, threshold - 0.1),
            reason="Fallback: prompt looks like a math problem.",
            needs_verification=complex_,
        )
    if pats["summary"].search(text):
        return RouterDecision(
            task_type="summarization",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt asks for a summary.",
            needs_verification=False,
        )
    if pats["classify"].search(text):
        return RouterDecision(
            task_type="classification",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt asks to classify or label content.",
            needs_verification=False,
        )
    if pats["extract"].search(text):
        return RouterDecision(
            task_type="extraction",
            complexity="low",
            capability="text",
            quality_required="standard",
            confidence=max(0.0, threshold - 0.05),
            reason="Fallback: prompt asks to extract structured data.",
            needs_verification=False,
        )
    return RouterDecision(
        task_type="general_qa",
        complexity="low",
        capability="text",
        quality_required="standard",
        confidence=max(0.0, threshold - 0.15),
        reason="Fallback: no specific signals, treating as general question.",
        needs_verification=False,
    )


@traceable(name="router-classify")
def classify_prompt(
    prompt: str,
    app_settings: Settings | None = None,
) -> tuple[RouterDecision, str, float, int | None, int]:
    """Classify a prompt via rule router or execution service.

    Returns (decision, model_used, latency_ms, tokens_used|None, routing_api_calls).
    `model_used` is "rules/local", the fixed classifier model, or "fallback".
    """
    cfg = app_settings or settings
    started = time.perf_counter()

    # Step 1: Try Fast Rule Router (0 LLM API calls)
    rule_decision = rule_classify_prompt(prompt)
    if rule_decision is not None:
        latency_ms = (time.perf_counter() - started) * 1000.0
        return rule_decision, "rules/local", latency_ms, 0, 0

    # Step 2: Fall through to LLM Classifier (1 LLM API call)
    try:
        payload, result = execute_json(
            provider=cfg.classifier_provider or "",
            model_api_id=cfg.classifier_model,
            prompt=prompt,
            system_prompt=(cfg.router_classifier_system_prompt
                           or _SYSTEM_PROMPT),
            max_tokens=300,
            app_settings=cfg,
        )
        decision = RouterDecision(**payload)
        model_used, tokens, routing_calls = cfg.classifier_model, result.total_tokens, 1
    except Exception as exc:
        log.info("classifier fallback: %s", type(exc).__name__)
        decision = fallback_classify(prompt, cfg.confidence_threshold)
        model_used, tokens, routing_calls = FALLBACK_MODEL, None, 0

    latency_ms = (time.perf_counter() - started) * 1000.0
    return decision, model_used, latency_ms, tokens, routing_calls

