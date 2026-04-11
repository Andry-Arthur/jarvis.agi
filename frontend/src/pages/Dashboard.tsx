import { ChatPanel } from "../components/ChatPanel";
import { StatsBar } from "../components/StatsBar";
import { useProviderStore } from "../store/provider";
import type { Provider } from "../types";
import type { ConnectionStatus, Message } from "../types";

interface Props {
  messages: Message[];
  status: ConnectionStatus;
  reconnectCount: number;
  isSpeaking: boolean;
  onSend: (text: string, history: Array<{ role: string; content: string }>) => void;
}

export function Dashboard({
  messages,
  status,
  reconnectCount,
  isSpeaking,
  onSend,
}: Props) {
  const { provider, setProvider } = useProviderStore();

  return (
    <div className="flex flex-1 flex-col overflow-hidden bg-hud-pane">
      {/* Provider selector */}
      <div className="flex items-center gap-2 border-b border-border bg-surface/80 px-4 py-2 backdrop-blur-sm">
        <span className="text-xs text-muted">Model:</span>
        {(["openai", "anthropic", "ollama"] as Provider[]).map((p) => (
          <button
            key={p}
            onClick={() => setProvider(p)}
            className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${
              provider === p
                ? "bg-jarvis-600 text-white shadow-sm"
                : "text-muted hover:bg-surface-muted hover:text-fg"
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
        isSpeaking={isSpeaking}
        onSend={onSend}
      />
    </div>
  );
}
