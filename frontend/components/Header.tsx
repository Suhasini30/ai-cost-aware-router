"use client";

import Link from "next/link";
import { SignInButton, SignUpButton, UserButton, useAuth } from "@clerk/nextjs";

function NavAuth() {
  const { isLoaded, isSignedIn } = useAuth();

  if (!isLoaded) {
    return (
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-white/10 animate-pulse" />
      </div>
    );
  }

  if (isSignedIn) {
    return (
      <div className="flex items-center gap-3">
        <UserButton afterSignOutUrl="/" />
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <SignInButton mode="modal">
        <button
          className="text-sm px-4 py-1.5 rounded-lg border border-white/20 text-[var(--color-muted)] hover:text-[var(--color-text)] hover:border-white/40 transition-all"
        >
          Sign in
        </button>
      </SignInButton>
      <SignUpButton mode="modal">
        <button
          className="text-sm px-4 py-1.5 rounded-lg font-semibold transition-all"
          style={{ background: "var(--color-primary)", color: "#04342C" }}
        >
          Sign up
        </button>
      </SignUpButton>
    </div>
  );
}

export default function Header() {
  return (
    <header className="glass p-4 flex justify-between items-center sticky top-0 z-10">
      <h1 className="text-2xl font-semibold" style={{ color: "var(--color-primary)" }}>
        Cost‑Aware Router
      </h1>
      <nav className="flex items-center gap-5">
        <Link
          href="/"
          className="text-[var(--color-muted)] hover:text-[var(--color-primary)] transition-colors text-sm"
        >
          Home
        </Link>
        <Link
          href="/console"
          className="text-[var(--color-muted)] hover:text-[var(--color-primary)] transition-colors text-sm"
        >
          Console
        </Link>
        <NavAuth />
      </nav>
    </header>
  );
}
