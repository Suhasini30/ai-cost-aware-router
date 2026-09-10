"""Token-based cost calculator (Phase 8). Pure functions, no I/O.

BASELINE SEMANTICS — strong-model final-answer baseline:
`baseline_cost` reprices the FINAL answer leg's token counts at the
strongest capable model's rates. It is NOT a literal counterfactual
re-execution of the whole request (first-leg tokens are excluded from
the baseline by definition). Documented here so Phase 9 benchmark
code cannot mistake it for a full-rerun cost.

ACTUAL SCOPE — answer-generation legs only (initial + escalation).
Classifier/judge overhead is excluded by accounting policy. Only
successful ExecutionResults carry token usage, so failed retries can
never inflate cost: no token counts are ever invented.
"""

from app.cost.schemas import CostBreakdown, CostResult
from app.models.registry import ModelSpec, REGISTRY


def resolve_model(model_ref: str) -> ModelSpec | None:
    """Find a registry model by id, then by provider api_id."""
    if model_ref in REGISTRY:
        return REGISTRY[model_ref]
    for spec in REGISTRY.values():
        if spec.api_id == model_ref:
            return spec
    return None


def price_leg(
    model_ref: str, input_tokens: int | None, output_tokens: int | None
) -> CostBreakdown:
    """Price one execution leg. Unknown models cost zero (flagged by id)."""
    spec = resolve_model(model_ref)
    in_tok = input_tokens or 0
    out_tok = output_tokens or 0
    if spec is None:
        return CostBreakdown(
            model_id=f"unpriced:{model_ref}",
            input_tokens=in_tok,
            output_tokens=out_tok,
            input_cost=0.0,
            output_cost=0.0,
            total_cost=0.0,
        )
    in_cost = in_tok / 1000 * spec.input_cost_per_1k
    out_cost = out_tok / 1000 * spec.output_cost_per_1k
    return CostBreakdown(
        model_id=spec.id,
        input_tokens=in_tok,
        output_tokens=out_tok,
        input_cost=in_cost,
        output_cost=out_cost,
        total_cost=in_cost + out_cost,
    )


def build_cost(
    legs: list[tuple[str, int | None, int | None]],
    baseline_model: ModelSpec,
    baseline_input_tokens: int | None,
    baseline_output_tokens: int | None,
) -> CostResult:
    """Assemble actual vs baseline cost.

    `legs` are (model_ref, input_tokens, output_tokens) for each
    successful answer leg. The baseline reprices the final-leg token
    counts at `baseline_model` rates (strong-model final-answer
    baseline — see module docstring).
    """
    breakdown = [price_leg(ref, i, o) for ref, i, o in legs]
    actual = sum(b.total_cost for b in breakdown)
    base_leg = price_leg(
        baseline_model.id, baseline_input_tokens, baseline_output_tokens
    )
    baseline = base_leg.total_cost
    savings = max(0.0, baseline - actual)
    percent = (savings / baseline * 100.0) if baseline > 0 else 0.0
    return CostResult(
        actual_cost=actual,
        baseline_cost=baseline,
        savings=savings,
        savings_percent=percent,
        actual_breakdown=breakdown,
        baseline_model_id=baseline_model.id,
    )
