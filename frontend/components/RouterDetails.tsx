import type { AskResponse } from "@/lib/api";
import { fmtMoney, fmtPct, titleCase } from "@/lib/format";
import { Badge } from "./ui";

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between items-baseline gap-4 py-[7px] border-b border-white/10 last:border-none">
      <span className="text-[13px] text-ink-muted shrink-0">{k}</span>
      <span className="text-[13px] font-medium text-right">{children}</span>
    </div>
  );
}

/** Two-level display: clean answer above, expandable router details here.
 *  Every row is null-safe ("—"); a response without transparency fields
 *  renders structure, never blankness. */
export function RouterDetails({ resp }: { resp: AskResponse }) {
  const d = resp.decision;
  const v = resp.verdict;
  const iv = resp.initial_verdict ?? null;
  const issues = iv?.issues ?? [];
  return (
    <details className="bg-ink-surface border border-white/10 rounded-xl px-[18px] py-3">
      <summary className="cursor-pointer list-none flex items-center gap-2 text-[13px] font-semibold text-ink-text marker:hidden">
        <span aria-hidden>▶</span> Router Details
      </summary>
      <div className="mt-2">
        <Row k="Initial model">
          {resp.initial_model ?? resp.selected_model?.display_name ?? "—"}
        </Row>
        <Row k="Final model">{resp.selected_model?.display_name ?? "—"}</Row>
        <Row k="Task">{d?.task_type ? titleCase(d.task_type) : "—"}</Row>
        <Row k="Quality">
          {v?.quality_score != null ? `${Math.round(v.quality_score * 100)}%` : "—"}{" "}
          {v == null ? (
            <Badge tone="no">—</Badge>
          ) : (
            <Badge tone={v.passed ? "pass" : "warn"}>{v.passed ? "Passed" : "Failed"}</Badge>
          )}
        </Row>
        <Row k="Escalated">
          <Badge tone={resp.escalated ? "warn" : "no"}>{resp.escalated ? "Yes" : "No"}</Badge>
        </Row>
        {iv != null && (
          <>
            <p className="text-[11.5px] text-ink-dim m-0 mt-3 mb-1 font-medium">
              WHY WAS IT REJECTED?
            </p>
            <p className="text-[13px] m-0 mb-2">{iv.reason || "—"}</p>
            {issues.length > 0 && (
              <>
                <p className="text-[11.5px] text-ink-dim m-0 mb-1 font-medium">ISSUES FOUND</p>
                <ul className="m-0 mb-2 pl-4 text-[13px] space-y-0.5">
                  {issues.map((issue, i) => (
                    <li key={i}>• {issue}</li>
                  ))}
                </ul>
              </>
            )}
            {iv.improvement_instructions && (
              <>
                <p className="text-[11.5px] text-ink-dim m-0 mb-1 font-medium">
                  HOW WAS IT IMPROVED?
                </p>
                <p className="text-[13px] m-0 mb-1">{iv.improvement_instructions}</p>
              </>
            )}
          </>
        )}
        <Row k="Calls">{resp.total_llm_api_calls ?? "—"}</Row>
        <Row k="Cost">{resp.cost ? fmtMoney(resp.cost.actual_cost) : "—"}</Row>
        <Row k="Saved">
          {resp.cost ? (
            <span className="text-mint font-semibold">{fmtPct(resp.cost.savings_percent)}</span>
          ) : (
            "—"
          )}
        </Row>
      </div>
    </details>
  );
}
