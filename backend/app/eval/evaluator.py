"""LLM quality judge (Phase 6).

Scores a generated ANSWER — never the classification. Judge-call
failure degrades to conservative `passed=False` (routes into the
single escalation instead of 500ing).
"""

from app.core.config import Settings, settings
from app.eval.schemas import QualityVerdict
from app.execution.base import traceable
from app.execution.service import execute_json

_JUDGE_PROMPT = """You grade an AI answer for a user prompt.
Reply with JSON ONLY, exactly these keys:
{"passed": true|false,
 "quality_score": <0.0-1.0>,
 "reason": "<one short sentence>"}
Grade on relevance, factual accuracy, and completeness. Pass answers
that genuinely help; fail refusals, off-topic text, or empty answers."""


@traceable(name="quality-eval")
def evaluate_answer(
    prompt: str,
    answer: str,
    app_settings: Settings | None = None,
) -> QualityVerdict:
    """Judge an answer, returning a fail-safe verdict."""
    cfg = app_settings or settings
    try:
        payload, _ = execute_json(
            provider=cfg.judge_provider or "",
            model_api_id=cfg.judge_model,
            prompt=f"USER PROMPT:\n{prompt}\n\nANSWER:\n{answer}",
            system_prompt=_JUDGE_PROMPT,
            max_tokens=300,
            app_settings=cfg,
        )
        return QualityVerdict(**payload)
    except Exception:
        return QualityVerdict(
            passed=False,
            quality_score=0.0,
            reason="Judge unavailable; failing safe toward escalation.",
        )
