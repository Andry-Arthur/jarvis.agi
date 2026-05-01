"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
  Loader2,
  RefreshCw,
  Save,
} from "lucide-react";
import { useEnvVars, usePatchEnvVars } from "../../hooks/useEnvVars";
import { apiUrl } from "../../lib/apiBase";

interface ConfigData {
  default_llm: string;
  ollama_model: string;
  memory_enabled: boolean;
  wake_word_model: string;
  tts_voice: string;
  multimodal_enabled: boolean;
  integrations_env: Record<string, boolean>;
}

async function fetchConfig(): Promise<ConfigData> {
  const res = await fetch(apiUrl("/api/config"));
  if (!res.ok) throw new Error("Failed to fetch config");
  return res.json();
}

async function reloadConfig() {
  const res = await fetch(apiUrl("/api/config/reload"), { method: "POST" });
  if (!res.ok) throw new Error("Reload failed");
  return res.json();
}

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

export function Settings() {
  const { data: envVarsData } = useEnvVars();
  const { data: config, isLoading: configLoading, error: configError } = useQuery({
    queryKey: ["config"],
    queryFn: fetchConfig,
  });

  const {
    mutate: patchEnvVars,
    isPending: isSaving,
    isError: saveError,
    error: saveErrorMsg,
    isSuccess: saveOk,
    data: saveResult,
  } = usePatchEnvVars();

  const [fields, setFields] = useState<Record<string, string>>({});
  const [reloadMsg, setReloadMsg] = useState<string | null>(null);
  const [isReloading, setIsReloading] = useState(false);

  useEffect(() => {
    if (!config) return;
    setFields((prev) => ({
      DEFAULT_LLM: config.default_llm,
      OLLAMA_MODEL: config.ollama_model,
      WAKE_WORD_MODEL: config.wake_word_model,
      TTS_VOICE: config.tts_voice,
      MULTIMODAL_ENABLED: config.multimodal_enabled ? "true" : "false",
      OLLAMA_BASE_URL: prev.OLLAMA_BASE_URL ?? "",
      WHISPER_MODEL: prev.WHISPER_MODEL ?? "",
      MULTIMODAL_FUSION_WINDOW_S: prev.MULTIMODAL_FUSION_WINDOW_S ?? "",
      MULTIMODAL_MAX_CONTEXT_CHARS: prev.MULTIMODAL_MAX_CONTEXT_CHARS ?? "",
      MULTIMODAL_BROADCAST_HZ: prev.MULTIMODAL_BROADCAST_HZ ?? "",
      MULTIMODAL_WS_URL: prev.MULTIMODAL_WS_URL ?? "",
      MULTIMODAL_MIC_ENABLED: prev.MULTIMODAL_MIC_ENABLED ?? "",
      MULTIMODAL_EMOTION_INTERVAL_S: prev.MULTIMODAL_EMOTION_INTERVAL_S ?? "",
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
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-fg">Settings</h1>
          <p className="mt-1 text-sm text-muted">
            Configure JARVIS directly from the UI. Changes are saved to your{" "}
            <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-jarvis-700">
              .env
            </code>{" "}
            file and applied immediately.{" "}
            <Link href="/onboarding?review=1" className="text-jarvis-600 hover:underline">
              Open the setup guide
            </Link>{" "}
            anytime.
          </p>
        </div>
        <button
          onClick={handleManualReload}
          disabled={isReloading}
          className="flex shrink-0 items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg transition-colors hover:bg-surface-muted disabled:opacity-60"
          type="button"
        >
          <RefreshCw className={`h-4 w-4 ${isReloading ? "animate-spin" : ""}`} />
          Reload only
        </button>
      </div>

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
        <div className="mb-5 rounded-lg border border-border bg-surface p-3 text-sm text-fg">
          {reloadMsg}
        </div>
      )}

      {configLoading && (
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading config…
        </div>
      )}
      {configError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Could not load config. Is the API server running?
        </div>
      )}

      {!configLoading && !configError && (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="space-y-4 rounded-xl border border-border bg-surface/90 p-5 shadow-sm backdrop-blur-sm">
            <h2 className="font-semibold text-fg">Core</h2>
            <SelectField
              label="Default LLM"
              envKey="DEFAULT_LLM"
              value={fields.DEFAULT_LLM ?? ""}
              onChange={setField("DEFAULT_LLM")}
              options={[
                { value: "openai", label: "OpenAI" },
                { value: "anthropic", label: "Anthropic" },
                { value: "ollama", label: "Ollama" },
              ]}
            />
            <TextField
              label="Ollama model"
              envKey="OLLAMA_MODEL"
              value={fields.OLLAMA_MODEL ?? ""}
              onChange={setField("OLLAMA_MODEL")}
              placeholder="llama3.1"
            />
            <TextField
              label="Ollama base URL"
              envKey="OLLAMA_BASE_URL"
              value={fields.OLLAMA_BASE_URL ?? ""}
              onChange={setField("OLLAMA_BASE_URL")}
              placeholder="http://localhost:11434"
            />
          </div>

          <div className="space-y-4 rounded-xl border border-border bg-surface/90 p-5 shadow-sm backdrop-blur-sm">
            <h2 className="font-semibold text-fg">Keys</h2>
            <SecretField
              label="OpenAI API key"
              envKey="OPENAI_API_KEY"
              value={fields.OPENAI_API_KEY ?? ""}
              onChange={setField("OPENAI_API_KEY")}
              placeholder="sk-..."
              isSet={ev("OPENAI_API_KEY")?.is_set ?? false}
              maskedValue={ev("OPENAI_API_KEY")?.masked_value ?? null}
            />
            <SecretField
              label="Anthropic API key"
              envKey="ANTHROPIC_API_KEY"
              value={fields.ANTHROPIC_API_KEY ?? ""}
              onChange={setField("ANTHROPIC_API_KEY")}
              placeholder="sk-ant-..."
              isSet={ev("ANTHROPIC_API_KEY")?.is_set ?? false}
              maskedValue={ev("ANTHROPIC_API_KEY")?.masked_value ?? null}
            />
          </div>

          <div className="space-y-4 rounded-xl border border-border bg-surface/90 p-5 shadow-sm backdrop-blur-sm">
            <h2 className="font-semibold text-fg">Voice</h2>
            <TextField
              label="Wake word model"
              envKey="WAKE_WORD_MODEL"
              value={fields.WAKE_WORD_MODEL ?? ""}
              onChange={setField("WAKE_WORD_MODEL")}
              placeholder="alexa"
            />
            <TextField
              label="Whisper model"
              envKey="WHISPER_MODEL"
              value={fields.WHISPER_MODEL ?? ""}
              onChange={setField("WHISPER_MODEL")}
              placeholder="base"
            />
            <TextField
              label="TTS voice"
              envKey="TTS_VOICE"
              value={fields.TTS_VOICE ?? ""}
              onChange={setField("TTS_VOICE")}
              placeholder="en-US-JennyNeural"
            />
          </div>

          <div className="space-y-4 rounded-xl border border-border bg-surface/90 p-5 shadow-sm backdrop-blur-sm lg:col-span-2">
            <h2 className="font-semibold text-fg">Multimodal (desktop)</h2>
            <p className="text-xs text-muted">
              Enable fusion of webcam/microphone cues into chat. Run{" "}
              <code className="rounded bg-surface-muted px-1">python -m jarvis multimodal</code> in a
              second terminal while the API is up. Raw video/audio are not stored server-side.
            </p>
            <SelectField
              label="Multimodal context injection"
              envKey="MULTIMODAL_ENABLED"
              value={fields.MULTIMODAL_ENABLED ?? "false"}
              onChange={setField("MULTIMODAL_ENABLED")}
              options={[
                { value: "false", label: "Off" },
                { value: "true", label: "On" },
              ]}
              hint="Requires desktop bridge + API; see GET /api/multimodal/status"
            />
            <TextField
              label="Fusion window (seconds)"
              envKey="MULTIMODAL_FUSION_WINDOW_S"
              value={fields.MULTIMODAL_FUSION_WINDOW_S ?? ""}
              onChange={setField("MULTIMODAL_FUSION_WINDOW_S")}
              placeholder={ev("MULTIMODAL_FUSION_WINDOW_S")?.placeholder ?? "20"}
            />
            <TextField
              label="Max multimodal context chars"
              envKey="MULTIMODAL_MAX_CONTEXT_CHARS"
              value={fields.MULTIMODAL_MAX_CONTEXT_CHARS ?? ""}
              onChange={setField("MULTIMODAL_MAX_CONTEXT_CHARS")}
              placeholder={ev("MULTIMODAL_MAX_CONTEXT_CHARS")?.placeholder ?? "1200"}
            />
            <TextField
              label="UI broadcast rate (Hz)"
              envKey="MULTIMODAL_BROADCAST_HZ"
              value={fields.MULTIMODAL_BROADCAST_HZ ?? ""}
              onChange={setField("MULTIMODAL_BROADCAST_HZ")}
              placeholder={ev("MULTIMODAL_BROADCAST_HZ")?.placeholder ?? "5"}
            />
            <TextField
              label="Desktop bridge WebSocket URL"
              envKey="MULTIMODAL_WS_URL"
              value={fields.MULTIMODAL_WS_URL ?? ""}
              onChange={setField("MULTIMODAL_WS_URL")}
              placeholder={ev("MULTIMODAL_WS_URL")?.placeholder ?? "ws://127.0.0.1:8000/ws"}
            />
            <SelectField
              label="Mic emotion capture"
              envKey="MULTIMODAL_MIC_ENABLED"
              value={fields.MULTIMODAL_MIC_ENABLED ?? "true"}
              onChange={setField("MULTIMODAL_MIC_ENABLED")}
              options={[
                { value: "true", label: "On" },
                { value: "false", label: "Off" },
              ]}
            />
            <TextField
              label="Mic emotion interval (seconds)"
              envKey="MULTIMODAL_EMOTION_INTERVAL_S"
              value={fields.MULTIMODAL_EMOTION_INTERVAL_S ?? ""}
              onChange={setField("MULTIMODAL_EMOTION_INTERVAL_S")}
              placeholder={ev("MULTIMODAL_EMOTION_INTERVAL_S")?.placeholder ?? "2.0"}
            />
          </div>
        </div>
      )}

      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-jarvis-600 px-4 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-jarvis-500 disabled:opacity-50"
          type="button"
        >
          {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {isSaving ? "Saving…" : "Save settings"}
        </button>
      </div>
    </div>
  );
}

