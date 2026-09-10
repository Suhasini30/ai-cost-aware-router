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

import time

from app.core.config import Settings, settings
from app.eval.evaluator import evaluate_answer
from app.eval.schemas import AskResponse
from app.execution.base import traceable
from app.execution.service import execute
from app.router.agent import classify_prompt
from app.router.policy import route_decision, strongest_capable
from app.router.schemas import RouteStage


@traceable(name="router-ask-pipeline")
def answer_prompt(
    prompt: str,
    app_settings: Settings | None = None,
) -> AskResponse:
    """Run the full pipeline and return the final answer with its trace."""
    cfg = app_settings or settings
    started = time.perf_counter()

    decision, classifier_used, _, classify_tokens = classify_prompt(
        prompt, app_settings=cfg
    )
    selected, trace, fallback = route_decision(
        decision, threshold=cfg.confidence_threshold
    )

    first = execute(
        provider=selected.provider.value,
        model_api_id=selected.api_id,
        prompt=prompt,
        capability=decision.capability,
        tier=selected.tier.value,
        app_settings=cfg,
    )
    verdict = evaluate_answer(prompt, first.text, app_settings=cfg)

    ok = verdict.passed and verdict.quality_score >= cfg.quality_pass_threshold
    escalated = False
    final = first
    if not ok:
        try:
            strong = strongest_capable(decision)
        except ValueError:
            strong = None
        if strong is None:
            # No strong model to escalate to: keep the initial answer
            # instead of turning a quality failure into a 500.
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
            # Verdict-only re-evaluation: the returned verdict must belong
            # to the FINAL answer. Never escalates a second time.
            verdict = evaluate_answer(prompt, final.text, app_settings=cfg)
            trace.append(
                RouteStage(
                    stage="escalation",
                    rule="initial answer failed quality threshold; "
                    f"escalated to {strong.id}",
                    kept=[strong.id],
                )
            )
            selected, escalated = strong, True

    latency_ms = (time.perf_counter() - started) * 1000.0
    tokens = (classify_tokens or 0) + (final.total_tokens or 0)
    return AskResponse(
        answer=final.text,
        selected_model=selected,
        escalated=escalated,
        decision=decision,
        verdict=verdict,
        classifier_model_used=classifier_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
        trace=trace,
        fallback=fallback,
    )
