import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  fetchImpl: vi.fn(),
}));

vi.mock("@clerk/nextjs", () => ({
  useAuth: mocks.useAuth,
  UserButton: () => <div data-testid="user-button" />,
  SignInButton: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

vi.mock("next/navigation", () => ({ usePathname: () => "/analytics" }));

import AnalyticsPage from "@/app/analytics/page";

function report(over: Record<string, unknown> = {}) {
  return {
    range: "7d",
    total_requests: 4,
    actual_spend: 0.006,
    always_strong_baseline_spend: 0.01,
    savings: 0.004,
    savings_percent: 40.0,
    escalation_rate: 0.25,
    average_quality: 0.87,
    requests_by_model: [
      { model: "mistral-fast", count: 3, cost: 0.004 },
      { model: "mistral-strong", count: 1, cost: 0.002 },
    ],
    spend_over_time: [
      { date: "2026-09-01", actual_cost: 0.004, baseline_cost: 0.007 },
      { date: "2026-09-02", actual_cost: 0.002, baseline_cost: 0.003 },
    ],
    escalations_by_reason: [
      { reason: "quality gate failed", category: "quality", count: 1 },
    ],
    avg_latency_by_model: [
      { model: "mistral-fast", latency_ms: 900 },
      { model: "mistral-strong", latency_ms: 2100 },
    ],
    ...over,
  };
}

function signedIn() {
  mocks.useAuth.mockReturnValue({
    isLoaded: true,
    isSignedIn: true,
    getToken: async () => "tok",
  });
}

function jsonResponse(body: unknown, ok = true, status = 200) {
  return { ok, status, statusText: "x", json: async () => body };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("AnalyticsPage", () => {
  it("renders empty state with zero traces and no fake numbers", async () => {
    signedIn();
    mocks.fetchImpl.mockResolvedValue(jsonResponse(report({ total_requests: 0 })));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() =>
      expect(screen.getByText("No usage data yet")).toBeTruthy()
    );
    expect(screen.queryByText("Total Savings")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("renders KPI values from the report", async () => {
    signedIn();
    mocks.fetchImpl.mockResolvedValue(jsonResponse(report()));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("4")).toBeTruthy());
    expect(screen.getByText("$0.00400")).toBeTruthy();
    expect(screen.getByText("25.0%")).toBeTruthy();
    vi.unstubAllGlobals();
  });

  it("renders model data", async () => {
    signedIn();
    mocks.fetchImpl.mockResolvedValue(jsonResponse(report()));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() =>
      expect(screen.getAllByText("mistral-strong").length).toBeGreaterThan(0)
    );
    expect(screen.getAllByText("mistral-fast").length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  });

  it("range switching refetches with the new range", async () => {
    signedIn();
    mocks.fetchImpl.mockResolvedValue(jsonResponse(report()));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("4")).toBeTruthy());
    screen.getByText("30d").click();
    await waitFor(() =>
      expect(
        mocks.fetchImpl.mock.calls.some(([url]: string[]) =>
          String(url).includes("range=30d")
        )
      ).toBe(true)
    );
    vi.unstubAllGlobals();
  });

  it("refresh retrieves fresh data", async () => {
    signedIn();
    mocks.fetchImpl.mockResolvedValue(jsonResponse(report()));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() => expect(screen.getByText("4")).toBeTruthy());
    const before = mocks.fetchImpl.mock.calls.length;
    screen.getByText("Refresh").click();
    await waitFor(() =>
      expect(mocks.fetchImpl.mock.calls.length).toBeGreaterThan(before)
    );
    vi.unstubAllGlobals();
  });

  it("shows loading state while fetching", async () => {
    signedIn();
    mocks.fetchImpl.mockReturnValue(new Promise(() => {}));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() => {
      if (!document.querySelector(".animate-pulse")) {
        throw new Error("waiting for skeletons");
      }
    });
    vi.unstubAllGlobals();
  });

  it("shows error state on API failure without fake data", async () => {
    signedIn();
    mocks.fetchImpl.mockResolvedValue(jsonResponse({ detail: "down" }, false, 503));
    vi.stubGlobal("fetch", mocks.fetchImpl);
    render(<AnalyticsPage />);
    await waitFor(() =>
      expect(screen.getByText(/unavailable|failed|down/i)).toBeTruthy()
    );
    expect(screen.queryByText("Total Savings")).toBeNull();
    vi.unstubAllGlobals();
  });
});
