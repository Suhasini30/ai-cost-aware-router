import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="glass p-4 text-center mt-8">
      <p className="text-[var(--color-muted)] text-sm">© 2026 Cost‑Aware Router. All rights reserved.</p>
      <nav className="space-x-4 mt-2">
        <Link href="/" className="text-[var(--color-muted)] hover:text-[var(--color-primary)] transition-colors">Home</Link>
        <Link href="/privacy" className="text-[var(--color-muted)] hover:text-[var(--color-primary)] transition-colors">Privacy</Link>
        <Link href="/terms" className="text-[var(--color-muted)] hover:text-[var(--color-primary)] transition-colors">Terms</Link>
      </nav>
    </footer>
  );
}
