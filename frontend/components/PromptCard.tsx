"use client";

export const MAX_CHARS = 4000;

export const CHIPS: { label: string; sample: string }[] = [
  { label: "Coding", sample: "Write a Python function that merges two sorted linked lists in O(n) time." },
  { label: "Reasoning", sample: "A passport is required for international travel. Maya is traveling internationally. Does Maya need a passport? Explain step by step." },
  { label: "Summarization", sample: "Summarize this article in three sentences: Electric cars are becoming cheaper every year as battery costs fall. Charging networks are expanding, though rural coverage still lags behind cities." },
  { label: "Extraction", sample: "Extract all invoice totals as a table from this text: Invoice A total $120.50 due March 3. Invoice B total $89.99 due March 10." },
  { label: "Classification", sample: "Classify this email as spam or ham: Congratulations, you have won a free cruise! Click here to claim your prize now!" },
  { label: "General Q&A", sample: "What is the capital of France?" },
];

export function PromptCard({
  prompt,
  setPrompt,
  running,
  onRun,
}: {
  prompt: string;
  setPrompt: (v: string) => void;
  running: boolean;
  onRun: () => void;
}) {
  const charCount = prompt.length;
  const nearLimit = charCount > MAX_CHARS * 0.8;
  const atLimit = charCount >= MAX_CHARS;

  return (
    <div className="bg-ink-surface border border-white/10 rounded-xl p-4 mb-5">
      <div className="flex gap-1.5 mb-3 flex-wrap">
        {CHIPS.map((chip) => (
          <button
            key={chip.label}
            onClick={() => setPrompt(chip.sample)}
            className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
              prompt === chip.sample
                ? "bg-gold-bg border-gold/40 text-gold"
                : "border-white/20 text-ink-muted hover:border-white/40 hover:text-ink-text"
            }`}
          >
            {chip.label}
          </button>
        ))}
      </div>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value.slice(0, MAX_CHARS))}
        placeholder="Ask anything — the router picks the cheapest capable model."
        className="w-full min-h-[72px] resize-none bg-ink-surface2 border border-white/15 rounded-lg px-3 py-2.5 outline-none text-ink-text text-sm leading-relaxed placeholder:text-ink-dim focus-within:border-white/30"
      />
      <div className="flex items-center justify-between mt-2">
        <span className={`text-[11px] font-mono tabular-nums transition-colors ${
          atLimit ? "text-rose-soft" : nearLimit ? "text-amber-soft" : "text-ink-dim"
        }`}>
          {charCount.toLocaleString()} / {MAX_CHARS.toLocaleString()}
        </span>
        <button
          onClick={onRun}
          disabled={running || !prompt.trim()}
          className="bg-gold text-[#231A03] rounded-lg px-4 py-2 text-[13px] font-semibold disabled:opacity-40 transition-opacity hover:opacity-90"
        >
          {running ? "Routing…" : "Run router"}
        </button>
      </div>
    </div>
  );
}
