export function Card({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px]">
      <p className="text-[11.5px] text-ink-dim m-0 mb-2.5 font-medium">{label}</p>
      {children}
    </div>
  );
}

export function Badge({ tone, children }: { tone: "pass" | "no" | "warn"; children: React.ReactNode }) {
  const cls =
    tone === "pass"
      ? "bg-mint-bg text-mint"
      : tone === "warn"
        ? "bg-amber-bg text-amber-soft"
        : "bg-white/5 text-ink-muted";
  return (
    <span className={`inline-flex items-center gap-1 text-[11.5px] px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {children}
    </span>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`animate-pulse bg-white/[0.06] rounded-lg ${className}`} />
  );
}

export function SkeletonCard({ label }: { label: string }) {
  return (
    <div className="bg-ink-surface border border-white/10 rounded-xl p-[18px]">
      <p className="text-[11.5px] text-ink-dim m-0 mb-2.5 font-medium">{label}</p>
      <div className="flex flex-col gap-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

