import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.auth.dependencies import get_current_user_id
from app.core.config import settings
from app.eval.schemas import AskRequest, AskResponse
from app.execution.base import ProviderUnavailableError
from app.history.service import persist_ask_response
from app.router.agent import classify_prompt
from app.router.pipeline import answer_prompt
from app.router.policy import route_decision
from app.router.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    RouteRequest,
    RouteResponse,
)

log = logging.getLogger("app.router")

router = APIRouter(prefix="/router", tags=["router"])


def _validate_prompt(prompt: str | None) -> str:
    """Shared prompt guard for router endpoints (422 on empty/oversize)."""
    text = (prompt or "").strip()
    if not text:
        raise HTTPException(status_code=422, detail="prompt must not be empty")
    if len(text) > settings.max_prompt_chars:
        raise HTTPException(
            status_code=422,
            detail=f"prompt exceeds {settings.max_prompt_chars} characters",
        )
    return text


@router.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest) -> ClassifyResponse:
    prompt = _validate_prompt(req.prompt)
    try:
        res = classify_prompt(prompt)
        if len(res) == 5:
            decision, model_used, latency_ms, tokens, routing_calls = res
        else:
            decision, model_used, latency_ms, tokens = res[:4]
            routing_calls = 0 if model_used in ("rules/local", "fallback") else 1
    except ProviderUnavailableError as exc:
        log.warning("classify 502: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak internals to the client
        log.exception("classify 500")
        raise HTTPException(status_code=500, detail="classification failed") from exc
    return ClassifyResponse(
        decision=decision,
        model_used=model_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
        routing_api_calls=routing_calls,
    )


@router.post("/route", response_model=RouteResponse)
def route(req: RouteRequest) -> RouteResponse:
    """Classify a prompt and select the cheapest capable model.

    NOTE: the prompt is transmitted to the configured external
    classifier provider, and the call is traced in LangSmith when
    LANGCHAIN_API_KEY is set. The offline fallback transmits nothing.
    """
    prompt = _validate_prompt(req.prompt)
    try:
        res = classify_prompt(prompt)
        if len(res) == 5:
            decision, model_used, latency_ms, tokens, routing_calls = res
        else:
            decision, model_used, latency_ms, tokens = res[:4]
            routing_calls = 0 if model_used in ("rules/local", "fallback") else 1
        selected, trace, fallback = route_decision(
            decision, threshold=settings.confidence_threshold
        )
    except ProviderUnavailableError as exc:
        log.warning("route 502: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak internals to the client
        log.exception("route 500")
        raise HTTPException(status_code=500, detail="routing failed") from exc
    return RouteResponse(
        decision=decision,
        selected_model=selected,
        classifier_model_used=model_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
        trace=trace,
        fallback=fallback,
        routing_api_calls=routing_calls,
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    user_id: str = Depends(get_current_user_id),
    background: BackgroundTasks = None,
) -> AskResponse:
    """Full pipeline: classify, route, execute, evaluate, escalate once.

    Requires a valid Clerk JWT (401 otherwise). The user_id is exposed
    on the response for downstream use. The response is also persisted
    to history best-effort AFTER sending (a dead database never fails
    the answer).

    NOTE: the prompt and the generated answer are transmitted to the
    configured external providers, and calls are traced in LangSmith
    when LANGCHAIN_API_KEY is set. Offline fallback paths transmit
    nothing but cannot produce a live answer.
    """
    prompt = _validate_prompt(req.prompt)
    try:
        response = answer_prompt(prompt)
    except ProviderUnavailableError as exc:
        log.warning("ask 502: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak internals to the client
        log.exception("ask 500")
        raise HTTPException(status_code=500, detail="ask pipeline failed") from exc
    response.user_id = user_id
    if background is not None:
        background.add_task(persist_ask_response, prompt, response, user_id)
    return response
