"""Evaluation schemas (Phase 6).

`quality_score` / `passed` describe ANSWER quality. They are deliberately
named apart from `RouterDecision.confidence`, which is CLASSIFICATION
confidence (Correction #2 — never mix these fields).
"""

from pydantic import BaseModel, Field

from app.cost.schemas import CostResult
from app.models.registry import ModelSpec
from app.router.schemas import RouteStage, RouterDecision


class QualityVerdict(BaseModel):
    passed: bool
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    reason: str
    skipped_judge: bool = False
    # Rejection transparency: populated by the judge when it fails an
    # answer; always optional so older payloads still validate.
    issues: list[str] = Field(default_factory=list)
    improvement_instructions: str | None = None


class AskRequest(BaseModel):
    prompt: str


class AskResponse(BaseModel):
    answer: str
    selected_model: ModelSpec
    escalated: bool
    decision: RouterDecision
    verdict: QualityVerdict
    classifier_model_used: str
    latency_ms: float
    tokens_used: int | None = None
    trace: list[RouteStage]
    fallback: bool
    cost: CostResult
    transport_fallback: bool = False
    # Rejection transparency: populated ONLY when an initial answer was
    # rejected (escalation) or retained for lack of a strong model.
    # All None on clean passes, so existing consumers see no change there.
    # `verdict` always belongs to the FINAL answer; `initial_verdict`
    # preserves the discarded one. `answer` is always the final answer.
    initial_model: str | None = None
    initial_verdict: QualityVerdict | None = None
    escalation_reason: str | None = None  # "quality_gate_failed" | "no_strong_available"
    # Phase 10: verified Clerk user id. Observable only — MongoDB (Phase 11)
    # owns persistence. Always set on endpoint success (the auth dependency
    # guarantees it); None only on programmatically built responses.
    user_id: str | None = None
