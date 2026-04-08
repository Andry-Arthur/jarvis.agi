import { useState } from "react";
import { Save } from "lucide-react";

interface SettingField {
  key: string;
  label: string;
  type: "text" | "password" | "select";
  placeholder?: string;
  options?: { value: string; label: string }[];
  hint?: string;
  envVar: string;
}

const SETTINGS: SettingField[] = [
  {
    key: "default_llm",
    label: "Default LLM Provider",
    type: "select",
    options: [
      { value: "openai", label: "OpenAI (GPT-4o)" },
      { value: "anthropic", label: "Anthropic (Claude)" },
      { value: "ollama", label: "Ollama (Local)" },
    ],
    envVar: "DEFAULT_LLM",
  },
  {
    key: "openai_key",
    label: "OpenAI API Key",
    type: "password",
    placeholder: "sk-...",
    hint: "From platform.openai.com/api-keys",
    envVar: "OPENAI_API_KEY",
  },
  {
    key: "anthropic_key",
    label: "Anthropic API Key",
    type: "password",
    placeholder: "sk-ant-...",
    hint: "From console.anthropic.com",
    envVar: "ANTHROPIC_API_KEY",
  },
  {
    key: "ollama_url",
    label: "Ollama Base URL",
    type: "text",
    placeholder: "http://localhost:11434",
    hint: "Default: http://localhost:11434",
    envVar: "OLLAMA_BASE_URL",
  },
  {
    key: "whisper_model",
    label: "Whisper Model Size",
    type: "select",
    options: [
      { value: "tiny", label: "tiny (fastest, least accurate)" },
      { value: "base", label: "base (recommended)" },
      { value: "small", label: "small" },
      { value: "medium", label: "medium" },
      { value: "large-v3", label: "large-v3 (best, slowest)" },
    ],
    hint: "Larger models are more accurate but require more memory.",
    envVar: "WHISPER_MODEL",
  },
  {
    key: "tts_voice",
    label: "TTS Voice",
    type: "text",
    placeholder: "en-US-GuyNeural",
    hint: "Any Microsoft Edge TTS voice name. See /api/voice/voices for a full list.",
    envVar: "TTS_VOICE",
  },
];

export function Settings() {
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-100">Settings</h1>
        <p className="mt-1 text-sm text-gray-400">
          Configuration is managed via your{" "}
          <code className="rounded bg-gray-800 px-1 py-0.5 text-jarvis-300">.env</code> file.
          Restart the server after changes.
        </p>
      </div>

      <div className="max-w-2xl space-y-6">
        {SETTINGS.map((field) => (
          <div key={field.key}>
            <label className="mb-1 block text-sm font-medium text-gray-300">
              {field.label}
              <span className="ml-2 text-xs font-normal text-gray-500">
                {field.envVar}
              </span>
            </label>

            {field.type === "select" ? (
              <select className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 outline-none focus:border-jarvis-600 transition-colors">
                {field.options?.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={field.type}
                placeholder={field.placeholder}
                className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 outline-none focus:border-jarvis-600 transition-colors"
              />
            )}

            {field.hint && (
              <p className="mt-1 text-xs text-gray-500">{field.hint}</p>
            )}
          </div>
        ))}

        <div className="rounded-lg border border-yellow-800/50 bg-yellow-900/10 p-4 text-sm text-yellow-300">
          <strong>Note:</strong> Settings shown here are read-only UI references.
          Edit your <code className="rounded bg-yellow-900/30 px-1">.env</code> file directly
          and restart the server to apply changes.
        </div>

        <button
          onClick={handleSave}
          className="flex items-center gap-2 rounded-lg bg-jarvis-600 px-4 py-2 text-sm font-medium text-white hover:bg-jarvis-500 transition-colors"
        >
          <Save className="h-4 w-4" />
          {saved ? "Noted!" : "Save reference"}
        </button>
      </div>
    </div>
  );
}
