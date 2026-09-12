"""LLM quality judge (Phase 6).

Scores a generated ANSWER — never the classification. Judge-call
failure degrades to conservative `passed=False` (routes into the
single escalation instead of 500ing).
"""

import logging

from app.core.config import Settings, settings
from app.eval.schemas import QualityVerdict
from app.execution.base import traceable
from app.execution.service import execute_json

from app.router.schemas import RouterDecision

log = logging.getLogger("app.eval")

_JUDGE_PROMPT = """You grade an AI answer for a user prompt.
Reply with JSON ONLY, exactly these keys:
{"passed": true|false,
 "quality_score": <0.0-1.0>,
 "reason": "<one short sentence>"}
Grade on relevance, factual accuracy, and completeness. Pass answers
that genuinely help; fail refusals, off-topic text, or empty answers."""


def should_evaluate(decision: RouterDecision | None, answer: str,
                      app_settings: Settings | None = None) -> bool:
    """Determine if an answer requires LLM Quality Judge verification.

    Task types and the short-answer cutoff come from settings
    (ROUTER_JUDGE_TASK_TYPES / ROUTER_JUDGE_MIN_ANSWER_CHARS).
    Returns True if prompt triggers (needs_verification, high complexity, high
    quality requirement, listed task type) OR answer triggers (too short,
    truncated, contains error markers). Returns False otherwise to skip
    the judge and save LLM API calls.
    """
    cfg = app_settings or settings
    min_chars = cfg.router_judge_min_answer_chars
    judge_tasks = {t.strip().lower()
                   for t in cfg.router_judge_task_types.split(",") if t.strip()}
    clean_ans = (answer or "").strip()
    if len(clean_ans) < min_chars or clean_ans.startswith(("Error:", "Failed:", "500", "502")):
        return True

    if decision is not None:
        if decision.needs_verification:
            return True
        if decision.complexity == "high":
            return True
        if decision.quality_required == "high":
            return True
        if decision.task_type in judge_tasks:
            return True

    return False


@traceable(name="quality-eval")
def evaluate_answer(
    prompt: str,
    answer: str,
    decision: RouterDecision | None = None,
    force_eval: bool = False,
    app_settings: Settings | None = None,
) -> QualityVerdict:
    """Judge an answer selectively, returning a fail-safe verdict.

    If force_eval is False and should_evaluate() is False, skips the judge
    LLM call and returns passed=True with quality_score=None and skipped_judge=True.
    """
    cfg = app_settings or settings

    if not force_eval and not should_evaluate(decision, answer, cfg):
        return QualityVerdict(
            passed=True,
            quality_score=None,
            reason="Skipped judge: prompt & answer passed low-risk criteria.",
            skipped_judge=True,
        )

    try:
        payload, _ = execute_json(
            provider=cfg.judge_provider or "",
            model_api_id=cfg.judge_model,
            prompt=f"USER PROMPT:\n{prompt}\n\nANSWER:\n{answer}",
            system_prompt=_JUDGE_PROMPT,
            max_tokens=300,
            app_settings=cfg,
        )
        return QualityVerdict(**payload, skipped_judge=False)
    except Exception as exc:
        log.warning(
            "judge failed (%s/%s): %s; failing safe toward escalation",
            cfg.judge_provider, cfg.judge_model, type(exc).__name__,
        )
        return QualityVerdict(
            passed=False,
            quality_score=0.0,
            reason="Judge unavailable; failing safe toward escalation.",
            skipped_judge=False,
        )

