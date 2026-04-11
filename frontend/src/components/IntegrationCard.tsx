import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Eye,
  EyeOff,
  Save,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import type { Integration } from "../types";
import { useEnvVars, usePatchEnvVars } from "../hooks/useEnvVars";

interface Props {
  integration: Integration & {
    icon?: string;
    category?: string;
    env_vars?: string[];
    setup_hint?: string;
  };
}

function EnvVarField({
  envKey,
  label,
  secret,
  isSet,
  maskedValue,
  placeholder,
  value,
  onChange,
}: {
  envKey: string;
  label: string;
  secret: boolean;
  isSet: boolean;
  maskedValue: string | null;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const [show, setShow] = useState(false);
  const inputType = secret && !show ? "password" : "text";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="text-xs font-medium text-fg">{label}</label>
        <code className="text-xs text-muted">{envKey}</code>
      </div>
      <div className="relative">
        <input
          type={inputType}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={
            isSet && maskedValue ? `Current: ${maskedValue}` : placeholder || `Enter ${envKey}`
          }
          className="w-full rounded-lg border border-border bg-surface py-1.5 pl-3 pr-8 text-xs text-fg outline-none transition-colors placeholder:text-muted focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
        />
        {secret && (
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-fg"
          >
            {show ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
      {isSet && (
        <p className="mt-0.5 text-xs text-emerald-700">
          Already set ({maskedValue})
        </p>
      )}
    </div>
  );
}

export function IntegrationCard({ integration }: Props) {
  const [configOpen, setConfigOpen] = useState(false);
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [saveSuccess, setSaveSuccess] = useState(false);

  const { data: envVarsData } = useEnvVars();
  const { mutate: patchEnvVars, isPending, isError, error } = usePatchEnvVars();

  const envVarKeys = integration.env_vars ?? [];
  const hasEnvVars = envVarKeys.length > 0;

  const handleFieldChange = (key: string, value: string) => {
    setFieldValues((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => {
    const toSave: Record<string, string> = {};
    for (const key of envVarKeys) {
      const v = fieldValues[key];
      if (v !== undefined && v !== "") {
        toSave[key] = v;
      }
    }
    if (Object.keys(toSave).length === 0) return;

    patchEnvVars(toSave, {
      onSuccess: () => {
        setFieldValues({});
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
      },
    });
  };

  const isDirty = envVarKeys.some(
    (k) => fieldValues[k] !== undefined && fieldValues[k] !== ""
  );

  return (
    <div
      className={`rounded-xl border transition-all shadow-sm ${
        integration.configured
          ? "border-jarvis-300/80 bg-accent-muted/60"
          : "border-border bg-surface/95 backdrop-blur-sm"
      }`}
    >
      <div className="p-5">
        <div className="mb-3 flex items-start justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl leading-none">{integration.icon ?? "🔌"}</span>
            <div>
              <h3 className="font-semibold leading-tight text-fg">{integration.name}</h3>
              {integration.category && (
                <span className="text-xs text-muted">{integration.category}</span>
              )}
            </div>
          </div>
          {integration.configured ? (
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
          ) : (
            <XCircle className="h-5 w-5 shrink-0 text-muted" />
          )}
        </div>

        <p className="text-sm leading-snug text-muted">
          {integration.description ?? `Integration with ${integration.name}`}
        </p>

        <div className="mt-3 flex items-center justify-between gap-2">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
              saveSuccess
                ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200"
                : integration.configured
                ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200"
                : "bg-surface-muted text-muted"
            }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                saveSuccess || integration.configured ? "bg-emerald-500" : "bg-muted"
              }`}
            />
            {saveSuccess ? "Saved!" : integration.configured ? "Connected" : "Not configured"}
          </span>

          {hasEnvVars && (
            <button
              onClick={() => setConfigOpen((v) => !v)}
              className={`flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors ${
                configOpen
                  ? "bg-accent-muted text-jarvis-800 ring-1 ring-jarvis-200/80"
                  : "bg-surface-muted text-fg hover:bg-surface-muted/80"
              }`}
            >
              Configure
              {configOpen ? (
                <ChevronUp className="h-3 w-3" />
              ) : (
                <ChevronDown className="h-3 w-3" />
              )}
            </button>
          )}
        </div>
      </div>

      {configOpen && hasEnvVars && (
        <div className="border-t border-border px-5 pb-5 pt-4">
          {integration.setup_hint && (
            <p className="mb-3 text-xs text-muted">{integration.setup_hint}</p>
          )}

          <div className="space-y-3">
            {envVarKeys.map((key) => {
              const meta = envVarsData?.vars[key];
              return (
                <EnvVarField
                  key={key}
                  envKey={key}
                  label={meta?.label ?? key}
                  secret={meta?.secret ?? true}
                  isSet={meta?.is_set ?? false}
                  maskedValue={meta?.masked_value ?? null}
                  placeholder={meta?.placeholder ?? ""}
                  value={fieldValues[key] ?? ""}
                  onChange={(v) => handleFieldChange(key, v)}
                />
              );
            })}
          </div>

          {isError && (
            <div className="mt-3 flex items-start gap-1.5 rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-800">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              {(error as Error)?.message ?? "Save failed"}
            </div>
          )}

          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={handleSave}
              disabled={!isDirty || isPending}
              className="flex items-center gap-1.5 rounded-lg bg-jarvis-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-jarvis-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Save className="h-3.5 w-3.5" />
              )}
              {isPending ? "Saving…" : "Save & Reconnect"}
            </button>
            <p className="text-xs text-muted">Leave blank to keep existing value</p>
          </div>
        </div>
      )}
    </div>
  );
}
