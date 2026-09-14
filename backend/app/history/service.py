"""History persistence (Phase 2).

Maps AskResponse -> QueryLogDocument and inserts best-effort: a dead
database must never fail the user's answer, so every failure is logged
and swallowed here (the endpoint already responded or will respond
regardless — see the BackgroundTasks bridge in app/router/router.py).
"""

import logging
import uuid

from app.core.config import Settings, settings
from app.db.mongo import get_query_logs
from app.db.schemas import ExecutionStep, PrivacySettings, QueryLogDocument
from app.eval.schemas import AskResponse

log = logging.getLogger("app.history")


def to_query_log(
    prompt: str,
    response: AskResponse,
    user_id: str,
    app_settings: Settings | None = None,
) -> QueryLogDocument:
    """Translate a pipeline response into a storable document."""
    cfg = app_settings or settings
    breakdown = response.cost.actual_breakdown
    in_tok = sum(b.input_tokens for b in breakdown)
    out_tok = sum(b.output_tokens for b in breakdown)
    steps = [
        ExecutionStep(
            stage=s.stage,
            decision=s.rule,
            details={"kept": list(s.kept)},
        )
        for s in response.trace
    ]
    initial = breakdown[0].model_id if breakdown else response.selected_model.id

    # --- Extract escalation fields from trace (analytics) ---
    esc_reason: str | None = None
    esc_category: str | None = None
    for stage in response.trace or []:
        if not isinstance(stage, dict) or stage.get("stage") != "escalation":
            continue
        rule = str(stage.get("rule", ""))
        if "failed quality" in rule:
            esc_reason = "quality gate failed"
            esc_category = "quality"
        elif "no enabled strong" in rule:
            esc_reason = "no strong model available"
            esc_category = "capacity"
        else:
            esc_reason = rule or "escalated"
            esc_category = "other"
        break  # first escalation stage wins

    # Provider: extract from the first model id in breakdown or selected_model
    # Model IDs often carry a prefix like "mistral-fast", "gpt-4o", "groq-llama-70b"
    provider: str | None = None
    if breakdown and breakdown[0].model_id:
        provider = breakdown[0].model_id.split("-")[0] if "-" in breakdown[0].model_id else breakdown[0].model_id
    elif response.selected_model.id:
        provider = response.selected_model.id.split("-")[0] if "-" in response.selected_model.id else response.selected_model.id

    doc = QueryLogDocument(
        request_id=uuid.uuid4().hex,
        user_id=user_id,
        prompt=prompt,
        answer=response.answer,
        execution_trace=steps,
        complexity_category=response.decision.complexity,
        confidence_score=response.decision.confidence,
        initial_model=initial,
        final_model=response.selected_model.id,
        provider=provider,
        escalated=response.escalated,
        passed=response.verdict.passed,
        quality_score=response.verdict.quality_score,
        skipped_judge=response.verdict.skipped_judge,
        routing_api_calls=response.routing_api_calls,
        model_api_calls=response.model_api_calls,
        total_llm_api_calls=response.total_llm_api_calls,
        baseline_model=response.baseline_model,
        input_tokens=in_tok,
        output_tokens=out_tok,
        total_tokens=response.tokens_used or (in_tok + out_tok),
        latency_ms=response.latency_ms,
        baseline_cost=response.cost.baseline_cost,
        actual_cost=response.cost.actual_cost,
        cost_saved=response.cost.savings,  # canonical: pipeline-computed
        escalation_reason=esc_reason,
        escalation_category=esc_category,
        privacy=PrivacySettings(
            store_prompts=cfg.privacy_store_prompts,
            store_answers=cfg.privacy_store_answers,
            store_execution_trace=True,
            anonymize_user=False,
        ),
    )
    doc.apply_privacy_filters()
    return doc


async def persist_ask_response(
    prompt: str,
    response: AskResponse,
    user_id: str,
    collection=None,
) -> str | None:
    """Insert one history document; returns request_id or None on failure.

    Never raises: persistence is best-effort by design.
    """
    try:
        doc = to_query_log(prompt, response, user_id)
        col = collection if collection is not None else get_query_logs()
        payload = doc.model_dump(by_alias=True, exclude_none=True)
        payload.pop("_id", None)  # let Mongo assign the ObjectId
        await col.insert_one(payload)
        return doc.request_id
    except Exception as exc:
        log.warning("history persist skipped: %s", type(exc).__name__)
        return None
