"""Analytics over MongoDB query_logs collection (read-only aggregates).

Source of truth: per-request QueryLogDocument records, one document per
completed request. All fields needed by the frontend are already written
by the history persistence path (see history/service.to_query_log).

Cost semantics are inherited verbatim from Phase 8: per-request
actual/baseline/savings as recorded in the document, summed without
recomputation.
"""
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import logging

from motor.motor_asyncio import AsyncIOMotorCollection

# Backward-compatibility: old tests monkeypatch svc.Client
# (LangSmith SDK instantiation). Keep a sentinel so those tests can
# setattr without AttributeError, even though the real client is no longer used.
Client = None  # type: ignore[assignment]  # noqa: F811

from app.core.config import Settings, settings
from app.db.mongo import get_query_logs

log = logging.getLogger("app.analytics")

# ---------------------------------------------------------------------------
# Range -> days mapping
# ---------------------------------------------------------------------------
RANGE_DAYS = {"7d": 7, "30d": 30, "all": None}


# ---------------------------------------------------------------------------
# Build MongoDB date filter for a range key
# ---------------------------------------------------------------------------
def _range_filter(range_key: str) -> dict | None:
    """Return a MongoDB {gte: datetime} filter for the given range, or None for 'all'."""
    days = RANGE_DAYS.get(range_key)
    if days is None or days == 0:
        return None  # "all" → no filter
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return {"created_at": {"$gte": since}}


# ---------------------------------------------------------------------------
# Aggregate one report from MongoDB (called from the FastAPI route via await)
# ---------------------------------------------------------------------------
async def aggregate_report(range_key: str, collection: AsyncIOMotorCollection | None = None, user_id: str | None = None) -> dict:
    """Run MongoDB aggregation pipelines and return the analytics report dict."""
    col = collection if collection is not None else get_query_logs()
    fmt = lambda v: v

    # Build the date filter
    date_filter = _range_filter(range_key)

    # --- $match stage ---
    match_conds: dict = date_filter or {}
    if user_id:
        match_conds["user_id"] = user_id
    match_stage: dict = {"$match": match_conds}

    # --- $project stage: pick / rename fields we need ---
    project_stage: dict = {
        "$project": {
            "model": "$final_model",
            "actual_cost": "$actual_cost",
            "baseline_cost": "$baseline_cost",
            "escalated": "$escalated",
            "escalation_reason": "$escalation_reason",
            "escalation_category": "$escalation_category",
            "latency_ms": "$latency_ms",
            "created_day": {
                "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
            },
        }
    }

    # --- 1. Overall stats pipeline ---
    pipeline_overall = [
        match_stage,
        project_stage,
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "actual_spend": {"$sum": "$actual_cost"},
                "always_strong_baseline_spend": {"$sum": "$baseline_cost"},
                "savings": {"$sum": {"$subtract": ["$baseline_cost", "$actual_cost"]}},
                "escalated_count": {
                    "$sum": {"$cond": [{"$eq": ["$escalated", True]}, 1, 0]}
                },
                "total_latency": {"$sum": "$latency_ms"},
                "quality_scores": {"$push": "$quality_score"},  # keep for later avg
            }
        },
    ]

    # --- 2. Requests by model pipeline ---
    # Note: `final_model` is a plain string field — do NOT $unwind it.
    pipeline_by_model = [
        match_stage,
        {
            "$group": {
                "_id": "$final_model",
                "count": {"$sum": 1},
                "model_cost": {"$sum": "$actual_cost"},
            }
        },
        {"$sort": {"count": -1}},
    ]

    # --- 3. Spend over time (by day) pipeline ---
    # project_stage must come first so that $created_day is available to $group.
    pipeline_spend_day = [
        match_stage,
        project_stage,
        {
            "$group": {
                "_id": "$created_day",
                "actual": {"$sum": "$actual_cost"},
                "baseline": {"$sum": "$baseline_cost"},
            }
        },
        {"$project": {"date": "$_id", "actual_cost": "$actual", "baseline_cost": "$baseline", "_id": 0}},
        {"$sort": {"date": 1}},
    ]

    # --- 4. Escalations by reason+category pipeline ---
    pipeline_escalations = [
        match_stage,
        {"$match": {"escalated": True}},
        {
            "$group": {
                "_id": {"reason": "$escalation_reason", "category": "$escalation_category", "model": "$final_model"},
                "count": {"$sum": 1},
            }
        },
        {
            "$project": {
                "reason": "$_id.reason",
                "category": "$_id.category",
                "model": "$_id.model",
                "count": 1,
                "_id": 0,
            }
        },
        {"$sort": {"count": -1}},
    ]

    # --- 5. Average latency by model pipeline ---
    # Note: `final_model` is a plain string field — do NOT $unwind it.
    pipeline_latency_by_model = [
        match_stage,
        {
            "$group": {
                "_id": "$final_model",
                "avg_latency": {"$avg": "$latency_ms"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    # Execute all pipelines
    overall_raw = await col.aggregate(pipeline_overall).to_list(length=1)
    by_model_raw = await col.aggregate(pipeline_by_model).to_list(length=None)
    spend_day_raw = await col.aggregate(pipeline_spend_day).to_list(length=None)
    escalations_raw = await col.aggregate(pipeline_escalations).to_list(length=None)
    latency_raw = await col.aggregate(pipeline_latency_by_model).to_list(length=None)

    # --- Post-process overall ----
    if overall_raw:
        o = overall_raw[0]
        n = o.get("total_requests", 0)
        actual = o.get("actual_spend", 0) or 0.0
        baseline = o.get("always_strong_baseline_spend", 0) or 0.0
        savings_val = o.get("savings", 0) or 0.0
        pct_savings = (savings_val / baseline * 100.0) if baseline > 0 else 0.0

        esc_total = o.get("escalated_count", 0) or 0
        esc_rate = (esc_total / n) if n else 0.0

        # average quality from pushed scores
        scores = o.get("quality_scores", []) or []
        valid_scores = [float(s) for s in scores if s is not None and not (isinstance(s, float) and __import__('math').isnan(s))]
        avg_quality = (sum(valid_scores) / len(valid_scores)) if valid_scores else None
    else:
        n = 0
        actual = 0.0
        baseline = 0.0
        savings_val = 0.0
        pct_savings = 0.0
        esc_rate = 0.0
        avg_quality = None

    # --- Post-process by-model ----
    requests_by_model = [
        {"model": m["_id"], "count": m["count"], "cost": m["model_cost"]}
        for m in by_model_raw
    ]

    # --- Post-process spend-over-time ----
    spend_over_time = [
        {"date": d["date"], "actual_cost": d["actual_cost"], "baseline_cost": d["baseline_cost"]}
        for d in spend_day_raw
    ]

    # --- Post-process escalations ---

    escalations_by_reason = [
        {
            "reason": e.get("reason") or "escalated",
            "category": e.get("category") or "other",
            "model": e.get("model") or "unknown",
            "count": e["count"],
        }
        for e in escalations_raw
    ]

    # --- Post-process avg latency by model ----
    avg_latency_by_model = [
        {"model": l["_id"], "latency_ms": round(l.get("avg_latency", 0) or 0)}
        for l in latency_raw
    ]

    return {
        "total_requests": n,
        "actual_spend": round(actual, 6),
        "always_strong_baseline_spend": round(baseline, 6),
        "savings": round(savings_val, 6),
        "savings_pct": round(pct_savings, 1),        # legacy alias
        "savings_percent": round(pct_savings, 1),    # frontend expects this name
        "escalation_rate": round(esc_rate, 3),
        "average_quality": avg_quality,
        "requests_by_model": requests_by_model,
        "spend_over_time": spend_over_time,
        "escalations_by_reason": escalations_by_reason,
        "avg_latency_by_model": avg_latency_by_model,
        "range": range_key,
    }


# ---------------------------------------------------------------------------
# Legacy `summarize` kept for test compatibility (records-shaped, not Mongo)
# ---------------------------------------------------------------------------

def summarize(records: list[dict]) -> dict:
    """Legacy aggregation over raw record dicts (used by existing tests).

    This is the old LangSmith-shaped version; it does NOT read from MongoDB.
    New code should use `aggregate_report()` / `build_report()` which query
    MongoDB directly.
    """
    n = len(records)
    actual = sum(r["actual"] for r in records)
    baseline = sum(r["baseline"] for r in records)
    savings = sum(r["savings"] for r in records)
    qualities = [r["quality"] for r in records if r["quality"] is not None]
    latencies = [r["latency"] for r in records]

    by_model: dict[str, dict] = defaultdict(
        lambda: {"model": "", "count": 0, "cost": 0.0}
    )
    for r in records:
        entry = by_model[r["model"]]
        entry["model"] = r["model"]
        entry["count"] += 1
        entry["cost"] += r["actual"]

    by_day: dict[str, dict] = defaultdict(
        lambda: {"date": "", "actual_cost": 0.0, "baseline_cost": 0.0}
    )
    for r in records:
        entry = by_day[r["date"]]
        entry["date"] = r["date"]
        entry["actual_cost"] += r["actual"]
        entry["baseline_cost"] += r["baseline"]

    reasons: dict[tuple[str, str], int] = defaultdict(int)
    for r in records:
        if r["escalation"] is not None:
            reasons[r["escalation"]] += 1

    lat_by_model: dict[str, list[float]] = defaultdict(list)
    for r in records:
        lat_by_model[r["model"]].append(r["latency"])

    return {
        "total_requests": n,
        "actual_spend": actual,
        "always_strong_baseline_spend": baseline,
        "savings": savings,
        "savings_pct": (savings / baseline * 100.0) if baseline > 0 else 0.0,
        "escalation_rate": (
            sum(1 for r in records if r["escalated"]) / n if n else 0.0),
        "average_quality": (sum(qualities) / len(qualities)
                            if qualities else None),
        "requests_by_model": sorted(by_model.values(),
                                    key=lambda e: -e["count"]),
        "spend_over_time": sorted(by_day.values(),
                                  key=lambda e: e["date"]),
        "escalations_by_reason": [
            {"reason": reason, "category": cat, "count": count}
            for (reason, cat), count in sorted(reasons.items())
        ],
        "avg_latency_by_model": sorted(
            ({"model": m, "latency_ms": sum(v) / len(v)}
             for m, v in lat_by_model.items()),
            key=lambda e: e["model"],
        ),
    }


# ---------------------------------------------------------------------------
# Public API: async function the FastAPI route can await
# ---------------------------------------------------------------------------

async def build_report(range_key: str, app_settings: Settings | None = None, user_id: str | None = None) -> dict:
    """Return a full analytics report for *range_key* from MongoDB.

    The FastAPI route calls: `await build_report(range)`.
    """
    cfg = app_settings or settings
    return await aggregate_report(range_key, user_id=user_id)