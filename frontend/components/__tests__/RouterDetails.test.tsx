import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RouterDetails } from "../RouterDetails";
import type { AskResponse } from "@/lib/api";

afterEach(cleanup);

function base(): AskResponse {
  return {
    answer: "Paris.",
    selected_model: {
      id: "mistral-strong",
      provider: "mistral",
      api_id: "mistral-large-latest",
      display_name: "Mistral Strong",
      tier: "strong",
      input_cost_per_1k: 0.002,
      output_cost_per_1k: 0.006,
      context_window: 128000,
      max_output_tokens: 8192,
      capabilities: ["chat"],
      enabled: true,
    },
    escalated: false,
    decision: {
      task_type: "general_qa",
      complexity: "low",
      capability: "text",
      quality_required: "standard",
      confidence: 0.9,
      reason: "t",
    },
    verdict: { passed: true, quality_score: 0.9, reason: "Good." },
    classifier_model_used: "cls",
    latency_ms: 100,
    tokens_used: 20,
    trace: [],
    fallback: false,
    transport_fallback: false,
    user_id: null,
    cost: {
      actual_cost: 0.0001,
      baseline_cost: 0.001,
      savings: 0.0009,
      savings_percent: 90,
      actual_breakdown: [],
      baseline_model_id: "mistral-strong",
    },
  };
}

describe("RouterDetails", () => {
  it("renders populated transparency fields", () => {
    const resp = base();
    resp.escalated = true;
    resp.initial_model = "mistral-fast";
    resp.initial_verdict = {
      passed: false,
      quality_score: 0.42,
      reason: "Incomplete.",
      issues: ["Missing implementation", "No complexity analysis"],
      improvement_instructions: "Provide both.",
    };
    resp.escalation_reason = "quality_gate_failed";
    render(<RouterDetails resp={resp} />);
    // NOTE: <details> starts closed, so assert against full text content
    // (getByText only matches visible elements).
    const text = document.querySelector("details")?.textContent ?? "";
    expect(screen.getByText("Router Details")).toBeTruthy();
    expect(text).toContain("mistral-fast");
    expect(text).toContain("Missing implementation");
    expect(text).toContain("Provide both.");
  });

  it("renders dashes, never blank, on all-null transparency", () => {
    const resp = base();
    resp.initial_model = null;
    resp.initial_verdict = null;
    resp.escalation_reason = null;
    const { container } = render(<RouterDetails resp={resp} />);
    expect(screen.getByText("Router Details")).toBeTruthy();
    expect(screen.queryByText("WHY WAS IT REJECTED?")).toBeNull();
    expect(container.textContent).toContain("—");
  });
});
