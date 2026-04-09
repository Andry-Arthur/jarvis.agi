import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, CheckCircle2, XCircle } from "lucide-react";
import { IntegrationCard } from "../components/IntegrationCard";
import type { Integration } from "../types";

async function fetchIntegrations(): Promise<Integration[]> {
  const res = await fetch("/api/integrations");
  if (!res.ok) throw new Error("Failed to fetch integrations");
  const data = await res.json();
  return data.integrations ?? [];
}

const CATEGORIES = ["All", "Communication", "Productivity", "Media", "Social", "Automation", "System", "Memory", "Information", "Development", "Smart Home", "Finance"];

export function Integrations() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [showConnectedOnly, setShowConnectedOnly] = useState(false);

  const { data: integrations = [], isLoading, error, refetch } = useQuery({
    queryKey: ["integrations"],
    queryFn: fetchIntegrations,
    refetchInterval: 60_000,
  });

  const filtered = integrations.filter((i) => {
    const matchesSearch =
      !search ||
      i.name.toLowerCase().includes(search.toLowerCase()) ||
      (i.description ?? "").toLowerCase().includes(search.toLowerCase());
    const matchesCategory = category === "All" || (i as any).category === category;
    const matchesStatus = !showConnectedOnly || i.configured;
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const connectedCount = integrations.filter((i) => i.configured).length;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Integrations</h1>
          <p className="mt-1 text-sm text-gray-400">
            Configure connected services. Set credentials in{" "}
            <code className="rounded bg-gray-800 px-1 py-0.5 text-jarvis-300">.env</code> to enable them.
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1.5 text-green-400">
            <CheckCircle2 className="h-4 w-4" />
            {connectedCount} connected
          </span>
          <span className="flex items-center gap-1.5 text-gray-500">
            <XCircle className="h-4 w-4" />
            {integrations.length - connectedCount} unconfigured
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
          <input
            type="text"
            placeholder="Search integrations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 py-2 pl-9 pr-3 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-jarvis-600 transition-colors"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                category === cat
                  ? "bg-jarvis-600 text-white"
                  : "bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowConnectedOnly((v) => !v)}
          className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
            showConnectedOnly
              ? "bg-green-800/50 text-green-300"
              : "bg-gray-800 text-gray-400 hover:bg-gray-700"
          }`}
        >
          Connected only
        </button>

        <button
          onClick={() => refetch()}
          className="rounded-full px-3 py-1 text-xs font-medium bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-gray-200 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-44 animate-pulse rounded-xl bg-gray-800" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
          Could not load integrations. Is the API server running?
        </div>
      )}

      {/* Grid */}
      {!isLoading && !error && (
        <>
          {filtered.length === 0 ? (
            <p className="py-12 text-center text-sm text-gray-500">
              No integrations match your filters.
            </p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {filtered.map((i) => (
                <IntegrationCard key={i.name} integration={i} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Setup guide */}
      <div className="mt-8 rounded-xl border border-gray-700 bg-gray-800/50 p-5">
        <h2 className="mb-3 font-semibold text-gray-200">Quick Setup Guide</h2>
        <ol className="list-inside list-decimal space-y-2 text-sm text-gray-400">
          <li>
            Copy{" "}
            <code className="rounded bg-gray-700 px-1 text-jarvis-300">.env.example</code> to{" "}
            <code className="rounded bg-gray-700 px-1 text-jarvis-300">.env</code>
          </li>
          <li>Add the required env vars for each integration you want to use</li>
          <li>Restart the JARVIS API server</li>
          <li>Click Refresh — configured integrations will show as Connected</li>
        </ol>
      </div>
    </div>
  );
}
