import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, CheckCircle2, XCircle } from "lucide-react";
import { IntegrationCard } from "../components/IntegrationCard";
import { apiUrl } from "../lib/apiBase";
import type { Integration } from "../types";

async function fetchIntegrations(): Promise<Integration[]> {
  const res = await fetch(apiUrl("/api/integrations"));
  if (!res.ok) throw new Error("Failed to fetch integrations");
  const data = await res.json();
  return data.integrations ?? [];
}

const CATEGORIES = [
  "All",
  "Communication",
  "Productivity",
  "Media",
  "Social",
  "Automation",
  "System",
  "Memory",
  "Information",
  "Development",
  "Smart Home",
  "Finance",
];

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
    const matchesCategory = category === "All" || (i as { category?: string }).category === category;
    const matchesStatus = !showConnectedOnly || i.configured;
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const connectedCount = integrations.filter((i) => i.configured).length;

  return (
    <div className="flex-1 overflow-y-auto bg-hud-pane p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-fg">Integrations</h1>
          <p className="mt-1 text-sm text-muted">
            Configure connected services. Set credentials in{" "}
            <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-jarvis-700">
              .env
            </code>{" "}
            to enable them.
          </p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1.5 text-emerald-700">
            <CheckCircle2 className="h-4 w-4" />
            {connectedCount} connected
          </span>
          <span className="flex items-center gap-1.5 text-muted">
            <XCircle className="h-4 w-4" />
            {integrations.length - connectedCount} unconfigured
          </span>
        </div>
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-48 flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search integrations…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-3 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                category === cat
                  ? "bg-jarvis-600 text-white shadow-sm"
                  : "bg-surface-muted text-muted hover:bg-surface-muted/80 hover:text-fg"
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
              ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200"
              : "bg-surface-muted text-muted hover:text-fg"
          }`}
        >
          Connected only
        </button>

        <button
          onClick={() => refetch()}
          className="rounded-full bg-surface-muted px-3 py-1 text-xs font-medium text-muted transition-colors hover:bg-surface-muted/80 hover:text-fg"
        >
          Refresh
        </button>
      </div>

      {isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-44 animate-pulse rounded-xl bg-surface-muted" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Could not load integrations. Is the API server running?
        </div>
      )}

      {!isLoading && !error && (
        <>
          {filtered.length === 0 ? (
            <p className="py-12 text-center text-sm text-muted">
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

      <div className="mt-8 rounded-xl border border-border bg-surface/90 p-5 shadow-sm backdrop-blur-sm">
        <h2 className="mb-3 font-semibold text-fg">Quick Setup Guide</h2>
        <ol className="list-inside list-decimal space-y-2 text-sm text-muted">
          <li>
            Copy{" "}
            <code className="rounded border border-border bg-surface-muted px-1 text-jarvis-700">
              .env.example
            </code>{" "}
            to{" "}
            <code className="rounded border border-border bg-surface-muted px-1 text-jarvis-700">
              .env
            </code>
          </li>
          <li>Add the required env vars for each integration you want to use</li>
          <li>Restart the JARVIS API server</li>
          <li>Click Refresh — configured integrations will show as Connected</li>
        </ol>
      </div>
    </div>
  );
}
