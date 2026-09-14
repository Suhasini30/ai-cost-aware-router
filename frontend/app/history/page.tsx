"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Badge } from "@/components/ui";

interface HistoryItem {
  id: string;
  request_id: string;
  prompt: string;
  final_model: string;
  actual_cost: number;
  quality_score: number;
  latency_ms: number;
  passed: boolean;
  escalated: boolean;
  answer?: string;
  baseline_cost?: number;
  cost_saved?: number;
  created_at?: string;
}

interface HistoryPage {
  items: HistoryItem[];
  total: number;
  page: number;
  pages: number;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function api<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`History request failed (${res.status})`);
  return res.json() as Promise<T>;
}

function DetailDrawer({ item, token, onClose, onRated }: {
  item: HistoryItem;
  token: string;
  onClose: () => void;
  onRated: () => void;
}) {
  const [detail, setDetail] = useState<HistoryItem | null>(null);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api<HistoryItem>(`/history/${item.request_id}`, token).then(setDetail).catch(() => setDetail(item));
  }, [item, token]);

  async function sendFeedback() {
    if (!rating && !comment.trim()) return;
    await api(`/history/${item.request_id}/feedback`, token, {
      method: "POST",
      body: JSON.stringify({ rating: rating || undefined, comment: comment.trim() || undefined }),
    });
    setSent(true);
    onRated();
  }

  const shown = detail ?? item;
  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div className="relative w-full max-w-xl bg-ink-surface border-l border-white/10 p-5 overflow-y-auto">
        <div className="flex items-start justify-between gap-3 mb-4">
          <p className="text-[15px] font-semibold m-0">Request detail</p>
          <button onClick={onClose} className="text-ink-dim hover:text-ink-text text-lg leading-none">×</button>
        </div>
        <p className="text-[11.5px] text-ink-dim m-0 mb-1 font-medium">PROMPT</p>
        <p className="text-[13px] m-0 mb-4">{shown.prompt}</p>
        <p className="text-[11.5px] text-ink-dim m-0 mb-1 font-medium">ANSWER</p>
        <p className="text-[13px] m-0 mb-4 whitespace-pre-wrap">{shown.answer ?? "—"}</p>
        <div className="grid grid-cols-2 gap-2.5 mb-4">
          <div className="bg-ink-surface2 border border-white/10 rounded-[10px] px-3 py-2">
            <p className="text-[11px] text-ink-dim m-0">Model</p>
            <p className="text-[13px] font-semibold m-0">{shown.final_model}</p>
          </div>
          <div className="bg-ink-surface2 border border-white/10 rounded-[10px] px-3 py-2">
            <p className="text-[11px] text-ink-dim m-0">Cost / saved</p>
            <p className="text-[13px] font-semibold m-0 text-gold">${shown.actual_cost?.toFixed(5) ?? "—"} / ${shown.cost_saved?.toFixed(5) ?? "—"}</p>
          </div>
        </div>
        <p className="text-[11.5px] text-ink-dim m-0 mb-1 font-medium">YOUR RATING</p>
        {sent ? (
            <p className="text-[13px] text-gold m-0">Thanks — feedback recorded.</p>
        ) : (
          <div>
            <div className="flex gap-1.5 mb-2">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} onClick={() => setRating(n)}
                  className={`w-8 h-8 rounded-lg border text-[13px] font-semibold ${rating >= n ? "bg-gold-bg border-gold/40 text-gold" : "border-white/15 text-ink-dim"}`}>
                  {n}
                </button>
              ))}
            </div>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comment…"
              className="w-full min-h-16 bg-ink-surface2 border border-white/10 rounded-lg p-2.5 text-[13px] outline-none placeholder:text-ink-dim mb-2" />
            <button onClick={sendFeedback} className="bg-gold text-[#231A03] rounded-lg px-4 py-2 text-[13px] font-semibold">
              Send feedback
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [data, setData] = useState<HistoryPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [model, setModel] = useState("");
  const [passed, setPassed] = useState("");
  const [escalated, setEscalated] = useState("");
  const [selected, setSelected] = useState<HistoryItem | null>(null);
  const [token, setToken] = useState<string | null>(null);

  const load = useCallback(async () => {
    const t = await getToken();
    if (!t) { setError("Please sign in to view history."); return; }
    setToken(t);
    const q = new URLSearchParams({ page: String(page), limit: "20" });
    if (search.trim()) q.set("search", search.trim());
    if (model) q.set("model", model);
    if (passed) q.set("passed", passed);
    if (escalated) q.set("escalated", escalated);
    try {
      setData(await api<HistoryPage>(`/history?${q}`, t));
      setError(null);
    } catch {
      setError("Could not load history — is the backend running?");
    }
  }, [getToken, page, search, model, passed, escalated]);

  useEffect(() => { if (isLoaded && isSignedIn) load(); }, [isLoaded, isSignedIn, load]);
  useEffect(() => { setPage(1); }, [search, model, passed, escalated]);

  return (
    <div>
      <div className="mb-[22px]">
        <p className="text-[17px] font-semibold m-0">History</p>
        <p className="text-xs text-ink-dim mt-0.5">
          {data ? `${data.total} requests · page ${data.page} of ${Math.max(data.pages, 1)}` : "Every request, its model, cost and savings."}
        </p>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search prompts…"
          className="bg-ink-surface border border-white/10 rounded-lg px-3 py-2 text-[13px] outline-none placeholder:text-ink-dim w-56" />
        <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model id (e.g. gemini-fast)"
          className="bg-ink-surface border border-white/10 rounded-lg px-3 py-2 text-[13px] outline-none placeholder:text-ink-dim w-56" />
        <select value={passed} onChange={(e) => setPassed(e.target.value)}
          className="bg-ink-surface border border-white/10 rounded-lg px-3 py-2 text-[13px] text-ink-muted">
          <option value="">Quality: all</option>
          <option value="true">Passed</option>
          <option value="false">Failed</option>
        </select>
        <select value={escalated} onChange={(e) => setEscalated(e.target.value)}
          className="bg-ink-surface border border-white/10 rounded-lg px-3 py-2 text-[13px] text-ink-muted">
          <option value="">Escalation: all</option>
          <option value="true">Escalated</option>
          <option value="false">Not escalated</option>
        </select>
      </div>

      {error && (
        <div className="bg-rose-bg border border-rose-soft/30 rounded-[10px] px-4 py-3 mb-5 text-[13px] text-rose-soft">{error}</div>
      )}

      <div className="max-w-5xl">
        <div className="bg-ink-surface border border-white/10 rounded-xl overflow-hidden">
          <div className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-x-4 px-4 py-2.5 border-b border-white/10 bg-ink-surface2">
            {["Prompt", "Model", "Cost", "Quality", "Latency", "Status"].map((h) => (
              <span key={h} className="text-[11px] text-ink-dim font-medium uppercase tracking-wide">{h}</span>
            ))}
          </div>
          {(data?.items ?? []).map((row) => (
            <div key={row.request_id}
              onClick={() => setSelected(row)}
              className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-x-4 px-4 py-3 border-b border-white/[0.06] last:border-none items-center cursor-pointer hover:bg-white/[0.02]">
              <span className="text-[12.5px] text-ink-muted truncate pr-4" title={row.prompt}>{row.prompt}</span>
              <span className="text-[12px] text-ink-text font-medium whitespace-nowrap">{row.final_model}</span>
              <span className="text-[12px] text-gold font-mono whitespace-nowrap">${row.actual_cost?.toFixed(5) ?? "—"}</span>
              <span className="text-[12px] text-ink-muted font-mono whitespace-nowrap">{row.quality_score?.toFixed(2) ?? "—"}</span>
              <span className="text-[12px] text-ink-dim font-mono whitespace-nowrap">{Math.round(row.latency_ms ?? 0)}ms</span>
              <div className="flex gap-1.5 whitespace-nowrap">
                <Badge tone={row.passed ? "pass" : "warn"}>{row.passed ? "Pass" : "Fail"}</Badge>
                {row.escalated && <Badge tone="warn">↑ Esc</Badge>}
              </div>
            </div>
          ))}
          {data && data.items.length === 0 && (
            <p className="text-[13px] text-ink-dim text-center py-8 m-0">No requests yet — run the console to create history.</p>
          )}
        </div>
        {data && data.pages > 1 && (
          <div className="flex gap-2 mt-3 justify-center">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
              className="px-4 py-2 rounded-lg border border-white/15 text-[13px] disabled:opacity-40">← Prev</button>
            <button disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}
              className="px-4 py-2 rounded-lg border border-white/15 text-[13px] disabled:opacity-40">Next →</button>
          </div>
        )}
      </div>

      {selected && token && (
        <DetailDrawer item={selected} token={token} onClose={() => setSelected(null)} onRated={load} />
      )}
    </div>
  );
}
