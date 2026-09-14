"use client";

import React from "react";

/** Catches render crashes (e.g. shape drift in API responses) and shows
 *  a message instead of a blank area. Data-fetch errors are handled
 *  separately by the page-level error state. */
export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      if (this.props.fallback !== undefined) {
        return <>{this.props.fallback}</>;
      }
      return (
        <div className="bg-rose-bg border border-rose-soft/30 rounded-[10px] px-4 py-3 mb-5">
          <p className="text-[13px] font-semibold text-rose-soft m-0 mb-1">
            This result could not be displayed.
          </p>
          <p className="text-xs text-ink-muted m-0 font-mono">
            {this.state.error.message}
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
