"use client";

import { useProviderStore } from "../store/provider";
import { useWebSocket } from "../hooks/useWebSocket";
import { ProtectedShell } from "../components/ProtectedShell";
import { Dashboard } from "../components/pages/Dashboard";

export default function HomePage() {
  const {
    status,
    messages,
    sendMessage,
    clearMessages,
    reconnectCount,
    isSpeaking,
    multimodal,
  } = useWebSocket();
  const provider = useProviderStore((s) => s.provider);

  const handleSend = (text: string, history: Array<{ role: string; content: string }>) => {
    sendMessage(text, history, provider);
  };

  return (
    <ProtectedShell onClearChat={clearMessages}>
      <Dashboard
        messages={messages}
        status={status}
        reconnectCount={reconnectCount}
        isSpeaking={isSpeaking}
        multimodal={multimodal}
        onSend={handleSend}
      />
    </ProtectedShell>
  );
}

