"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { UserButton, SignInButton, useAuth } from "@clerk/nextjs";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { formatSaved, monthSavings } from "@/lib/ledger";

const NAV = [
  {
    href: "/",
    label: "Dashboard",
    icon: "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z M9 22V12h6v10",
  },
  {
    href: "/console",
    label: "Console",
    icon: "M4 17l6-6-6-6M12 19h8",
  },
  {
    href: "/history",
    label: "History",
    icon: "M12 7v5l3 2M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z",
  },
  {
    href: "/models",
    label: "Models",
    icon: "M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5",
  },
  {
    href: "/analytics",
    label: "Analytics",
    icon: "M18 20V10M12 20V4M6 20v-6",
  },
  {
    href: "/connectors",
    label: "Connectors",
    icon: "M18 5v0M6 12v0M18 19v0M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98",
  },
];

function AuthSkeleton() {
  return (
    <div className="flex items-center gap-2" aria-label="Authentication loading">
      <div className="w-6 h-6 rounded-full bg-white/10 animate-pulse" />
      <div className="h-3 w-20 rounded bg-white/10 animate-pulse" />
    </div>
  );
}

function AuthFallback() {
  return (
    <div>
      <p className="text-xs text-ink-muted m-0 mb-2">
        Authentication is temporarily unavailable.
      </p>
      <div className="flex gap-3">
        <Link href="/sign-in" className="text-xs text-gold">
          Sign In
        </Link>
        <Link href="/sign-up" className="text-xs text-gold">
          Sign Up
        </Link>
      </div>
    </div>
  );
}

function FooterAuth() {
  const { isLoaded, isSignedIn } = useAuth();
  if (!isLoaded) return <AuthSkeleton />;
  if (isSignedIn) {
    return (
      <div className="flex items-center gap-2">
        <UserButton afterSignOutUrl="/" />
        <span className="text-xs text-ink-muted">Signed in</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-3">
      <SignInButton mode="modal">
        <button className="text-xs text-gold">Sign in</button>
      </SignInButton>
      <Link href="/sign-up" className="text-xs text-gold">
        Sign up
      </Link>
    </div>
  );
}

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [saved, setSaved] = useState<number | null>(null);
  useEffect(() => {
    const refresh = () => setSaved(monthSavings());
    refresh();
    window.addEventListener("car:ledger-update", refresh);
    return () => window.removeEventListener("car:ledger-update", refresh);
  }, []);
  return (
    <div className="flex min-h-screen">
      <aside className="w-[216px] shrink-0 bg-ink-surface2 border-r border-white/10 px-3.5 py-5 flex flex-col gap-0.5">
        <div className="flex items-center gap-2 px-2 pb-5">
          <div className="w-[22px] h-[22px] rounded-md bg-gradient-to-br from-gold to-[#7A5410]" />
          <div className="text-sm font-semibold tracking-tight">Cost-Aware AI Router</div>
        </div>
        {NAV.map((item) => {
          const active = item.href === "/" ? path === "/" : path.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-[13.5px] no-underline transition-colors ${
                active
                  ? "bg-[#F0B429]/10 text-[#F0B429] border border-[#F0B429]/25"
                  : "text-ink-muted border border-transparent hover:text-ink-text hover:bg-white/[0.03]"
              }`}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" className="w-[17px] h-[17px] opacity-85 shrink-0">
                <path d={item.icon} />
              </svg>
              {item.label}
            </Link>
          );
        })}
        <div className="flex-1" />
        {saved != null && saved > 0 && (
          <div className="px-2 py-2.5 border-t border-white/10 mt-2">
            <p className="text-[11px] text-ink-dim m-0">Saved this month</p>
            <p className="text-sm font-semibold text-[#F0B429] m-0 font-mono">{formatSaved(saved)}</p>
          </div>
        )}
        <div className="px-2 py-2.5 border-t border-white/10 mt-2 flex items-center gap-2">
          <ErrorBoundary fallback={<AuthFallback />}>
            <FooterAuth />
          </ErrorBoundary>
        </div>
      </aside>
      <main className="flex-1 min-w-0 px-9 py-7 pb-16">{children}</main>
    </div>
  );
}
