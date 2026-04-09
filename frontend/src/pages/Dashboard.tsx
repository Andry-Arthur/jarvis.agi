import { ChatPanel } from "../components/ChatPanel";
import { StatsBar } from "../components/StatsBar";
import { useProviderStore } from "../store/provider";
import type { Provider } from "../types";
import type { ConnectionStatus, Message } from "../types";

interface Props {
  messages: Message[];
  status: ConnectionStatus;
  reconnectCount: number;
  onSend: (text: string, history: Array<{ role: string; content: string }>) => void;
}

export function Dashboard({ messages, status, reconnectCount, onSend }: Props) {
  const { provider, setProvider } = useProviderStore();

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

      <StatsBar reconnectCount={reconnectCount} />

      <ChatPanel
        messages={messages}
        status={status}
        provider={provider}
        onSend={onSend}
      />
    </div>
  );
}
