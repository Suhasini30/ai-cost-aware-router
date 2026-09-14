import Link from 'next/link';

export default function Hero() {
  return (
    <section className="glass p-8 text-center mb-8">
      <h1 className="text-4xl font-bold mb-4" style={{ color: 'var(--color-primary)' }}>Cost‑Aware Routing</h1>
      <p className="text-lg text-[var(--color-muted)] mb-6">Route every request to the cheapest model that can actually handle it.</p>
      <Link href="/console" className="inline-block bg-gold text-[#231A03] rounded-lg px-6 py-3 text-sm font-semibold btn-ripple">
        Open console
      </Link>
    </section>
  );
}
