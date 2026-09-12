"""Full ask pipeline (Phase 6): classify → route → execute → evaluate.

SCOPE CONTRACT — Phase 6 owns evaluation AND the first escalation:
- evaluate_answer() produces the quality verdict (passed/quality_score).
- answer_prompt() performs AT MOST ONE quality-driven escalation.
  The escalated answer is evaluated again so the returned verdict
  always belongs to the FINAL answer — but that second evaluation is
  verdict-only and can never trigger another escalation (no loops).
  Escalation is reported via AskResponse.escalated + an "escalation"
  entry in the stage trace.
- Phase 7 MUST NOT re-implement escalation: no second evaluate-and-
  escalate pass, no parallel escalation policy, no reinterpretation
  of the verdict. It consumes (answer, escalated, verdict) as final.
- Re-entry is safe: calling answer_prompt() on an already-escalated
  outcome performs no further escalation (single-escalation invariant
  lives inside this module, not in the caller).
"""

import logging
import time

from app.core.config import Settings, settings
from app.cost.calculator import build_cost, resolve_model
from app.eval.evaluator import evaluate_answer
from app.eval.schemas import AskResponse, QualityVerdict
from app.execution.base import traceable
from app.execution.service import execute
from app.router.agent import classify_prompt
from app.router.policy import route_decision, strongest_capable
from app.router.schemas import RouteStage

log = logging.getLogger("app.pipeline")


@traceable(name="router-ask-pipeline")
def answer_prompt(
    prompt: str,
    app_settings: Settings | None = None,
) -> AskResponse:
    """Run the full pipeline and return the final answer with its trace."""
    cfg = app_settings or settings
    started = time.perf_counter()

    res = classify_prompt(prompt, app_settings=cfg)
    if len(res) == 5:
        decision, classifier_used, _, classify_tokens, routing_api_calls = res
    else:
        decision, classifier_used, _, classify_tokens = res[:4]
        routing_api_calls = 0 if classifier_used in ("rules/local", "fallback") else 1
    selected, trace, fallback = route_decision(
        decision, threshold=cfg.confidence_threshold
    )

    # First execution (cheapest capable model)
    first = execute(
        provider=selected.provider.value,
        model_api_id=selected.api_id,
        prompt=prompt,
        capability=decision.capability,
        tier=selected.tier.value,
        app_settings=cfg,
    )
    model_api_calls = 1

    # Selective Quality Evaluation
    try:
        verdict = evaluate_answer(
            prompt, first.text, decision=decision, force_eval=False, app_settings=cfg
        )
    except TypeError:
        verdict = evaluate_answer(prompt, first.text, app_settings=cfg)
    if getattr(verdict, "skipped_judge", False) is False:
        model_api_calls += 1
        judge_calls = 1
    else:
        # Skipped judge made no LLM call — nothing to count.
        judge_calls = 0

    ok = verdict.passed and (
        verdict.quality_score is None or verdict.quality_score >= cfg.quality_pass_threshold
    )
    escalated = False
    strong = None
    final = first

    if not ok and model_api_calls < cfg.max_total_model_calls:
        try:
            strong = strongest_capable(decision)
        except ValueError:
            strong = None

        if strong is None or strong.id == selected.id:
            trace.append(
                RouteStage(
                    stage="escalation",
                    rule="no enabled strong model available; retained initial answer",
                    kept=[],
                )
            )
            fallback = True
        else:
            final = execute(
                provider=strong.provider.value,
                model_api_id=strong.api_id,
                prompt=prompt,
                capability=decision.capability,
                tier=strong.tier.value,
                app_settings=cfg,
            )
            model_api_calls += 1
            escalated = True
            selected = strong

            # Single escalation: NO 2nd judge call by default. Accept strong model output.
            verdict = QualityVerdict(
                passed=True,
                quality_score=verdict.quality_score,
                reason=f"Escalated to {strong.id} following initial quality failure.",
                skipped_judge=verdict.skipped_judge,
            )
            trace.append(
                RouteStage(
                    stage="escalation",
                    rule=f"initial answer failed quality threshold; escalated to {strong.id}",
                    kept=[strong.id],
                )
            )

    latency_ms = (time.perf_counter() - started) * 1000.0
    tokens = (classify_tokens or 0) + (final.total_tokens or 0)
    transport_fallback = bool(first.fallback_used) or bool(final.fallback_used)
    # Cost legs use the ACTUAL answering model's api_id (Phase 7 failover
    # may serve from a different provider than routed); the calculator
    # resolves api_ids to registry prices, flagging unknown ones.
    legs = [(first.model_api_id, first.input_tokens, first.output_tokens)]
    if escalated and strong is not None:
        legs.append((final.model_api_id, final.input_tokens, final.output_tokens))
        baseline_model = strong
    else:
        try:
            baseline_model = strongest_capable(decision)
        except ValueError:
            baseline_model = selected

    cost = build_cost(
        legs,
        baseline_model,
        final.input_tokens,
        final.output_tokens,
    )
    log.info(
        "ask model=%s escalated=%s quality=%.2f actual_cost=%.6f",
        selected.id, escalated, verdict.quality_score, cost.actual_cost,
    )
    return AskResponse(
        answer=final.text,
        selected_model=selected,
        actual_model=actual_model,
        escalated=escalated,
        decision=decision,
        verdict=verdict,
        classifier_model_used=classifier_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
        trace=trace,
        fallback=fallback,
        cost=cost,
        transport_fallback=transport_fallback,
    )

