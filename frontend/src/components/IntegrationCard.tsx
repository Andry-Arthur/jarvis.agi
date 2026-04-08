import { CheckCircle, XCircle } from "lucide-react";
import type { Integration } from "../types";

interface Props {
  integration: Integration;
}

const ICONS: Record<string, string> = {
  Gmail: "📧",
  Discord: "💬",
  YouTube: "▶️",
  Instagram: "📸",
};

const DESCRIPTIONS: Record<string, string> = {
  Gmail: "Read, search, and send emails from your Gmail account.",
  Discord: "Send and receive messages from Discord channels and DMs.",
  YouTube: "Search videos and retrieve transcripts.",
  Instagram: "Read and send Instagram direct messages.",
};

export function IntegrationCard({ integration }: Props) {
  return (
    <div
      className={`rounded-xl border p-5 transition-colors ${
        integration.configured
          ? "border-jarvis-700/50 bg-jarvis-900/20"
          : "border-gray-700 bg-gray-800/50"
      }`}
    >
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{ICONS[integration.name] ?? "🔌"}</span>
          <h3 className="font-semibold text-gray-100">{integration.name}</h3>
        </div>
        {integration.configured ? (
          <CheckCircle className="h-5 w-5 text-green-400 shrink-0" />
        ) : (
          <XCircle className="h-5 w-5 text-gray-600 shrink-0" />
        )}
      </div>
      <p className="text-sm text-gray-400">
        {DESCRIPTIONS[integration.name] ?? "Integration with " + integration.name}
      </p>
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
    </div>
  );
}
