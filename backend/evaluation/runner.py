"""Benchmark runner (Phase 9).

Live provider calls — every run spends real tokens. Guarded by an
estimate print plus a required --yes flag; --limit and --strategies
allow cheap partial runs. Zero new backend logic: strategies reuse
answer_prompt / execute / evaluate_answer / build_cost directly.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:  # allow `python evaluation/runner.py`
    sys.path.insert(0, str(BACKEND_DIR))

from app.cost.calculator import build_cost  # noqa: E402
from app.eval.evaluator import evaluate_answer  # noqa: E402
from evaluation.metrics import compare  # noqa: E402
from app.execution.service import execute  # noqa: E402
from app.models.registry import get_cheapest_model, get_strong_model  # noqa: E402
from app.router.pipeline import answer_prompt  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_DATASET = HERE / "dataset.json"
DEFAULT_OUTDIR = HERE / "results"

# Worst-case provider calls per case per strategy (escalation + re-judge).
CALL_ESTIMATE = {"router": 5, "strong": 2, "fast": 2}


def load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data["cases"]
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    for c in cases:
        for key in ("prompt", "expected_task_type", "expected_capability",
                    "expected_complexity"):
            assert key in c, f"{c.get('id')}: missing {key}"
    return cases


def run_router(case: dict) -> dict:
    resp = answer_prompt(case["prompt"])
    return {
        "pred_task_type": resp.decision.task_type,
        "pred_capability": resp.decision.capability,
        "pred_complexity": resp.decision.complexity,
        "model_id": resp.selected_model.id,
        "quality_score": resp.verdict.quality_score,
        "passed": resp.verdict.passed,
        "escalated": resp.escalated,
        "transport_fallback": resp.transport_fallback,
        "latency_ms": resp.latency_ms,
        "actual_cost": resp.cost.actual_cost,
        "baseline_cost": resp.cost.baseline_cost,
        "savings": resp.cost.savings,
    }


def run_fixed(case: dict, model) -> dict:
    started = time.perf_counter()
    result = execute(provider=model.provider.value, model_api_id=model.api_id,
                     prompt=case["prompt"])
    verdict = evaluate_answer(case["prompt"], result.text)
    cost = build_cost(
        [(model.id, result.input_tokens, result.output_tokens)],
        get_strong_model(),
        result.input_tokens,
        result.output_tokens,
    )
    return {
        "pred_task_type": None,
        "pred_capability": None,
        "pred_complexity": None,
        "model_id": model.id,
        "quality_score": verdict.quality_score,
        "passed": verdict.passed,
        "escalated": False,
        "transport_fallback": result.fallback_used,
        "latency_ms": (time.perf_counter() - started) * 1000.0,
        "actual_cost": cost.actual_cost,
        "baseline_cost": cost.baseline_cost,
        "savings": cost.savings,
    }


def run_strategy(strategy: str, cases: list[dict]) -> list[dict]:
    fixed = {"strong": get_strong_model(), "fast": get_cheapest_model()}
    out = []
    for i, case in enumerate(cases):
        print(f"  [{strategy}] {i + 1}/{len(cases)} {case['id']}...",
              flush=True)
        if strategy == "router":
            rec = run_router(case)
        else:
            rec = run_fixed(case, fixed[strategy])
        rec.update(
            case_id=case["id"],
            strategy=strategy,
            expected_task_type=case["expected_task_type"],
            expected_capability=case["expected_capability"],
            expected_complexity=case["expected_complexity"],
        )
        out.append(rec)
    return out


def print_table(report: dict) -> None:
    print(f"\n{'strategy':<10}{'n':>4}{'qual':>7}{'esc%':>7}"
          f"{'fb%':>6}{'p50ms':>9}{'actual$':>10}{'base$':>9}{'save%':>7}")
    for name, s in report.items():
        if s.get("n", 0) == 0:
            continue
        print(f"{name:<10}{s['n']:>4}{s['average_quality']:>7.3f}"
              f"{s['escalation_rate'] * 100:>7.1f}"
              f"{s['fallback_rate'] * 100:>6.1f}"
              f"{s['latency_ms']['p50']:>9.0f}"
              f"{s['actual_cost']:>10.6f}{s['baseline_cost']:>9.6f}"
              f"{s['savings_percent']:>7.1f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 9 benchmark runner")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--strategies", default="router,strong,fast",
                        help="comma subset of router,strong,fast")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--yes", action="store_true",
                        help="confirm live provider spend")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR))
    args = parser.parse_args(argv)

    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    assert all(s in CALL_ESTIMATE for s in strategies), "bad strategy name"
    cases = load_dataset(Path(args.dataset))
    if args.limit is not None:
        cases = cases[: args.limit]

    estimate = sum(CALL_ESTIMATE[s] for s in strategies) * len(cases)
    print(f"cases={len(cases)} strategies={strategies} "
          f"estimated max provider calls={estimate}")
    if not args.yes:
        print("Live run: re-run with --yes to confirm the spend.")
        return 2

    results = {s: run_strategy(s, cases) for s in strategies}
    report = compare(results)
    report["_meta"] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategies": strategies,
        "cases": len(cases),
        "estimated_max_calls": estimate,
    }
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = outdir / f"report-{stamp}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_table(report)
    print(f"\nreport: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
