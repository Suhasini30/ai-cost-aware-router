import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Shell } from "@/components/Shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cost-Aware AI Router",
  description: "Route every request to the cheapest model that can handle it.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-ink-bg text-ink-text font-sans">
          <Shell>{children}</Shell>
        </body>
      </html>
    </ClerkProvider>
  );
}
