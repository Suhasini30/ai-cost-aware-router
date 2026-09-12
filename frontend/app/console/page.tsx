"use client";

import { useEffect, useState } from "react";
import { useAuth, SignInButton } from "@clerk/nextjs";
import { AnswerCard, TraceTimeline } from "@/components/AnswerTrace";
import { CostCard, ReliabilityCard, SummaryGrid } from "@/components/Panels";
import { RouterDetails } from "@/components/RouterDetails";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { PromptCard } from "@/components/PromptCard";
import { SkeletonCard } from "@/components/ui";
import { AskResponse, ApiError, errorHint, getModels, postAsk } from "@/lib/api";

export default function ConsolePage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [prompt, setPrompt] = useState("");
  const [running, setRunning] = useState(false);
  const [resp, setResp] = useState<AskResponse | null>(null);
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
    setResp(null);
    try {
      const token = await getToken();
      if (!token) throw new ApiError(401, "No session token — please sign in.");
      setResp(await postAsk(prompt.trim(), token));
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
            <button className="shrink-0 bg-mint text-[#04342C] rounded-lg px-4 py-2 text-[13px] font-semibold hover:opacity-90 transition-opacity">
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

      {resp && !running && (
        <ErrorBoundary>
          {resp.cost == null && (
            <div className="bg-amber-bg border border-amber-soft/30 rounded-[10px] px-4 py-3 mb-5 text-[13px] text-amber-soft">
              This response is missing cost data — the backend is running
              pre-Phase-8 code. Restart uvicorn on the latest branch.
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-[1.55fr_1fr] gap-5 items-start">
            <div className="flex flex-col gap-5">
              <AnswerCard resp={resp} />
              <RouterDetails resp={resp} />
              <TraceTimeline resp={resp} universe={universe} />
            </div>
            <div className="flex flex-col gap-5">
              <SummaryGrid resp={resp} />
              <CostCard resp={resp} />
              <ReliabilityCard resp={resp} />
            </div>
          </div>
        </ErrorBoundary>
      )}
      <p className="text-[11.5px] text-ink-dim mt-6 text-center">Console calls your live FastAPI backend.</p>
    </div>
  );
}

