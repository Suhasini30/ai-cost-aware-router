from fastapi import APIRouter, Depends, HTTPException

from app.auth.dependencies import get_current_user_id
from app.core.config import settings
from app.eval.schemas import AskRequest, AskResponse
from app.execution.base import ProviderUnavailableError
from app.router.agent import classify_prompt
from app.router.pipeline import answer_prompt
from app.router.policy import route_decision
from app.router.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    RouteRequest,
    RouteResponse,
)

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
        decision, model_used, latency_ms, tokens = classify_prompt(prompt)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak internals to the client
        raise HTTPException(status_code=500, detail="classification failed") from exc
    return ClassifyResponse(
        decision=decision,
        model_used=model_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
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
        decision, model_used, latency_ms, tokens = classify_prompt(prompt)
        selected, trace, fallback = route_decision(
            decision, threshold=settings.confidence_threshold
        )
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak internals to the client
        raise HTTPException(status_code=500, detail="routing failed") from exc
    return RouteResponse(
        decision=decision,
        selected_model=selected,
        classifier_model_used=model_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
        trace=trace,
        fallback=fallback,
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    user_id: str = Depends(get_current_user_id),
) -> AskResponse:
    """Full pipeline: classify, route, execute, evaluate, escalate once.

    Requires a valid Clerk JWT (401 otherwise). The user_id is exposed
    on the response for downstream use; nothing is persisted here.

    NOTE: the prompt and the generated answer are transmitted to the
    configured external providers, and calls are traced in LangSmith
    when LANGCHAIN_API_KEY is set. Offline fallback paths transmit
    nothing but cannot produce a live answer.
    """
    prompt = _validate_prompt(req.prompt)
    try:
        return answer_prompt(prompt)
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # never leak internals to the client
        raise HTTPException(status_code=500, detail="ask pipeline failed") from exc
    response.user_id = user_id
    return response
