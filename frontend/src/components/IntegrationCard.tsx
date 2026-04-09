import { useState } from "react";
import { CheckCircle2, XCircle, Copy, Check, ChevronDown, ChevronUp } from "lucide-react";
import type { Integration } from "../types";

interface Props {
  integration: Integration & {
    icon?: string;
    category?: string;
    env_vars?: string[];
    setup_hint?: string;
  };
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <button
      onClick={handleCopy}
      className="ml-1 rounded p-0.5 text-gray-500 hover:text-jarvis-300 transition-colors"
      title={`Copy ${text}`}
    >
      {copied ? <Check className="h-3 w-3 text-green-400" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

export function IntegrationCard({ integration }: Props) {
  const [expanded, setExpanded] = useState(false);
  const hasEnvVars = (integration.env_vars ?? []).length > 0;

  return (
    <div
      className={`rounded-xl border p-5 transition-all ${
        integration.configured
          ? "border-jarvis-700/50 bg-jarvis-900/20"
          : "border-gray-700 bg-gray-800/50"
      }`}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl leading-none">{integration.icon ?? "🔌"}</span>
          <div>
            <h3 className="font-semibold text-gray-100 leading-tight">{integration.name}</h3>
            {integration.category && (
              <span className="text-xs text-gray-500">{integration.category}</span>
            )}
          </div>
        </div>
        {integration.configured ? (
          <CheckCircle2 className="h-5 w-5 text-green-400 shrink-0" />
        ) : (
          <XCircle className="h-5 w-5 text-gray-600 shrink-0" />
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-gray-400 leading-snug">
        {integration.description ?? `Integration with ${integration.name}`}
      </p>

      {/* Status badge */}
      <div className="mt-3">
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${
            integration.configured
              ? "bg-green-900/40 text-green-400"
              : "bg-gray-700 text-gray-400"
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              integration.configured ? "bg-green-400" : "bg-gray-500"
            }`}
          />
          {integration.configured ? "Connected" : "Not configured"}
        </span>
      </div>

      {/* Expandable env vars section */}
      {(hasEnvVars || integration.setup_hint) && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Setup info
          </button>

          {expanded && (
            <div className="mt-2 space-y-2">
              {integration.setup_hint && (
                <p className="text-xs text-gray-400">{integration.setup_hint}</p>
              )}
              {hasEnvVars && (
                <div className="space-y-1">
                  {integration.env_vars!.map((v) => (
                    <div
                      key={v}
                      className="flex items-center justify-between rounded bg-gray-900/60 px-2 py-1"
                    >
                      <code className="text-xs text-jarvis-300">{v}</code>
                      <CopyButton text={v} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
