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
    quality_score: float = Field(ge=0.0, le=1.0)
    reason: str


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
    # Phase 10: verified Clerk user id. Observable only — MongoDB (Phase 11)
    # owns persistence. Always set on endpoint success (the auth dependency
    # guarantees it); None only on programmatically built responses.
    user_id: str | None = None
