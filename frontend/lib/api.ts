export interface RouteStage {
  stage: string;
  rule: string;
  kept: string[];
}

export interface ModelSpec {
  id: string;
  provider: string;
  api_id: string;
  display_name: string;
  tier: string;
  input_cost_per_1k: number;
  output_cost_per_1k: number;
  context_window: number;
  max_output_tokens: number;
  capabilities: string[];
  enabled: boolean;
}

export interface CostBreakdown {
  model_id: string;
  input_tokens: number;
  output_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
}

export interface CostResult {
  actual_cost: number;
  baseline_cost: number;
  savings: number;
  savings_percent: number;
  actual_breakdown: CostBreakdown[];
  baseline_model_id: string;
}

export interface AskResponse {
  answer: string;
  selected_model: ModelSpec;
  escalated: boolean;
  decision: {
    task_type: string;
    complexity: string;
    capability: string;
    quality_required: string;
    confidence: number;
    reason: string;
  };
  verdict: {
    passed: boolean;
    quality_score: number | null;
    reason: string;
    skipped_judge?: boolean;
    issues?: string[];
    improvement_instructions?: string | null;
  };
  classifier_model_used: string;
  latency_ms: number;
  tokens_used: number | null;
  trace: RouteStage[];
  fallback: boolean;
  transport_fallback: boolean;
  user_id: string | null;
  cost: CostResult;
  total_llm_api_calls?: number | null;
  // Rejection transparency (all null on clean passes).
  initial_model?: string | null;
  initial_verdict?: {
    passed: boolean;
    quality_score: number | null;
    reason: string;
    issues?: string[];
    improvement_instructions?: string | null;
  } | null;
  escalation_reason?: string | null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
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
  return res.json() as Promise<T>;
}

export function postAsk(prompt: string, token: string): Promise<AskResponse> {
  return request<AskResponse>("/router/ask", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt }),
  });
}

export function getModels(): Promise<{ models: ModelSpec[]; count: number }> {
  return request("/models");
}

export function errorHint(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401) return "Session expired or missing — please sign in again.";
    if (err.status === 422) return err.message;
    if (err.status === 502)
      return "Provider unavailable after retries — try again in a moment.";
    return `Request failed (${err.status}): ${err.message}`;
  }
  return "Network error — is the backend running?";
}
