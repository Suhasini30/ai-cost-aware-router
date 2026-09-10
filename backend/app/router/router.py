from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.router.agent import classify_prompt
from app.router.schemas import ClassifyRequest, ClassifyResponse

router = APIRouter(prefix="/router", tags=["router"])


@router.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest) -> ClassifyResponse:
    prompt = (req.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt must not be empty")
    if len(prompt) > settings.max_prompt_chars:
        raise HTTPException(
            status_code=422,
            detail=f"prompt exceeds {settings.max_prompt_chars} characters",
        )
    try:
        decision, model_used, latency_ms, tokens = classify_prompt(prompt)
    except Exception as exc:  # never leak internals to the client
        raise HTTPException(status_code=500, detail="classification failed") from exc
    return ClassifyResponse(
        decision=decision,
        model_used=model_used,
        latency_ms=latency_ms,
        tokens_used=tokens,
    )
