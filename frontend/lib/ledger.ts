/** Client-side savings ledger (localStorage). Tracks per-run actual vs
 *  baseline cost so the sidebar can show cumulative monthly savings
 *  without any backend dependency. */

export interface LedgerEntry {
  ts: number;
  actual: number;
  baseline: number;
}

const KEY = "car.savings.ledger.v1";
const MAX_ENTRIES = 500;

function readAll(): LedgerEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function recordRun(actual: number, baseline: number): void {
  try {
    const entries = [...readAll(), { ts: Date.now(), actual, baseline }];
    localStorage.setItem(KEY, JSON.stringify(entries.slice(-MAX_ENTRIES)));
    window.dispatchEvent(new Event("car:ledger-update"));
  } catch {
    /* storage unavailable (private mode) — savings footer stays empty */
  }
}

export function monthSavings(now = Date.now()): number {
  const d = new Date(now);
  const start = new Date(d.getFullYear(), d.getMonth(), 1).getTime();
  return readAll()
    .filter((e) => e.ts >= start)
    .reduce((sum, e) => sum + Math.max(0, e.baseline - e.actual), 0);
}

export function formatSaved(n: number): string {
  if (!isFinite(n) || n <= 0) return "$0.00";
  if (n < 0.01) return `$${n.toFixed(5)}`;
  return `$${n.toFixed(2)}`;
}
