import Link from "next/link";

const STEPS = [
  { n: "1", t: "Classify", d: "Task type, complexity and capability detected." },
  { n: "2", t: "Route", d: "Cheapest capable model wins the policy gates." },
  { n: "3", t: "Execute", d: "Provider adapters run with retry + failover." },
  { n: "4", t: "Evaluate", d: "Quality judged; one strong escalation max." },
];

export default function Home() {
  return (
    <div>
      <div className="mb-6">
        <p className="text-[17px] font-semibold m-0">Cost-aware routing</p>
        <p className="text-xs text-ink-dim mt-0.5">Route every request to the cheapest model that can actually handle it.</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-3xl">
        <div className="bg-ink-surface border border-white/10 rounded-xl p-5">
          <p className="text-sm font-semibold m-0 mb-2">Run the console</p>
          <p className="text-[13px] text-ink-muted m-0 mb-4">Submit a task, watch routing, cost and trace live.</p>
          <Link href="/console" className="inline-block bg-mint text-[#04342C] rounded-lg px-4 py-2 text-[13px] font-semibold no-underline">
            Open console
          </Link>
        </div>
        <div className="bg-ink-surface border border-white/10 rounded-xl p-5">
          <p className="text-sm font-semibold m-0 mb-2">How it works</p>
          {STEPS.map((s) => (
            <div key={s.n} className="flex gap-3 py-1.5">
              <span className="text-mint text-xs font-semibold">{s.n}</span>
              <p className="text-[13px] m-0"><span className="font-medium">{s.t}.</span> <span className="text-ink-muted">{s.d}</span></p>
            </div>
          ))}
        </div>
      </div>
      <p className="text-[11.5px] text-ink-dim mt-6 text-center">Backend: FastAPI · Auth: Clerk · Console calls the live API.</p>
    </div>
  );
}
