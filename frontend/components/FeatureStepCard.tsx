export default function FeatureStepCard({ step }: { step: { n: string; t: string; d: string } }) {
  return (
    <div className="glass p-4 card-hover">
      <div className="flex gap-3 items-start">
        <span className="text-teal text-xs font-semibold">{step.n}</span>
        <div>
          <p className="font-medium text-[13px] text-[var(--color-text)] mb-1">{step.t}.</p>
          <p className="text-[13px] text-[var(--color-muted)]">{step.d}</p>
        </div>
      </div>
    </div>
  );
}
