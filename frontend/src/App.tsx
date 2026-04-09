import { Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Dashboard } from "./pages/Dashboard";
import { Integrations } from "./pages/Integrations";
import { Settings } from "./pages/Settings";
import { Tools } from "./pages/Tools";
import { useWebSocket } from "./hooks/useWebSocket";
import { useProviderStore } from "./store/provider";

export default function App() {
  const { status, messages, sendMessage, clearMessages, reconnectCount } = useWebSocket();
  const provider = useProviderStore((s) => s.provider);

  const handleSend = (
    text: string,
    history: Array<{ role: string; content: string }>
  ) => {
    sendMessage(text, history, provider);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      <Sidebar onClear={clearMessages} />

      <main className="flex flex-1 flex-col overflow-hidden">
        <Routes>
          <Route
            path="/"
            element={
              <Dashboard
                messages={messages}
                status={status}
                reconnectCount={reconnectCount}
                onSend={handleSend}
              />
            }
          />
          <Route path="/integrations" element={<Integrations />} />
          <Route path="/tools" element={<Tools />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
