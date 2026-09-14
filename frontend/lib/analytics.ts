import { ApiError } from "@/lib/api";

export type RangeKey = "7d" | "30d" | "all";
export const RANGES: { key: RangeKey; label: string }[] = [
  { key: "7d", label: "7d" },
  { key: "30d", label: "30d" },
  { key: "all", label: "All time" },
];

export interface ModelRow {
  model: string;
  count: number;
  cost: number;
}

export interface DayRow {
  date: string;
  actual_cost: number;
  baseline_cost: number;
}

export interface EscalationRow {
  reason: string;
  category: string;
  model: string;
  count: number;
}

export interface LatencyRow {
  model: string;
  latency_ms: number;
}

export interface AnalyticsReport {
  range: string;
  total_requests: number;
  actual_spend: number;
  always_strong_baseline_spend: number;
  savings: number;
  savings_percent: number;
  escalation_rate: number;
  average_quality: number | null;
  requests_by_model: ModelRow[];
  spend_over_time: DayRow[];
  escalations_by_reason: EscalationRow[];
  avg_latency_by_model: LatencyRow[];
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export async function fetchAnalytics(
  range: RangeKey,
  token: string
): Promise<AnalyticsReport> {
  const res = await fetch(
    `${API}/analytics?range=${encodeURIComponent(range)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<AnalyticsReport>;
}

export function analyticsErrorHint(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return "Session expired — please sign in again.";
    if (err.status === 422) return err.message;
    if (err.status === 503)
      return "Analytics store unavailable. Try again later.";
    return `Request failed (${err.status}): ${err.message}`;
  }
  return "Network error — is the backend running?";
}
