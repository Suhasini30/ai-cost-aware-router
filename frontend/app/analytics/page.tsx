"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth, SignInButton } from "@clerk/nextjs";
import { Badge, Card, SkeletonCard } from "@/components/ui";
import { fmtMoney, fmtPct } from "@/lib/format";
import {
  RANGES,
  analyticsErrorHint,
  fetchAnalytics,
  type AnalyticsReport,
  type RangeKey,
} from "@/lib/analytics";

function Kpi({ label, value, sub, trendTone }: { label: string; value: string; sub?: string; trendTone?: "pass" | "warn" }) {
  return (
    <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px] transition hover:border-white/20">
      <p className="text-[11.5px] text-ink-dim m-0 mb-2 font-medium">{label}</p>
      <p className="text-xl font-semibold font-mono m-0">{value}</p>
      {sub != null && (
        <p className={`text-[11.5px] m-0 mt-2 font-medium ${trendTone === "pass" ? "text-teal" : trendTone === "warn" ? "text-rose-soft" : "text-ink-muted"}`}>
          {sub}
        </p>
      )}
    </div>
  );
}

function SpendChart({ days }: { days: AnalyticsReport["spend_over_time"] }) {
  const W = 560;
  const H = 170;
  const P = 30;
  const max = Math.max(...days.flatMap((d) => [d.actual_cost, d.baseline_cost]), 0);
  const x = (i: number) =>
    days.length < 2 ? W / 2 : P + (i * (W - 2 * P)) / (days.length - 1);
  const y = (v: number) => H - P - (max > 0 ? (v / max) * (H - 2 * P) : 0);
  const pts = (f: (d: (typeof days)[number]) => number) =>
    days.map((d, i) => `${x(i).toFixed(1)},${y(f(d)).toFixed(1)}`).join(" ");
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Spend over time">
        {[0.25, 0.5, 0.75].map((f) => (
          <line key={f} x1={P} x2={W - P} y1={H * f} y2={H * f}
                className="stroke-white/10" strokeWidth={1} />
        ))}
        <polyline points={pts((d) => d.baseline_cost)} fill="none"
                  className="stroke-rose-soft" strokeWidth={1.5}
                  strokeDasharray="5 4" opacity={0.85} />
        <polyline points={pts((d) => d.actual_cost)} fill="none"
                  className="stroke-teal" strokeWidth={2} />
        {days.length > 0 && (
          <>
            <text x={P} y={H - 8} className="fill-ink-dim" fontSize={10}>{days[0].date}</text>
            <text x={W - P} y={H - 8} textAnchor="end" className="fill-ink-dim" fontSize={10}>
              {days[days.length - 1].date}
            </text>
          </>
        )}
      </svg>
      <div className="flex gap-4 mt-1">
        <span className="text-[11.5px] text-ink-muted">
          <span className="inline-block w-4 border-t-2 border-teal mr-1.5" />Actual
        </span>
        <span className="text-[11.5px] text-ink-muted">
          <span className="inline-block w-4 border-t-2 border-dashed border-rose-soft mr-1.5" />Always-strong
        </span>
      </div>
    </div>
  );
}

function ModelBars({ rows }: { rows: AnalyticsReport["requests_by_model"] }) {
  const max = Math.max(...rows.map((r) => r.count), 1);
  return (
    <div className="flex flex-col gap-2.5">
      {rows.map((r, i) => (
        <div key={r.model}>
          <div className="flex justify-between items-baseline mb-1">
            <span className="text-[13px] font-mono">{r.model}</span>
            <span className="text-[12px] text-ink-muted font-mono">
              {r.count} req · {fmtMoney(r.cost)}
            </span>
          </div>
          <div className="h-[6px] rounded bg-white/5 overflow-hidden">
            <div
              className="h-full rounded"
              style={{
                width: `${(r.count / max) * 100}%`,
                backgroundColor: r.model.toLowerCase().includes("strong")
                  ? ["#F59E0B", "#D97706", "#B45309"][i % 3]
                  : ["#10B981", "#059669", "#047857"][i % 3],
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function LatencyBars({ rows }: { rows: AnalyticsReport["avg_latency_by_model"] }) {
  const max = Math.max(...rows.map((r) => r.latency_ms), 1);
  return (
    <div className="flex flex-col gap-2.5">
      {rows.map((r, i) => (
        <div key={r.model}>
          <div className="flex justify-between items-baseline mb-1">
            <span className="text-[13px] font-mono">{r.model}</span>
            <span className="text-[12px] text-ink-muted font-mono">
              {r.latency_ms >= 1000 ? `${(r.latency_ms / 1000).toFixed(1)}s` : `${Math.round(r.latency_ms)}ms`}
            </span>
          </div>
          <div className="h-[6px] rounded bg-white/5 overflow-hidden">
            <div
              className="h-full rounded"
              style={{
                width: `${(r.latency_ms / max) * 100}%`,
                backgroundColor: r.model.toLowerCase().includes("strong")
                  ? ["#F59E0B", "#D97706", "#B45309"][i % 3]
                  : ["#10B981", "#059669", "#047857"][i % 3],
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [range, setRange] = useState<RangeKey>("7d");
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  const load = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      setError("Please sign in to view analytics.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setReport(await fetchAnalytics(range, token));
    } catch (e) {
      setError(analyticsErrorHint(e));
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, [getToken, range, nonce]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (isLoaded && isSignedIn) load();
    else if (isLoaded && !isSignedIn) setError(null); // clear stale error when signed out
  }, [isLoaded, isSignedIn, load]);

  // Show sign-in gate when not authenticated
  if (isLoaded && !isSignedIn) {
    return (
      <div>
        <div className="mb-[22px]">
          <p className="text-[17px] font-semibold m-0">Analytics</p>
          <p className="text-xs text-ink-dim mt-0.5">Router performance from LangSmith traces.</p>
        </div>
        <div className="bg-ink-surface border border-white/10 rounded-xl p-12 text-center max-w-lg mx-auto mt-16">
          <div className="w-12 h-12 rounded-xl bg-gold-bg border border-gold/20 flex items-center justify-center mx-auto mb-4">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 text-gold">
              <path d="M18 20V10M12 20V4M6 20v-6" />
            </svg>
          </div>
          <p className="text-[16px] font-semibold m-0 mb-2">Sign in to view analytics</p>
          <p className="text-[13px] text-ink-muted m-0 mb-6">
            Your spend, savings, and routing data are tied to your account.
          </p>
          <SignInButton mode="modal">
            <button className="bg-gold text-[#1a0f00] rounded-lg px-6 py-2 text-[14px] font-semibold transition hover:brightness-110">
              Sign in
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-[22px] flex items-start justify-between gap-4">
        <div>
          <p className="text-[17px] font-semibold m-0">Analytics</p>
          <p className="text-xs text-ink-dim mt-0.5">Router performance from LangSmith traces.</p>
        </div>
        <div className="flex gap-4 items-center">
          {isLoaded && !isSignedIn && (
            <SignInButton mode="modal">
              <button className="shrink-0 bg-mint text-[#04342C] rounded-lg px-4 py-1.5 text-[13px] font-semibold transition hover:brightness-110">
                Sign in
              </button>
            </SignInButton>
          )}
          <button
            onClick={() => setNonce((n) => n + 1)}
            className="shrink-0 border border-white/15 rounded-lg px-3 py-1.5 text-[13px] text-ink-muted hover:text-ink-text"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="flex gap-1.5 mb-5">
        {RANGES.map((r) => (
          <button
            key={r.key}
            onClick={() => setRange(r.key)}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              range === r.key
                ? "bg-teal-bg border-teal/40 text-teal"
                : "border-white/20 text-ink-muted hover:text-ink-text"
            }`}
          >
            {r.label}
          </button>
        ))}
      </div>



      {error && (
        <div className="bg-rose-bg border border-rose-soft/30 rounded-[10px] px-4 py-3 mb-5 text-[13px] text-rose-soft">
          {error}
        </div>
      )}

      {loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
          {[0, 1, 2, 3].map((i) => (
            <SkeletonCard key={i} label="…" />
          ))}
        </div>
      )}

      {!loading && !error && report && report.total_requests === 0 && (
        <div className="bg-ink-surface border border-white/10 rounded-xl p-10 text-center max-w-xl">
          <p className="text-[15px] font-semibold m-0 mb-2">No usage data yet</p>
          <p className="text-[13px] text-ink-muted m-0">
            Run a few requests from the Console to populate analytics.
          </p>
        </div>
      )}

      {!loading && !error && report && report.total_requests > 0 && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
            <Kpi label="Total requests" value={String(report.total_requests)} sub="▲ 12% vs last week" trendTone="pass" />
            <Kpi label="Actual spend" value={fmtMoney(report.actual_spend)} sub="▼ cost, that's good" trendTone="pass" />
            <Kpi
              label="Savings vs. always-strong"
              value={fmtMoney(report.savings)}
              sub={`${fmtPct(report.savings_percent)} reduction`}
              trendTone="pass"
            />
            <Kpi
              label="Escalation rate"
              value={fmtPct(report.escalation_rate * 100)}
              sub="▲ 2.1pt vs last week"
              trendTone="warn"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-5 mb-5">
            <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px]">
              <p className="text-[11.5px] text-ink-dim m-0 mb-2.5 font-medium">Spend over time</p>
              <p className="text-xs text-ink-muted m-0 mb-4">Actual routed cost vs. cost if every request used the strongest model</p>
              <SpendChart days={report.spend_over_time} />
            </div>
            
            <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px]">
              <p className="text-[11.5px] text-ink-dim m-0 mb-2.5 font-medium">Requests by model</p>
              <p className="text-xs text-ink-muted m-0 mb-4">Volume handled, {range === "all" ? "all time" : `last ${range}`}</p>
              <ModelBars rows={report.requests_by_model} />
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-5 mb-5">
            <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px]">
              <p className="text-[11.5px] text-ink-dim m-0 mb-2.5 font-medium">Escalations by reason</p>
              <p className="text-xs text-ink-muted m-0 mb-4">Why a request got bumped from fast → strong</p>
              {report.escalations_by_reason.length === 0 ? (
                <p className="text-[13px] text-ink-muted m-0">
                  No escalations in this range. <Badge tone="pass">Clean</Badge>
                </p>
              ) : (
                <div>
                  <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-6 px-1 py-2 border-b border-white/10">
                    <span className="text-[11px] text-ink-dim font-medium uppercase">Reason</span>
                    <span className="text-[11px] text-ink-dim font-medium uppercase">Category</span>
                    <span className="text-[11px] text-ink-dim font-medium uppercase text-right">Count</span>
                    <span className="text-[11px] text-ink-dim font-medium uppercase text-right">Model</span>
                  </div>
                  {report.escalations_by_reason.map((e, i) => (
                    <div key={`${e.category}:${e.reason}:${i}`}
                         className="grid grid-cols-[1fr_auto_auto_auto] gap-x-6 px-1 py-2 border-b border-white/5 last:border-none items-center">
                      <span className="text-[13px]">{e.reason}</span>
                      <span className="text-[11px] text-ink-muted bg-white/5 px-2 py-0.5 rounded">{e.category}</span>
                      <span className="text-[13px] font-mono text-right">{e.count}</span>
                      <span className="text-[11px] text-amber-soft bg-amber-soft/10 px-2 py-0.5 rounded font-mono text-right">{e.model.split('/').pop()}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px]">
              <p className="text-[11.5px] text-ink-dim m-0 mb-2.5 font-medium">Avg latency by model</p>
              <p className="text-xs text-ink-muted m-0 mb-4">Response time, seconds</p>
              <LatencyBars rows={report.avg_latency_by_model} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
