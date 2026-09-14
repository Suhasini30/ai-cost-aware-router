"""Benchmark metrics (Phase 9). Pure functions over per-case records.

A case record is a plain dict (see runner.collect_case); metrics never
touch providers, the registry, or the pipeline.
"""

from statistics import mean


def _percentile(xs: list[float], pct: float) -> float:
    """Linear-interpolation percentile (no numpy dependency)."""
    if not xs:
        return 0.0
    ordered = sorted(xs)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    low, high = int(rank), min(int(rank) + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] * (1 - frac) + ordered[high] * frac


def routing_accuracy(cases: list[dict]) -> dict:
    """Fraction of router predictions matching dataset ground truth.

    Only cases with a prediction (strategy 'router') count; fixed-model
    strategies record None and are excluded.
    """
    judged = [c for c in cases if c.get("pred_task_type") is not None]
    if not judged:
        return {"overall": None, "task_type": None,
                "capability": None, "complexity": None, "n": 0}
    fields = (
        ("task_type", "pred_task_type", "expected_task_type"),
        ("capability", "pred_capability", "expected_capability"),
        ("complexity", "pred_complexity", "expected_complexity"),
    )
    per_field = {
        name: sum(1 for c in judged if c[p] == c[e]) / len(judged)
        for name, p, e in fields
    }
    overall = sum(
        1 for c in judged
        if all(c[p] == c[e] for _, p, e in fields)
    ) / len(judged)
    return {"overall": overall, **per_field, "n": len(judged)}


def summarize_strategy(cases: list[dict]) -> dict:
    """Aggregate one strategy's cases (quality, rates, latency, cost)."""
    n = len(cases)
    if n == 0:
        return {"n": 0}
    qualities = [c["quality_score"] for c in cases]
    latencies = [c["latency_ms"] for c in cases]
    actual = sum(c["actual_cost"] for c in cases)
    baseline = sum(c["baseline_cost"] for c in cases)
    savings = sum(c["savings"] for c in cases)
    return {
        "n": n,
        "routing_accuracy": routing_accuracy(cases),
        "average_quality": mean(qualities),
        "pass_rate": sum(1 for c in cases if c["passed"]) / n,
        "escalation_rate": sum(1 for c in cases if c["escalated"]) / n,
        "fallback_rate": sum(1 for c in cases if c["transport_fallback"]) / n,
        "latency_ms": {
            "avg": mean(latencies),
            "p50": _percentile(latencies, 50),
            "p95": _percentile(latencies, 95),
        },
        "actual_cost": actual,
        "baseline_cost": baseline,
        "savings": savings,
        "savings_percent": (savings / baseline * 100.0) if baseline > 0 else 0.0,
    }


def compare(strategies: dict[str, list[dict]]) -> dict:
    """Build the multi-strategy comparison report."""
    return {
        strategy: summarize_strategy(cases)
        for strategy, cases in strategies.items()
    }
