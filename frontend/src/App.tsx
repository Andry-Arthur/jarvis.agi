import { Route, Routes } from "react-router-dom";
import { ProtectedLayout } from "./components/ProtectedLayout";
import { Dashboard } from "./pages/Dashboard";
import { Integrations } from "./pages/Integrations";
import { Onboarding } from "./pages/Onboarding";
import { Settings } from "./pages/Settings";
import { Tools } from "./pages/Tools";
import { useWebSocket } from "./hooks/useWebSocket";
import { useProviderStore } from "./store/provider";

export default function App() {
  const { status, messages, sendMessage, clearMessages, reconnectCount, isSpeaking } =
    useWebSocket();
  const provider = useProviderStore((s) => s.provider);

  const handleSend = (
    text: string,
    history: Array<{ role: string; content: string }>
  ) => {
    sendMessage(text, history, provider);
  };

  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route element={<ProtectedLayout onClearChat={clearMessages} />}>
        <Route
          path="/"
          element={
            <Dashboard
              messages={messages}
              status={status}
              reconnectCount={reconnectCount}
              isSpeaking={isSpeaking}
              onSend={handleSend}
            />
          }
        />
        <Route path="/integrations" element={<Integrations />} />
        <Route path="/tools" element={<Tools />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  );
}
