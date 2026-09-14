"use client";

import { useEffect, useState } from "react";
import { ModelSpec, getModels } from "@/lib/api";
import { fmtMoney } from "@/lib/format";
import { Skeleton } from "@/components/ui";

const TIER_STYLE: Record<string, string> = {
  fast: "bg-teal-bg text-teal border-teal/25",
  strong: "bg-amber-bg text-amber-soft border-amber-soft/25",
};

const MAX_COST = 0.006; // output cost ceiling for bar scaling

function CostBar({ value }: { value: number }) {
  const pct = Math.min(100, (value / MAX_COST) * 100);
  const color = pct < 10 ? "bg-teal" : pct < 40 ? "bg-amber-soft" : "bg-rose-soft";
  return (
    <div className="h-[5px] rounded-full bg-white/[0.06] overflow-hidden w-full mt-1">
      <div className={`h-full rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
    </div>
  );
}

function CapabilityChip({ label }: { label: string }) {
  return (
    <span className="text-[10.5px] px-1.5 py-0.5 rounded-md bg-white/[0.06] border border-white/10 text-ink-muted">
      {label}
    </span>
  );
}

function ModelRow({ m, maxInput, maxOutput }: { m: ModelSpec; maxInput: number; maxOutput: number }) {
  return (
    <div className={`bg-ink-surface border rounded-xl p-4 flex flex-col gap-3 transition-colors ${m.enabled ? "border-white/10" : "border-white/5 opacity-50"}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-[14px] font-semibold text-ink-text">{m.display_name}</span>
            <span className={`text-[10.5px] px-1.5 py-0.5 rounded-md border font-medium ${TIER_STYLE[m.tier] ?? "bg-white/5 text-ink-muted border-white/10"}`}>
              {m.tier}
            </span>
            {!m.enabled && (
              <span className="text-[10.5px] px-1.5 py-0.5 rounded-md bg-rose-bg text-rose-soft border border-rose-soft/20 font-medium">
                disabled
              </span>
            )}
          </div>
          <span className="text-[11.5px] text-ink-dim font-mono">{m.provider} · {m.api_id}</span>
        </div>
      </div>

      {/* Cost section */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-ink-surface2 rounded-[10px] px-3 py-2 border border-white/[0.07]">
          <p className="text-[10.5px] text-ink-dim m-0 mb-0.5">Input / 1k tokens</p>
          <p className="text-[13px] font-semibold m-0 text-ink-text">{fmtMoney(m.input_cost_per_1k)}</p>
          <CostBar value={m.input_cost_per_1k} />
        </div>
        <div className="bg-ink-surface2 rounded-[10px] px-3 py-2 border border-white/[0.07]">
          <p className="text-[10.5px] text-ink-dim m-0 mb-0.5">Output / 1k tokens</p>
          <p className="text-[13px] font-semibold m-0 text-ink-text">{fmtMoney(m.output_cost_per_1k)}</p>
          <CostBar value={m.output_cost_per_1k} />
        </div>
      </div>

      {/* Context window */}
      <div className="flex items-center gap-4 text-[11.5px] text-ink-dim">
        <span>Context: <span className="text-ink-muted font-medium">{(m.context_window / 1000).toFixed(0)}k tokens</span></span>
        <span>Max output: <span className="text-ink-muted font-medium">{(m.max_output_tokens / 1000).toFixed(0)}k tokens</span></span>
      </div>

      {/* Capabilities */}
      <div className="flex flex-wrap gap-1.5">
        {m.capabilities.map((cap) => (
          <CapabilityChip key={cap} label={cap} />
        ))}
      </div>
    </div>
  );
}

export default function ModelsPage() {
  const [models, setModels] = useState<ModelSpec[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getModels()
      .then((d) => setModels(d.models))
      .catch(() => setError("Could not load models — is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  const maxInput = Math.max(...(models.map((m) => m.input_cost_per_1k)), 0.001);
  const maxOutput = Math.max(...(models.map((m) => m.output_cost_per_1k)), 0.001);

  return (
    <div>
      <div className="mb-[22px]">
        <p className="text-[17px] font-semibold m-0">Model registry</p>
        <p className="text-xs text-ink-dim mt-0.5">
          {loading ? "Loading…" : `${models.length} models · tiers, pricing and capabilities.`}
        </p>
      </div>

      {error && (
        <div className="bg-rose-bg border border-rose-soft/30 rounded-[10px] px-4 py-3 mb-5 text-[13px] text-rose-soft">
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="bg-ink-surface border border-white/10 rounded-xl p-4 flex flex-col gap-3">
              <Skeleton className="h-5 w-2/3" />
              <div className="grid grid-cols-2 gap-3">
                <Skeleton className="h-14 rounded-[10px]" />
                <Skeleton className="h-14 rounded-[10px]" />
              </div>
              <Skeleton className="h-3 w-1/2" />
              <div className="flex gap-1.5">
                <Skeleton className="h-5 w-14 rounded-md" />
                <Skeleton className="h-5 w-20 rounded-md" />
                <Skeleton className="h-5 w-12 rounded-md" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
          {models.map((m) => (
            <ModelRow key={m.id} m={m} maxInput={maxInput} maxOutput={maxOutput} />
          ))}
        </div>
      )}

      <p className="text-[11.5px] text-ink-dim mt-6 text-center">
        Live data from <span className="font-mono">GET /models</span>.
      </p>
    </div>
  );
}
