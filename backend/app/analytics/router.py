"""Analytics API (read-only aggregates over MongoDB query_logs)."""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.service import build_report
from app.auth.dependencies import get_current_user_id

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
async def get_analytics(
    range: str = Query(default="7d"),
    # Authenticated like every protected endpoint; aggregates are
    # project-global (traces carry no per-user attribution).
    user_id: str = Depends(get_current_user_id),
) -> dict:
    try:
        report = await build_report(range, user_id=user_id)
        return report
    except Exception as exc:
        # If MongoDB is genuinely down, return a controlled 503.
        # Log the real exception server-side; do not expose details to client.
        import logging

        log = logging.getLogger("app.analytics")
        log.exception("Analytics report generation failed")
        raise HTTPException(status_code=503, detail="Analytics store unavailable") from exc