import { useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import type { Provider } from "../types";
import type { ConnectionStatus, Message } from "../types";

interface Props {
  messages: Message[];
  status: ConnectionStatus;
  onSend: (text: string, history: Array<{ role: string; content: string }>) => void;
}

export function Dashboard({ messages, status, onSend }: Props) {
  const [provider, setProvider] = useState<Provider>("openai");

  const handleSend = (text: string, history: Array<{ role: string; content: string }>) => {
    onSend(text, history);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Provider selector */}
      <div className="flex items-center gap-2 border-b border-gray-800 bg-gray-900 px-4 py-2">
        <span className="text-xs text-gray-500">Model:</span>
        {(["openai", "anthropic", "ollama"] as Provider[]).map((p) => (
          <button
            key={p}
            onClick={() => setProvider(p)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${
              provider === p
                ? "bg-jarvis-600 text-white"
                : "text-gray-400 hover:bg-gray-700 hover:text-gray-200"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <ChatPanel
        messages={messages}
        status={status}
        provider={provider}
        onSend={handleSend}
      />
    </div>
  );
}
