import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Save,
  RefreshCw,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { useEnvVars, usePatchEnvVars } from "../hooks/useEnvVars";

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

async function reloadConfig() {
  const res = await fetch("/api/config/reload", { method: "POST" });
  if (!res.ok) throw new Error("Reload failed");
  return res.json();
}

// ── Reusable field components ────────────────────────────────────────────────

function TextField({
  label,
  envKey,
  value,
  onChange,
  placeholder,
  hint,
}: {
  label: string;
  envKey: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <label className="text-sm font-medium text-fg">{label}</label>
        <code className="text-xs text-muted">{envKey}</code>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
      />
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

function SecretField({
  label,
  envKey,
  value,
  onChange,
  placeholder,
  isSet,
  maskedValue,
}: {
  label: string;
  envKey: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  isSet: boolean;
  maskedValue: string | null;
}) {
  const [show, setShow] = useState(false);

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-fg">{label}</label>
          <code className="text-xs text-muted">{envKey}</code>
        </div>
        {isSet && (
          <span className="flex items-center gap-1 text-xs text-emerald-700">
            <CheckCircle2 className="h-3 w-3" />
            Set ({maskedValue})
          </span>
        )}
      </div>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={isSet ? "Leave blank to keep existing" : placeholder}
          className="w-full rounded-lg border border-border bg-surface py-2 pl-3 pr-10 text-sm text-fg outline-none transition-colors placeholder:text-muted focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-fg"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function SelectField({
  label,
  envKey,
  value,
  onChange,
  options,
  hint,
}: {
  label: string;
  envKey: string;
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  hint?: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center gap-2">
        <label className="text-sm font-medium text-fg">{label}</label>
        <code className="text-xs text-muted">{envKey}</code>
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg outline-none transition-colors focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

// ── Main Settings page ────────────────────────────────────────────────────────

export function Settings() {
  const { data: envVarsData } = useEnvVars();
  const { data: config, isLoading: configLoading, error: configError } = useQuery({
    queryKey: ["config"],
    queryFn: fetchConfig,
  });

  const { mutate: patchEnvVars, isPending: isSaving, isError: saveError, error: saveErrorMsg, isSuccess: saveOk, data: saveResult } = usePatchEnvVars();

  // Local form state — keyed by env var name
  const [fields, setFields] = useState<Record<string, string>>({});
  const [reloadMsg, setReloadMsg] = useState<string | null>(null);
  const [isReloading, setIsReloading] = useState(false);

  // Pre-populate non-secret fields from live config
  useEffect(() => {
    if (!config) return;
    setFields((prev) => ({
      DEFAULT_LLM: config.default_llm,
      OLLAMA_MODEL: config.ollama_model,
      WAKE_WORD_MODEL: config.wake_word_model,
      TTS_VOICE: config.tts_voice,
      // Don't overwrite if user already typed something
      OLLAMA_BASE_URL: prev.OLLAMA_BASE_URL ?? "",
      WHISPER_MODEL: prev.WHISPER_MODEL ?? "",
      // Secret fields start empty (never pre-filled)
      OPENAI_API_KEY: prev.OPENAI_API_KEY ?? "",
      ANTHROPIC_API_KEY: prev.ANTHROPIC_API_KEY ?? "",
    }));
  }, [config]);

  const setField = (key: string) => (value: string) =>
    setFields((prev) => ({ ...prev, [key]: value }));

  const handleSave = () => {
    const toSave: Record<string, string> = {};
    for (const [key, value] of Object.entries(fields)) {
      if (value !== "") toSave[key] = value;
    }
    patchEnvVars(toSave);
  };

  const handleManualReload = async () => {
    setIsReloading(true);
    try {
      const res = await reloadConfig();
      setReloadMsg(res.message);
    } catch {
      setReloadMsg("Reload failed — check server logs.");
    } finally {
      setIsReloading(false);
      setTimeout(() => setReloadMsg(null), 5000);
    }
  };

  const ev = (key: string) => envVarsData?.vars[key];

  return (
    <div className="flex-1 overflow-y-auto bg-hud-pane p-6">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-fg">Settings</h1>
          <p className="mt-1 text-sm text-muted">
            Configure JARVIS directly from the UI. Changes are saved to your{" "}
            <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-jarvis-700">
              .env
            </code>{" "}
            file and applied immediately.{" "}
            <Link to="/onboarding?review=1" className="text-jarvis-600 hover:underline">
              Open the setup guide
            </Link>{" "}
            anytime.
          </p>
        </div>
        <button
          onClick={handleManualReload}
          disabled={isReloading}
          className="flex shrink-0 items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg transition-colors hover:bg-surface-muted disabled:opacity-60"
        >
          <RefreshCw className={`h-4 w-4 ${isReloading ? "animate-spin" : ""}`} />
          Reload only
        </button>
      </div>

      {/* Save feedback */}
      {saveOk && saveResult && (
        <div className="mb-5 flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          {saveResult.message}
        </div>
      )}
      {saveError && (
        <div className="mb-5 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {(saveErrorMsg as Error)?.message}
        </div>
      )}
      {reloadMsg && (
        <div className="mb-5 rounded-lg border border-sky-200 bg-sky-50 p-3 text-sm text-sky-900">
          {reloadMsg}
        </div>
      )}

      {configLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl bg-surface-muted" />
          ))}
        </div>
      )}

      {configError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Could not load config. Is the API server running?
        </div>
      )}

      {!configLoading && (
        <div className="max-w-2xl space-y-8">

          {/* ── LLM ── */}
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
              Language Model
            </h2>
            <div className="space-y-4 rounded-xl border border-border bg-surface/95 p-5 shadow-sm backdrop-blur-sm">
              <SelectField
                label="Default Provider"
                envKey="DEFAULT_LLM"
                value={fields.DEFAULT_LLM ?? "openai"}
                onChange={setField("DEFAULT_LLM")}
                options={[
                  { value: "openai", label: "OpenAI (GPT-4o)" },
                  { value: "anthropic", label: "Anthropic (Claude)" },
                  { value: "ollama", label: "Ollama (Local)" },
                ]}
              />
              <SecretField
                label="OpenAI API Key"
                envKey="OPENAI_API_KEY"
                value={fields.OPENAI_API_KEY ?? ""}
                onChange={setField("OPENAI_API_KEY")}
                placeholder="sk-..."
                isSet={ev("OPENAI_API_KEY")?.is_set ?? false}
                maskedValue={ev("OPENAI_API_KEY")?.masked_value ?? null}
              />
              <SecretField
                label="Anthropic API Key"
                envKey="ANTHROPIC_API_KEY"
                value={fields.ANTHROPIC_API_KEY ?? ""}
                onChange={setField("ANTHROPIC_API_KEY")}
                placeholder="sk-ant-..."
                isSet={ev("ANTHROPIC_API_KEY")?.is_set ?? false}
                maskedValue={ev("ANTHROPIC_API_KEY")?.masked_value ?? null}
              />
              <TextField
                label="Ollama Base URL"
                envKey="OLLAMA_BASE_URL"
                value={fields.OLLAMA_BASE_URL ?? ""}
                onChange={setField("OLLAMA_BASE_URL")}
                placeholder="http://localhost:11434"
                hint="Default: http://localhost:11434"
              />
              <TextField
                label="Ollama Model"
                envKey="OLLAMA_MODEL"
                value={fields.OLLAMA_MODEL ?? ""}
                onChange={setField("OLLAMA_MODEL")}
                placeholder="qwen2.5:1.5b"
                hint="Any model served by your local Ollama instance."
              />
            </div>
          </section>

          {/* ── Voice ── */}
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
              Voice
            </h2>
            <div className="space-y-4 rounded-xl border border-border bg-surface/95 p-5 shadow-sm backdrop-blur-sm">
              <SelectField
                label="Whisper Model Size"
                envKey="WHISPER_MODEL"
                value={fields.WHISPER_MODEL || "base"}
                onChange={setField("WHISPER_MODEL")}
                options={[
                  { value: "tiny", label: "tiny — fastest, least accurate" },
                  { value: "base", label: "base — recommended" },
                  { value: "small", label: "small" },
                  { value: "medium", label: "medium" },
                  { value: "large-v3", label: "large-v3 — best, slowest" },
                ]}
                hint="Larger models are more accurate but use more memory."
              />
              <TextField
                label="TTS Voice"
                envKey="TTS_VOICE"
                value={fields.TTS_VOICE ?? ""}
                onChange={setField("TTS_VOICE")}
                placeholder="en-US-AriaNeural"
                hint="Any Microsoft Edge TTS voice. See /api/voice/voices for options."
              />
              <SelectField
                label="Wake Word Model"
                envKey="WAKE_WORD_MODEL"
                value={fields.WAKE_WORD_MODEL || "hey_jarvis"}
                onChange={setField("WAKE_WORD_MODEL")}
                options={[
                  { value: "hey_jarvis", label: "hey_jarvis" },
                  { value: "hey_mycroft", label: "hey_mycroft" },
                  { value: "alexa", label: "alexa" },
                ]}
              />
            </div>
          </section>

          {/* ── Save button ── */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center gap-2 rounded-lg bg-jarvis-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-jarvis-500 disabled:opacity-60 transition-colors"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              {isSaving ? "Saving…" : "Save Settings"}
            </button>
            <p className="text-xs text-muted">
              Writes to <code className="text-fg">.env</code> and reloads the agent automatically.
            </p>
          </div>

          {/* ── Integration credential status (read-only) ── */}
          {config && (
            <section>
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">
                Integration Credentials
              </h2>
              <p className="mb-3 text-xs text-muted">
                Configure credentials per-integration on the{" "}
                <a href="/integrations" className="text-jarvis-600 hover:underline">
                  Integrations page
                </a>
                .
              </p>
              <div className="divide-y divide-border rounded-xl border border-border bg-surface/95 px-4 shadow-sm backdrop-blur-sm">
                {Object.entries(config.integrations_env).map(([key, isSet]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between py-2.5"
                  >
                    <span className="text-sm capitalize text-fg">
                      {key.replace(/_/g, " ")}
                    </span>
                    {isSet ? (
                      <span className="flex items-center gap-1 text-xs text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Configured
                      </span>
                    ) : (
                      <span className="text-xs text-muted">Not set</span>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
