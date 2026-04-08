import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ConnectionStatus,
  Message,
  Provider,
  WsInboundMessage,
} from "../types";

let msgCounter = 0;
function uid() {
  return `msg-${Date.now()}-${++msgCounter}`;
}

const WS_URL = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000/ws";

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [messages, setMessages] = useState<Message[]>([]);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      // Keepalive ping every 25 s
      pingTimer.current = setInterval(() => {
        ws.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: "ping" }));
      }, 25_000);
    };

    ws.onclose = () => {
      setStatus("disconnected");
      if (pingTimer.current) clearInterval(pingTimer.current);
      // Auto-reconnect after 3 s
      setTimeout(connect, 3_000);
    };

    ws.onerror = () => setStatus("error");

    ws.onmessage = (evt) => {
      const data: WsInboundMessage = JSON.parse(evt.data);

      if (data.type === "pong") return;

      if (data.type === "audio" && data.data) {
        const blob = new Blob(
          [Uint8Array.from(atob(data.data), (c) => c.charCodeAt(0))],
          { type: data.mime ?? "audio/mpeg" }
        );
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play().catch(() => {});
        audio.onended = () => URL.revokeObjectURL(url);
        return;
      }

      if (data.type === "tool_call") {
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: "tool_call",
            content: `Calling **${data.name}**`,
            toolName: data.name,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      if (data.type === "tool_result") {
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: "tool_result",
            content: data.result ?? "",
            toolName: data.name,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      if (data.type === "done") {
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: "assistant",
            content: data.content ?? "",
            model: data.model,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      if (data.type === "error") {
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: "assistant",
            content: `⚠️ Error: ${data.content}`,
            timestamp: new Date(),
          },
        ]);
      }
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (pingTimer.current) clearInterval(pingTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendMessage = useCallback(
    (text: string, history: Array<{ role: string; content: string }>, provider?: Provider) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

      // Optimistically add user message
      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "user", content: text, timestamp: new Date() },
      ]);

      wsRef.current.send(
        JSON.stringify({ type: "message", content: text, history, provider })
      );
    },
    []
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return { status, messages, sendMessage, clearMessages, connect };
}
