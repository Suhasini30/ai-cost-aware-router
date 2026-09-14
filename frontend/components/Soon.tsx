export function Soon({ title, sub }: { title: string; sub: string }) {
  return (
    <div>
      <p className="text-[17px] font-semibold m-0 mb-1">{title}</p>
      <p className="text-xs text-ink-dim mt-0 mb-5">{sub}</p>
      <div className="bg-ink-surface border border-white/10 rounded-xl p-5 max-w-xl text-[13px] text-ink-muted">
        Coming in the next build — the console page is fully live today.
      </div>
    </div>
  );
}
