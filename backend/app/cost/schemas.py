"""Cost accounting schemas (Phase 8).

Token math only — latency never enters monetary cost. Missing token
counts (None) are priced as zero; token counts are never invented.
"""

from pydantic import BaseModel, Field


class CostBreakdown(BaseModel):
    model_id: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    input_cost: float = Field(ge=0.0)
    output_cost: float = Field(ge=0.0)
    total_cost: float = Field(ge=0.0)


class CostResult(BaseModel):
    actual_cost: float = Field(ge=0.0)
    baseline_cost: float = Field(ge=0.0)
    savings: float = Field(ge=0.0)
    savings_percent: float = Field(ge=0.0)
    actual_breakdown: list[CostBreakdown]
    baseline_model_id: str
