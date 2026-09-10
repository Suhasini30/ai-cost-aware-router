"""Router schemas — classification I/O only.

No routing policy here: this layer analyzes prompts without answering
them. Cost-aware model selection happens in Phase 4, which consumes
`RouterDecision.confidence` against `settings.confidence_threshold`.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.models.registry import ModelSpec

TaskType = Literal["summarization", "coding", "math", "general_qa", "image"]
Complexity = Literal["low", "high"]
Capability = Literal["text", "coding", "reasoning", "image"]
QualityRequired = Literal["standard", "high"]


class RouterDecision(BaseModel):
    task_type: TaskType
    complexity: Complexity
    capability: Capability
    quality_required: QualityRequired
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class ClassifyRequest(BaseModel):
    prompt: str


class ClassifyResponse(BaseModel):
    decision: RouterDecision
    model_used: str
    latency_ms: float
    tokens_used: int | None = None


class RouteStage(BaseModel):
    """One recorded pipeline step: rule applied + surviving model ids."""

    stage: str
    rule: str
    kept: list[str]


class RouteRequest(BaseModel):
    prompt: str


class RouteResponse(BaseModel):
    decision: RouterDecision
    selected_model: ModelSpec
    classifier_model_used: str
    latency_ms: float
    tokens_used: int | None = None
    trace: list[RouteStage]
    fallback: bool
