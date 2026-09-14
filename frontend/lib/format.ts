export function fmtMoney(n: number): string {
  if (!isFinite(n)) return "$—";
  if (n === 0) return "$0";
  if (n < 0.01) return `$${n.toFixed(5)}`;
  return `$${n.toFixed(4)}`;
}

export function fmtPct(n: number): string {
  if (!isFinite(n)) return "—";
  return `${n.toFixed(1)}%`;
}

export function fmtTokens(n: number | null): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString();
}

export function fmtMs(n: number): string {
  if (!isFinite(n)) return "—";
  return n >= 1000 ? `${(n / 1000).toFixed(1)}s` : `${Math.round(n)}ms`;
}

export function titleCase(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
