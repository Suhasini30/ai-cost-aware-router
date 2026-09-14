"use client";

import { useEffect, useState } from "react";
import { useAuth, SignInButton } from "@clerk/nextjs";
import { AnswerCard, TraceTimeline } from "@/components/AnswerTrace";
import { CostCard, ReliabilityCard, SummaryGrid } from "@/components/Panels";
import { RouterDetails } from "@/components/RouterDetails";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PromptCard } from "@/components/PromptCard";
import { SkeletonCard } from "@/components/ui";
import { fmtMoney } from "@/lib/format";
import { recordRun } from "@/lib/ledger";
import { AskResponse, ApiError, errorHint, getModels, postAsk } from "@/lib/api";

function ResultCard({ resp, universe }: { resp: AskResponse; universe: string[] }) {
  const modelName = resp.selected_model?.display_name ?? resp.selected_model?.id ?? "unknown model";
  const cost = resp.cost?.actual_cost;
  return (
    <div className="bg-ink-surface border border-white/10 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2.5 px-[18px] py-3 border-b border-white/10 bg-ink-surface2">
        <span className="inline-block w-2 h-2 rounded-full bg-teal shrink-0" aria-label="served" />
        <span className="text-[13px] font-semibold font-mono">{modelName}</span>
        <span className="flex-1" />
        <span className="text-[13px] font-mono text-gold">{cost != null ? fmtMoney(cost) : "—"}</span>
      </div>
      <div className="p-[18px] flex flex-col gap-5">
        <ErrorBoundary>
          <AnswerCard resp={resp} />
          <RouterDetails resp={resp} />
          <TraceTimeline resp={resp} universe={universe} />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <SummaryGrid resp={resp} />
            <div className="flex flex-col gap-5">
              <CostCard resp={resp} />
              <ReliabilityCard resp={resp} />
            </div>
          </div>
        </ErrorBoundary>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="bg-ink-surface border border-white/10 rounded-xl p-10 flex flex-col items-center gap-3 text-center">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} className="w-8 h-8 text-ink-dim">
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-4.3-4.3" />
      </svg>
      <p className="text-[13px] text-ink-muted m-0">No runs yet — submit a prompt above and the routed answer lands here.</p>
    </div>
  );
}

export default function ConsolePage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [running, setRunning] = useState(false);
  const [resps, setResps] = useState<AskResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [universe, setUniverse] = useState<string[]>([]);

  useEffect(() => {
    getModels()
      .then((d) => setUniverse(d.models.map((m) => m.id)))
      .catch(() => setUniverse([]));
  }, []);

  async function onRun() {
    if (!prompt.trim() || running) return;
    setRunning(true);
    setError(null);
    try {
      const token = await getToken();
      if (!token) throw new ApiError(401, "No session token — please sign in.");
      const data = await postAsk(prompt.trim(), token);
      setResps((prev) => [data, ...prev].slice(0, 20));
      if (data.cost) recordRun(data.cost.actual_cost, data.cost.baseline_cost);
    } catch (e) {
      setError(errorHint(e));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <div className="mb-[22px]">
        <p className="text-[17px] font-semibold m-0">Ask the AI router</p>
        <p className="text-xs text-ink-dim mt-0.5">Cheapest capable model, evaluated and escalated only when needed.</p>
      </div>

      {/* Sign-in CTA — prominent when not authenticated */}
      {isLoaded && !isSignedIn && (
        <div className="bg-ink-surface border border-white/15 rounded-xl p-5 mb-5 flex items-center justify-between gap-4">
          <div>
            <p className="text-[13.5px] font-semibold m-0 mb-1">Sign in to run the router</p>
            <p className="text-xs text-ink-muted m-0">The API requires a Clerk session token. It only takes a second.</p>
          </div>
          <SignInButton mode="modal">
            <button className="shrink-0 bg-gold text-[#231A03] rounded-lg px-4 py-2 text-[13px] font-semibold hover:opacity-90 transition-opacity">
              Sign in
            </button>
          </SignInButton>
        </div>
      )}

      <PromptCard prompt={prompt} setPrompt={setPrompt} running={running} onRun={onRun} />

      {error && (
        <div className="bg-rose-bg border border-rose-soft/30 rounded-[10px] px-3 py-2.5 mb-5 text-[13px] text-rose-soft">
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {running && (
        <div className="grid grid-cols-1 lg:grid-cols-[1.55fr_1fr] gap-5 items-start">
          <div className="flex flex-col gap-5">
            <SkeletonCard label="Final answer" />
            <SkeletonCard label="Routing decision trace" />
          </div>
          <div className="flex flex-col gap-5">
            <SkeletonCard label="Routing summary" />
            <SkeletonCard label="Cost" />
            <SkeletonCard label="Provider reliability" />
          </div>
        </div>
      )}

      {!running && resps.length === 0 && !error && <EmptyState />}

      {resps.length > 0 && (
        <div className="flex flex-col gap-5">
          {resps.map((resp, i) => (
            <ResultCard key={`${resp.latency_ms}-${i}`} resp={resp} universe={universe} />
          ))}
        </div>
      )}
      <p className="text-[11.5px] text-ink-dim mt-6 text-center">Console calls your live FastAPI backend.</p>
    </div>
  );
}

