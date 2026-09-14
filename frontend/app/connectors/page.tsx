"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui";
import { SkeletonCard } from "@/components/ui";

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${ok ? "bg-teal" : "bg-rose-soft"}`}
      aria-label={ok ? "connected" : "unreachable"}
    />
  );
}

function ConnectorCard({
  label,
  status,
  description,
  children,
}: {
  label: string;
  status: "connected" | "unreachable" | "unknown";
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <Card label={label}>
      <div className="flex items-center gap-2 mb-2">
        <Dot ok={status === "connected"} />
        <span className="text-sm font-semibold">
          {status === "connected" ? "Connected" : status === "unreachable" ? "Unreachable" : "Unknown"}
        </span>
      </div>
      <p className="text-[12.5px] text-ink-muted m-0">{description}</p>
      {children}
    </Card>
  );
}

export default function ConnectorsPage() {
  const [parallelSearchOk, setParallelSearchOk] = useState<boolean | null>(null);
  const [parallelSearchConnected, setParallelSearchConnected] = useState(true);

  useEffect(() => {
    checkParallelSearch().then(setParallelSearchOk);
  }, []);

  async function checkParallelSearch(): Promise<boolean> {
    try {
      const res = await fetch("https://search.parallel.ai/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "tools/call",
          params: {
            name: "web_search",
            arguments: { query: "test", max_results: 1 }
          },
          id: 1
        }),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  const loading = parallelSearchOk === null;

  return (
    <div>
      <div className="mb-[22px]">
        <p className="text-[17px] font-semibold m-0">Connectors</p>
        <p className="text-xs text-ink-dim mt-0.5">Live reasoning tools called by the model during execution.</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
          <SkeletonCard label="Connection" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
          <ConnectorCard
            label="Parallel Search"
            status={!parallelSearchConnected ? "unreachable" : parallelSearchOk === true ? "connected" : parallelSearchOk === false ? "unreachable" : "unknown"}
            description="Checks live provider pricing pages to catch registry drift"
          >
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={() => setParallelSearchConnected(!parallelSearchConnected)}
                className="text-xs text-gold"
              >
                {parallelSearchConnected ? "Disconnect" : "Connect"}
              </button>
            </div>
          </ConnectorCard>
        </div>
      )}
    </div>
  );
}