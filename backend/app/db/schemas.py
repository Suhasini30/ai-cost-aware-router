from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class PrivacySettings(BaseModel):
    store_prompts: bool = True
    store_answers: bool = True
    store_execution_trace: bool = True
    anonymize_user: bool = False


class ExecutionStep(BaseModel):
    stage: str
    decision: str | None = None
    model: str | None = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    status: str = "ok"
    details: dict[str, Any] = Field(default_factory=dict)


class QueryLogDocument(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    request_id: str = Field(description="Unique request UUID")
    session_id: str | None = Field(default=None, description="Optional session/conversation ID")
    user_id: str = Field(description="Authenticated user identifier")

    # Content fields (governed by privacy settings)
    prompt: str | None = Field(default=None)
    answer: str | None = Field(default=None)
    execution_trace: list[ExecutionStep] | None = Field(default=None)

    # Classification & Routing details
    complexity_category: str = Field(default="unknown")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    initial_model: str
    final_model: str
    escalated: bool = False
    passed: bool = True
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    skipped_judge: bool = False
    routing_api_calls: int = 0
    model_api_calls: int = 1
    total_llm_api_calls: int = 1
    baseline_model: str | None = None

    # Token usage
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)

    # Financial Cost Metrics
    baseline_cost: float = Field(default=0.0, ge=0.0, description="Cost if strongest baseline model was used")
    actual_cost: float = Field(default=0.0, ge=0.0, description="Actual model execution cost")
    cost_saved: float = Field(default=0.0, description="Calculated as baseline_cost - actual_cost")

    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    user_feedback: dict[str, Any] | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def calculate_cost_saved(self) -> float:
        """Enforce cost_saved = baseline_cost - actual_cost."""
        self.cost_saved = round(max(0.0, self.baseline_cost - self.actual_cost), 6)
        return self.cost_saved

    def apply_privacy_filters(self):
        """Redact / filter fields based on privacy configuration."""
        if not self.privacy.store_prompts:
            self.prompt = "[REDACTED_PROMPT]"
        if not self.privacy.store_answers:
            self.answer = "[REDACTED_ANSWER]"
        if not self.privacy.store_execution_trace:
            self.execution_trace = None
        if self.privacy.anonymize_user and self.user_id:
            import hashlib
            self.user_id = "anon_" + hashlib.sha256(self.user_id.encode()).hexdigest()[:12]
