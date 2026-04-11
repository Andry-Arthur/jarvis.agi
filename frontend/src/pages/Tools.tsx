import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, ChevronDown, ChevronUp, Wrench } from "lucide-react";
import { apiUrl } from "../lib/apiBase";

interface ToolParam {
  type: string;
  description?: string;
  enum?: string[];
}

interface ToolSchema {
  name: string;
  description?: string;
  parameters?: {
    type: string;
    properties?: Record<string, ToolParam>;
    required?: string[];
  };
}

async function fetchTools(): Promise<ToolSchema[]> {
  const res = await fetch(apiUrl("/api/integrations/tools"));
  if (!res.ok) throw new Error("Failed to fetch tools");
  const data = await res.json();
  return data.tools ?? [];
}

function ParamBadge({ required }: { required: boolean }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-xs font-medium ${
        required ? "bg-red-100 text-red-800 ring-1 ring-red-200" : "bg-surface-muted text-muted"
      }`}
    >
      {required ? "required" : "optional"}
    </span>
  );
}

function ToolCard({ tool }: { tool: ToolSchema }) {
  const [expanded, setExpanded] = useState(false);
  const properties = tool.parameters?.properties ?? {};
  const required = tool.parameters?.required ?? [];
  const paramCount = Object.keys(properties).length;

  return (
    <div className="rounded-xl border border-border bg-surface/95 p-4 shadow-sm transition-colors hover:border-jarvis-300/60">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Wrench className="h-4 w-4 shrink-0 text-jarvis-600" />
            <code className="truncate font-mono text-sm font-semibold text-jarvis-800">{tool.name}</code>
          </div>
          {tool.description && (
            <p className="mt-1.5 text-sm leading-snug text-muted">{tool.description}</p>
          )}
        </div>
        {paramCount > 0 && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex shrink-0 items-center gap-1 rounded-full bg-surface-muted px-2.5 py-1 text-xs text-fg transition-colors hover:bg-surface-muted/80"
          >
            {paramCount} param{paramCount !== 1 ? "s" : ""}
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
        )}
      </div>

      {expanded && paramCount > 0 && (
        <div className="mt-3 divide-y divide-border overflow-hidden rounded-lg border border-border bg-surface-muted/50">
          {Object.entries(properties).map(([name, param]) => (
            <div key={name} className="px-3 py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <code className="font-mono text-xs text-amber-800">{name}</code>
                <span className="text-xs text-muted">{param.type}</span>
                <ParamBadge required={required.includes(name)} />
              </div>
              {param.description && <p className="mt-1 text-xs text-muted">{param.description}</p>}
              {param.enum && (
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {param.enum.map((v) => (
                    <code
                      key={v}
                      className="rounded border border-border bg-surface px-1.5 py-0.5 text-xs text-muted"
                    >
                      {v}
                    </code>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function Tools() {
  const [search, setSearch] = useState("");

  const { data: tools = [], isLoading, error, refetch } = useQuery({
    queryKey: ["tools"],
    queryFn: fetchTools,
    refetchInterval: 60_000,
  });

  const filtered = tools.filter(
    (t) =>
      !search ||
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      (t.description ?? "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="flex-1 overflow-y-auto bg-hud-pane p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-fg">Tools</h1>
          <p className="mt-1 text-sm text-muted">All tools currently registered and available to the agent.</p>
        </div>
        {tools.length > 0 && (
          <span className="rounded-full bg-accent-muted px-3 py-1 text-sm font-medium text-jarvis-800 ring-1 ring-jarvis-200/80">
            {tools.length} tools
          </span>
        )}
      </div>

      <div className="mb-5 flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search tools…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-3 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
          />
        </div>
        <button
          onClick={() => refetch()}
          className="rounded-lg border border-border bg-surface px-3 py-2 text-xs text-muted transition-colors hover:bg-surface-muted hover:text-fg"
        >
          Refresh
        </button>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-surface-muted" />
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Could not load tools. Make sure the API server is running and an agent is initialized.
        </div>
      )}

      {!isLoading && !error && tools.length === 0 && (
        <div className="py-16 text-center">
          <Wrench className="mx-auto mb-3 h-10 w-10 text-muted" />
          <p className="text-sm text-muted">
            No tools registered yet. Start the API server to load integrations.
          </p>
        </div>
      )}

      {!isLoading && !error && filtered.length > 0 && (
        <div className="space-y-3">
          {filtered.map((t) => (
            <ToolCard key={t.name} tool={t} />
          ))}
        </div>
      )}

      {!isLoading && !error && tools.length > 0 && filtered.length === 0 && (
        <p className="py-12 text-center text-sm text-muted">No tools match your search.</p>
      )}
    </div>
  );
}
