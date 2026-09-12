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
    routing_api_calls: int = 0
    model_api_calls: int = 1
    total_llm_api_calls: int = 1
    baseline_model: str | None = None
    # Failover reporting: the registry model that REALLY answered (may
    # differ from selected_model after transport failover). Falls back
    # to selected_model when the api_id is unresolvable. Added so a
    # response can never claim a model that did not serve it.
    actual_model: ModelSpec | None = None
    # Transport attempts across answer executions (initial + escalation
    # legs summed). Classifier calls are tracked separately in
    # routing_api_calls; judge invocations in judge_calls.
    calls: int = 1
    # evaluate_answer() invocations for this request (0, 1, or 2).
    judge_calls: int = 0
    # Phase 10: verified Clerk user id. Observable only — MongoDB (Phase 11)
    # owns persistence. Always set on endpoint success (the auth dependency
    # guarantees it); None only on programmatically built responses.
    user_id: str | None = None

