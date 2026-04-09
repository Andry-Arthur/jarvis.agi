import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCw, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";

interface ConfigData {
  default_llm: string;
  ollama_model: string;
  memory_enabled: boolean;
  wake_word_model: string;
  tts_voice: string;
  integrations_env: Record<string, boolean>;
}

async function fetchConfig(): Promise<ConfigData> {
  const res = await fetch("/api/config");
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

async function reloadConfig(): Promise<{ status: string; providers: string[]; message: string }> {
  const res = await fetch("/api/config/reload", { method: "POST" });
  if (!res.ok) throw new Error("Reload failed");
  return res.json();
}

interface FieldRowProps {
  label: string;
  envVar: string;
  value?: string | boolean;
  hint?: string;
  isSet?: boolean;
}

function FieldRow({ label, envVar, value, hint, isSet }: FieldRowProps) {
  const displayValue =
    value === undefined || value === null
      ? undefined
      : typeof value === "boolean"
      ? value
        ? "true"
        : "false"
      : String(value);

  return (
    <div className="flex items-start gap-4 py-3 border-b border-gray-800 last:border-b-0">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-200">{label}</span>
          <code className="text-xs text-gray-500">{envVar}</code>
        </div>
        {hint && <p className="mt-0.5 text-xs text-gray-600">{hint}</p>}
      </div>
      <div className="shrink-0 flex items-center gap-2">
        {displayValue !== undefined ? (
          <span className="rounded bg-gray-800 px-2 py-0.5 font-mono text-xs text-jarvis-300">
            {displayValue}
          </span>
        ) : isSet !== undefined ? (
          isSet ? (
            <span className="flex items-center gap-1 text-xs text-green-400">
              <CheckCircle2 className="h-3.5 w-3.5" /> Set
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-gray-500">
              <XCircle className="h-3.5 w-3.5" /> Not set
            </span>
          )
        ) : null}
      </div>
    </div>
  );
}

export function Settings() {
  const queryClient = useQueryClient();

  const { data: config, isLoading, error } = useQuery({
    queryKey: ["config"],
    queryFn: fetchConfig,
  });

  const {
    mutate: reload,
    isPending: isReloading,
    isSuccess: reloadOk,
    isError: reloadFailed,
    data: reloadData,
    error: reloadError,
  } = useMutation({
    mutationFn: reloadConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["config"] });
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["tools"] });
    },
  });

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-100">Settings</h1>
          <p className="mt-1 text-sm text-gray-400">
            Live view of current runtime configuration. Edit your{" "}
            <code className="rounded bg-gray-800 px-1 py-0.5 text-jarvis-300">.env</code> file,
            then click Reload Config to apply without restarting.
          </p>
        </div>

        <button
          onClick={() => reload()}
          disabled={isReloading}
          className="flex shrink-0 items-center gap-2 rounded-lg bg-jarvis-600 px-4 py-2 text-sm font-medium text-white hover:bg-jarvis-500 disabled:opacity-60 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${isReloading ? "animate-spin" : ""}`} />
          {isReloading ? "Reloading…" : "Reload Config"}
        </button>
      </div>

      {/* Reload feedback */}
      {reloadOk && reloadData && (
        <div className="mb-5 flex items-start gap-2 rounded-lg border border-green-800 bg-green-900/20 p-3 text-sm text-green-300">
          <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
          {reloadData.message}
        </div>
      )}
      {reloadFailed && (
        <div className="mb-5 flex items-start gap-2 rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
          Reload failed: {(reloadError as Error)?.message}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 animate-pulse rounded-xl bg-gray-800" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-4 text-sm text-red-400">
          Could not load config. Is the API server running?
        </div>
      )}

      {config && (
        <div className="max-w-2xl space-y-6">
          {/* LLM Settings */}
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Language Model
            </h2>
            <div className="rounded-xl border border-gray-700 bg-gray-800/50 px-4 divide-y divide-gray-800">
              <FieldRow
                label="Default LLM Provider"
                envVar="DEFAULT_LLM"
                value={config.default_llm}
                hint="Which provider to use when none is specified."
              />
              <FieldRow
                label="Ollama Model"
                envVar="OLLAMA_MODEL"
                value={config.ollama_model}
                hint="Model name served by your local Ollama instance."
              />
            </div>
          </section>

          {/* Voice Settings */}
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Voice
            </h2>
            <div className="rounded-xl border border-gray-700 bg-gray-800/50 px-4 divide-y divide-gray-800">
              <FieldRow
                label="Wake Word Model"
                envVar="WAKE_WORD_MODEL"
                value={config.wake_word_model}
                hint="openWakeWord model used for wake word detection."
              />
              <FieldRow
                label="TTS Voice"
                envVar="TTS_VOICE"
                value={config.tts_voice}
                hint="Microsoft Edge TTS voice name. See /api/voice/voices for options."
              />
            </div>
          </section>

          {/* Memory */}
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Memory
            </h2>
            <div className="rounded-xl border border-gray-700 bg-gray-800/50 px-4">
              <FieldRow
                label="Memory Enabled"
                envVar="MEMORY_ENABLED"
                value={config.memory_enabled ? "true" : "false"}
                hint="Whether ChromaDB-backed conversation memory is active."
              />
            </div>
          </section>

          {/* Integration env flags */}
          <section>
            <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Integration Credentials
            </h2>
            <div className="rounded-xl border border-gray-700 bg-gray-800/50 px-4 divide-y divide-gray-800">
              {Object.entries(config.integrations_env).map(([key, isSet]) => (
                <FieldRow
                  key={key}
                  label={key
                    .replace(/_/g, " ")
                    .replace(/\b\w/g, (c) => c.toUpperCase())}
                  envVar={key.toUpperCase()}
                  isSet={isSet}
                />
              ))}
            </div>
          </section>

          <div className="rounded-lg border border-yellow-800/50 bg-yellow-900/10 p-4 text-sm text-yellow-300">
            <strong>Tip:</strong> After editing{" "}
            <code className="rounded bg-yellow-900/30 px-1">.env</code>, use{" "}
            <strong>Reload Config</strong> above to apply changes without a full server restart.
            Some changes (like voice pipeline) may still require a restart.
          </div>
        </div>
      )}
    </div>
  );
}
