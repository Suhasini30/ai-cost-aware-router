from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.logging import RequestLoggingMiddleware, setup_logging
from app.core.tracing import setup_tracing
from app.models.registry import get_model, list_models
from app.router.router import router as router_router

setup_logging(settings.log_level)
setup_tracing(settings)

app = FastAPI(title="Cost-Aware Multi-Model Router API")
# Browser dashboard support: allow the Next.js dev origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Access log last = outermost, so every request is recorded.
app.add_middleware(RequestLoggingMiddleware)
app.include_router(auth_router)
app.include_router(router_router)

        
@app.get("/")
async def root():
    return {
        "message": "Cost-Aware Multi-Model Router API",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


@app.get("/models")
async def get_models(provider: str | None = Query(default=None)):
    try:
        models = list_models(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"models": [m.model_dump() for m in models], "count": len(models)}


@app.get("/models/{model_id}")
async def get_model_by_id(model_id: str):
    try:
        return get_model(model_id).model_dump()
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id!r}")


