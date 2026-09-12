"""Cost-aware routing policy (Phase 4).

Pipeline: capability filter → confidence gate → complexity gate
→ quality gate → cheapest-capable pick (summed input+output price).

Pure function over the static registry: no LLM calls, no prompt I/O.
`confidence` here is CLASSIFICATION confidence from Phase 3 — it must
never be confused with answer quality (a Phase 6 concern).
"""

import logging

from app.models.registry import CAPABILITY_TAGS, ModelSpec, Tier, list_models
from app.router.agent import traceable
from app.router.schemas import RouteStage, RouterDecision

log = logging.getLogger("app.router")


def _cost_key(m: ModelSpec) -> tuple[float, str]:
    """Summed per-1K price (both directions), then id for determinism."""
    return (m.input_cost_per_1k + m.output_cost_per_1k, m.id)


def _cheapest(candidates: list[ModelSpec]) -> ModelSpec:
    return min(candidates, key=_cost_key)


def _safe_fallback(
    pool: list[ModelSpec], trace: list[RouteStage]
) -> tuple[ModelSpec, list[RouteStage], bool]:
    """Enabled-only safety net (never returns a disabled model).

    Order: cheapest strong in the capable pool → cheapest enabled
    strong globally → cheapest capable → cheapest enabled overall.
    Raises ValueError only when the registry has no enabled models
    at all (misconfiguration, not a routing outcome).
    """
    strong = [m for m in pool if m.tier == Tier.STRONG]
    if strong:
        return _cheapest(strong), trace, True
    enabled = [m for m in list_models() if m.enabled]
    strong_all = [m for m in enabled if m.tier == Tier.STRONG]
    if strong_all:
        return _cheapest(strong_all), trace, True
    if pool:
        return _cheapest(pool), trace, True
    if enabled:
        return _cheapest(enabled), trace, True
    log.warning("routing dead-end: registry has no enabled models")
    raise ValueError("No enabled models in registry")


def strongest_capable(decision: RouterDecision) -> ModelSpec:
    """Cheapest enabled strong model matching the decision's capability.

    Used for Phase 6 quality-driven escalation (and only there).
    Falls back to the cheapest enabled strong globally; raises
    ValueError only when no enabled strong model exists at all.
    """
    required = CAPABILITY_TAGS[decision.capability]
    capable = [
        m
        for m in list_models()
        if m.enabled and (required & set(m.capabilities))
    ]
    strong = [m for m in capable if m.tier == Tier.STRONG]
    if strong:
        return _cheapest(strong)
    enabled_strong = [
        m for m in list_models() if m.enabled and m.tier == Tier.STRONG
    ]
    if enabled_strong:
        return _cheapest(enabled_strong)
    raise ValueError("No enabled strong model for escalation")


@traceable(name="router-policy")
def route_decision(
    decision: RouterDecision,
    threshold: float = 0.75,
) -> tuple[ModelSpec, list[RouteStage], bool]:
    """Select the cheapest capable model for a classification.

    Returns (selected_model, stage_trace, fallback_flag).
    Never returns a disabled model. Degrades to the cheapest enabled
    strong model and flags `fallback=True` when the pipeline empties.
    Raises ValueError only when the registry has no enabled models
    at all.
    """
    trace: list[RouteStage] = []
    candidates = [m for m in list_models() if m.enabled]

    # 1. Capability filter.
    required = CAPABILITY_TAGS[decision.capability]
    candidates = [
        m for m in candidates if required & set(m.capabilities)
    ]
    trace.append(
        RouteStage(
            stage="capability",
            rule=f"capability={decision.capability} requires one of {sorted(required)}",
            kept=[m.id for m in candidates],
        )
    )
    if not candidates:
        return _safe_fallback([], trace)

    # 2-4. Tier gates: confidence escalation, complexity, then quality.
    # Quality=high OVERRIDES (replaces) the tier set instead of
    # intersecting it, so low-complexity + high-quality lands on strong
    # without emptying the pipeline into the safety fallback.
    escalated = decision.confidence < threshold
    if escalated:
        tier_allow = {Tier.STRONG}
        trace.append(
            RouteStage(
                stage="confidence",
                rule=f"confidence={decision.confidence} < threshold={threshold}: escalate to strong",
                kept=[m.id for m in candidates if m.tier in tier_allow],
            )
        )
        trace.append(
            RouteStage(
                stage="complexity",
                rule="skipped: already escalated to strong",
                kept=[m.id for m in candidates if m.tier in tier_allow],
            )
        )
    else:
        trace.append(
            RouteStage(
                stage="confidence",
                rule=f"confidence={decision.confidence} >= threshold={threshold}: keep tiers",
                kept=[m.id for m in candidates],
            )
        )
        tier_allow = {Tier.FAST} if decision.complexity == "low" else {Tier.STRONG}
        trace.append(
            RouteStage(
                stage="complexity",
                rule=f"complexity={decision.complexity}: {[t.value for t in tier_allow]} tier only",
                kept=[m.id for m in candidates if m.tier in tier_allow],
            )
        )

    if decision.quality_required == "high":
        tier_allow = {Tier.STRONG}
        trace.append(
            RouteStage(
                stage="quality",
                rule="quality_required=high: override to strong tier",
                kept=[m.id for m in candidates if m.tier in tier_allow],
            )
        )
    else:
        trace.append(
            RouteStage(
                stage="quality",
                rule="quality_required=standard: no restriction",
                kept=[m.id for m in candidates if m.tier in tier_allow],
            )
        )
    candidates = [m for m in candidates if m.tier in tier_allow]

    # 5. Cheapest capable pick; empty → enabled-only safe fallback.
    if not candidates:
        capable = [
            m
            for m in list_models()
            if m.enabled and (required & set(m.capabilities))
        ]
        return _safe_fallback(capable, trace)
    return _cheapest(candidates), trace, False
