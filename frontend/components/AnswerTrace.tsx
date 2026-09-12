import type { AskResponse } from "@/lib/api";
import { titleCase } from "@/lib/format";
import { Badge, Card } from "./ui";

export function AnswerCard({ resp }: { resp: AskResponse }) {
  return (
    <Card label="Final answer">
      <p className="text-[14.5px] leading-relaxed m-0 whitespace-pre-wrap">{resp.answer ?? ""}</p>
    </Card>
  );
}

const STAGE_TITLES: Record<string, string> = {
  capability: "Capability filter",
  confidence: "Confidence gate",
  complexity: "Complexity gate",
  quality: "Quality gate",
  escalation: "Escalation",
};

export function TraceTimeline({ resp, universe }: { resp: AskResponse; universe: string[] }) {
  const stages = resp.trace ?? [];
  let prev: string[] = universe;
  return (
    <Card label="Routing decision trace">
      {stages.length === 0 && (
        <p className="text-xs text-ink-dim m-0">No trace data in this response.</p>
      )}
      {stages.map((stage, i) => {
        const kept: string[] = stage.kept ?? [];
        const removed = prev.filter((m) => !kept.includes(m));
        prev = kept;
        return (
          <div key={`${stage.stage}-${i}`} className="flex gap-3 py-2.5 border-b border-white/10 last:border-none">
            <div className="w-5 h-5 rounded-full bg-ink-surface2 border border-white/20 flex items-center justify-center text-[10.5px] text-ink-muted shrink-0 mt-px">
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium m-0 mb-1 flex items-center gap-2">
                <span className="text-mint">✓</span>
                {STAGE_TITLES[stage.stage] ?? titleCase(stage.stage)}
              </p>
              <p className="text-xs text-ink-muted m-0 mb-1.5 leading-relaxed">{stage.rule ?? ""}</p>
              <div className="flex gap-1.5 flex-wrap">
                {kept.map((m) => (
                  <span key={m} className="text-[11px] px-2 py-0.5 rounded bg-ink-surface2 border border-white/20 text-ink-text">
                    {m}
                  </span>
                ))}
                {removed.map((m) => (
                  <span key={m} className="text-[11px] px-2 py-0.5 rounded bg-ink-surface2 border border-white/10 text-ink-dim line-through">
                    {m}
                  </span>
                ))}
              </div>
            </div>
          </div>
        );
      })}
    </Card>
  );
}
