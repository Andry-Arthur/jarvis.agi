import { useEffect, useState } from "react";
import { IntegrationCard } from "../components/IntegrationCard";
import type { Integration } from "../types";

export function Integrations() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/integrations")
      .then((r) => r.json())
      .then((data) => setIntegrations(data.integrations ?? []))
      .catch(() => setError("Could not load integrations. Is the API server running?"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Integrations</h1>
        <p className="mt-1 text-sm text-gray-400">
          Configure your connected apps. Set credentials in <code className="rounded bg-gray-800 px-1 py-0.5 text-jarvis-300">.env</code> to enable them.
        </p>
      </div>

      {loading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-36 animate-pulse rounded-xl bg-gray-800" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {integrations.map((i) => (
            <IntegrationCard key={i.name} integration={i} />
          ))}
        </div>
      )}

      {/* Setup guide */}
      <div className="mt-8 rounded-xl border border-gray-700 bg-gray-800/50 p-5">
        <h2 className="mb-3 font-semibold text-gray-200">Quick Setup Guide</h2>
        <ol className="space-y-2 text-sm text-gray-400 list-decimal list-inside">
          <li>
            Copy <code className="rounded bg-gray-700 px-1 text-jarvis-300">.env.example</code> to{" "}
            <code className="rounded bg-gray-700 px-1 text-jarvis-300">.env</code>
          </li>
          <li>
            Add your API keys and tokens for each integration you want to use
          </li>
          <li>Restart the JARVIS API server</li>
          <li>Refresh this page — configured integrations will show as Connected</li>
        </ol>
      </div>
    </div>
  );
}
