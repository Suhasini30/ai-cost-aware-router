"""History API (Phase 2). All async (Motor); every operation is hard-scoped
to the authenticated caller — users can only ever see their own rows."""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo.errors import PyMongoError

from app.auth.dependencies import get_current_user_id
from app.db.mongo import get_query_logs

router = APIRouter(prefix="/history", tags=["history"])

_SORTS = {
    "created_at": [("created_at", 1)],
    "-created_at": [("created_at", -1)],
}


class FeedbackIn(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


def _collection():
    try:
        return get_query_logs()
    except RuntimeError as exc:
        raise HTTPException(status_code=503,
                            detail="History store unavailable") from exc


def _or_503(fn):
    """Map any PyMongo failure to 503 (store down, never a 500)."""
    import functools

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except HTTPException:
            raise
        except PyMongoError as exc:
            raise HTTPException(status_code=503,
                                detail="History store unavailable") from exc
    return wrapper


def _jsonable(doc: dict) -> dict:
    out = dict(doc)
    if isinstance(out.get("_id"), ObjectId):
        out["id"] = str(out.pop("_id"))
    created = out.get("created_at")
    if isinstance(created, datetime):
        out["created_at"] = created.isoformat()
    return out


@router.get("")
@_or_503
async def list_history(
    user_id: str = Depends(get_current_user_id),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    model: str | None = None,
    passed: bool | None = None,
    escalated: bool | None = None,
    sort_by: str = Query(default="-created_at"),
) -> dict:
    col = _collection()
    filt: dict = {"user_id": user_id}
    if search:
        import re
        filt["prompt"] = {"$regex": re.escape(search), "$options": "i"}
    if model:
        filt["final_model"] = model
    if passed is not None:
        filt["passed"] = passed
    if escalated is not None:
        filt["escalated"] = escalated
    sort = _SORTS.get(sort_by)
    if sort is None:
        raise HTTPException(status_code=422, detail="Invalid sort_by")
    total = await col.count_documents(filt)
    cursor = col.find(filt).sort(sort).skip((page - 1) * limit).limit(limit)
    items = [_jsonable(d) async for d in cursor]
    pages = (total + limit - 1) // limit if total else 0
    return {"items": items, "total": total, "page": page, "pages": pages}


@router.get("/{request_id}")
@_or_503
async def get_entry(request_id: str,
                    user_id: str = Depends(get_current_user_id)) -> dict:
    doc = await _collection().find_one(
        {"request_id": request_id, "user_id": user_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Not found")
    return _jsonable(doc)


@router.delete("/{request_id}", status_code=204)
@_or_503
async def delete_entry(request_id: str,
                       user_id: str = Depends(get_current_user_id)) -> None:
    res = await _collection().delete_one(
        {"request_id": request_id, "user_id": user_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None


@router.post("/{request_id}/feedback")
@_or_503
async def submit_feedback(request_id: str, body: FeedbackIn,
                          user_id: str = Depends(get_current_user_id)) -> dict:
    res = await _collection().update_one(
        {"request_id": request_id, "user_id": user_id},
        {"$set": {"user_feedback": body.model_dump(exclude_none=True)}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await _collection().find_one(
        {"request_id": request_id, "user_id": user_id})
    return _jsonable(doc)
