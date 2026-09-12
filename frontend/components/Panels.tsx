import type { AskResponse } from "@/lib/api";
import { fmtMoney, fmtMs, fmtPct, fmtTokens, titleCase } from "@/lib/format";
import { Badge, Card } from "./ui";

function Stat({ k, v, tone }: { k: string; v: React.ReactNode; tone?: "emerald" | "amber" }) {
  return (
    <div className="bg-ink-surface2 border border-white/10 rounded-[10px] px-3 py-2.5">
      <p className="text-[11px] text-ink-dim m-0 mb-1">{k}</p>
      <p className={`text-sm font-semibold m-0 ${tone === "emerald" ? "text-mint" : tone === "amber" ? "text-amber-soft" : ""}`}>
        {v}
      </p>
    </div>
  );
}

export function SummaryGrid({ resp }: { resp: AskResponse }) {
  const d = resp.decision ?? ({} as AskResponse["decision"]);
  const v = resp.verdict;
  const modelName = resp.selected_model?.display_name ?? "—";
  return (
    <Card label="Routing summary">
      <div className="grid grid-cols-2 gap-2.5">
        <Stat k="Task type" v={d.task_type ? titleCase(d.task_type) : "—"} />
        <Stat k="Complexity" v={d.complexity ? titleCase(d.complexity) : "—"} />
        <Stat k="Capability" v={d.capability ? titleCase(d.capability) : "—"} />
        <Stat k="Confidence" v={d.confidence != null ? `${Math.round(d.confidence * 100)}%` : "—"} tone="emerald" />
        <Stat k="Selected model" v={modelName} />
        <Stat k="Quality score" v={v?.quality_score != null ? `${v.quality_score.toFixed(2)} / 1.0` : "— / 1.0"} tone="emerald" />
        <Stat k="Latency" v={fmtMs(resp.latency_ms)} />
        <Stat k="Tokens used" v={fmtTokens(resp.tokens_used)} />
        <Stat k="Escalated" v={<Badge tone={resp.escalated ? "warn" : "no"}>{resp.escalated ? "Yes" : "No"}</Badge>} />
        <Stat k="Quality" v={v == null ? <Badge tone="no">—</Badge> : <Badge tone={v.passed ? "pass" : "warn"}>{v.passed ? "Pass" : "Fail"}</Badge>} />
        <Stat k="Classifier" v={<span className="text-[11.5px] font-mono text-ink-muted">{resp.classifier_model_used ?? "—"}</span>} />
      </div>
    </Card>
  );
}


export function CostCard({ resp }: { resp: AskResponse }) {
  const c = resp.cost;
  if (!c) {
    return (
      <Card label="Cost">
        <p className="text-[13px] text-ink-muted m-0">Cost data unavailable in this response.</p>
      </Card>
    );
  }
  const pct = Math.min(100, Math.max(0, c.savings_percent ?? 0));
  return (
    <Card label="Cost">
      <div className="flex justify-between items-baseline py-[7px] border-b border-white/10">
        <span className="text-[13px] text-ink-muted">Actual cost</span>
        <span className="text-[13.5px] font-medium">{fmtMoney(c.actual_cost)}</span>
      </div>
      <div className="flex justify-between items-baseline py-[7px]">
        <span className="text-[13px] text-ink-muted">Strong-model baseline</span>
        <span className="text-[13.5px] text-ink-dim line-through">{fmtMoney(c.baseline_cost)}</span>
      </div>
      <div className="mt-3 bg-mint-bg border border-mint/30 rounded-[10px] px-3 py-2.5 flex justify-between items-center">
        <div>
          <div className="text-[15px] font-bold text-mint">{fmtMoney(c.savings)} saved</div>
          <div className="text-xs text-mint opacity-85">vs. always using the strong model</div>
        </div>
        <div className="text-base font-bold text-mint">{fmtPct(c.savings_percent)}</div>
      </div>
      <div className="h-[5px] rounded bg-white/5 mt-2.5 overflow-hidden">
        <div className="h-full bg-mint rounded" style={{ width: `${pct}%` }} />
      </div>
    </Card>
  );
}

export function ReliabilityCard({ resp }: { resp: AskResponse }) {
  const flagged = resp.transport_fallback || resp.fallback;
  const escRule = (resp.trace ?? []).find((s) => s.stage === "escalation")?.rule;
  return (
    <Card label="Provider reliability">
      {!flagged ? (
        <div className="flex items-center gap-2 text-[13px] text-ink-muted">
          <span className="text-mint">✓</span>No provider fallback required
        </div>
      ) : (
        <div className="bg-amber-bg border border-amber-soft/30 rounded-[10px] px-3 py-2.5">
          <p className="text-[13px] font-semibold text-amber-soft m-0 mb-1.5">⚠ Fallback engaged</p>
          {resp.transport_fallback && (
            <p className="text-xs text-ink-muted m-0">Provider failover served this answer.</p>
          )}
          {escRule && <p className="text-xs text-ink-muted mt-1">{escRule}</p>}
        </div>
      )}
    </Card>
  );
}
