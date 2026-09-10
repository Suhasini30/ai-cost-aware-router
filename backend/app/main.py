from fastapi import FastAPI, HTTPException, Query

from app.models.registry import get_model, list_models

app = FastAPI(title="Cost-Aware Multi-Model Router API")

        
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


