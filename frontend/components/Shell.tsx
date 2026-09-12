"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton, SignedIn, SignedOut, SignInButton } from "@clerk/nextjs";

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
];

export function Shell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  return (
    <div className="flex min-h-screen">
      <aside className="w-[216px] shrink-0 bg-ink-surface2 border-r border-white/10 px-3.5 py-5 flex flex-col gap-0.5">
        <div className="flex items-center gap-2 px-2 pb-5">
          <div className="w-[22px] h-[22px] rounded-md bg-gradient-to-br from-mint to-[#0F6E56]" />
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
                  ? "bg-white/5 text-ink-text border border-white/10"
                  : "text-ink-muted border border-transparent hover:text-ink-text hover:bg-white/[0.03]"
              }`}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 opacity-85 shrink-0">
                <path d={item.icon} />
              </svg>
              {item.label}
            </Link>
          );
        })}
        <div className="flex-1" />
        <div className="px-2 py-2.5 border-t border-white/10 mt-2 flex items-center gap-2">
          <SignedIn>
            <UserButton />
            <span className="text-xs text-ink-muted">Signed in</span>
          </SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="text-xs text-mint">Sign in</button>
            </SignInButton>
          </SignedOut>
        </div>
      </aside>
      <main className="flex-1 min-w-0 px-9 py-7 pb-16">{children}</main>
    </div>
  );
}
