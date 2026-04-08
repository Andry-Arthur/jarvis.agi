import { Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/Sidebar";
import { Dashboard } from "./pages/Dashboard";
import { Integrations } from "./pages/Integrations";
import { Settings } from "./pages/Settings";
import { useWebSocket } from "./hooks/useWebSocket";
import type { Provider } from "./types";

export default function App() {
  const { status, messages, sendMessage, clearMessages } = useWebSocket();

  const handleSend = (
    text: string,
    history: Array<{ role: string; content: string }>
  ) => {
    const provider = (localStorage.getItem("jarvis_provider") as Provider) ?? "openai";
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
                onSend={handleSend}
              />
            }
          />
          <Route path="/integrations" element={<Integrations />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
