"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ConnectionStatus,
  Message,
  MultimodalStateSummary,
  Provider,
  WsInboundMessage,
} from "../types";

let msgCounter = 0;
function uid() {
  return `msg-${Date.now()}-${++msgCounter}`;
}

function defaultWsUrl(): string {
  if (typeof window === "undefined") return "ws://localhost:8000/ws";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws`;
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [messages, setMessages] = useState<Message[]>([]);
  const [reconnectCount, setReconnectCount] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [multimodal, setMultimodal] = useState<MultimodalStateSummary | null>(null);
  const speakingCountRef = useRef(0);
  const pingTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const adjustSpeaking = useCallback((delta: number) => {
    speakingCountRef.current += delta;
    if (speakingCountRef.current < 0) speakingCountRef.current = 0;
    setIsSpeaking(speakingCountRef.current > 0);
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus("connecting");
    const ws = new WebSocket(defaultWsUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      pingTimer.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 25_000);
    };

    ws.onclose = () => {
      setStatus("disconnected");
      if (pingTimer.current) clearInterval(pingTimer.current);
      setReconnectCount((c) => c + 1);
      setTimeout(connect, 3_000);
    };

    ws.onerror = () => setStatus("error");

    ws.onmessage = (evt) => {
      const data: WsInboundMessage = JSON.parse(evt.data);

      if (data.type === "pong") return;

      if (data.type === "multimodal_state") {
        setMultimodal({
          event_count: data.event_count,
          last_gesture: data.last_gesture ?? null,
          last_emotion: data.last_emotion ?? null,
          attention: data.attention,
          window_s: data.window_s,
          calibration: data.calibration ?? null,
          ts: typeof data.ts === "number" ? data.ts : undefined,
        });
        return;
      }

      if (data.type === "notification") {
        const title = data.title ?? "Notification";
        const body = data.body ?? "";
        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: "assistant",
            content: `🔔 **${title}**\n\n${body}`,
            timestamp: new Date(),
          },
        ]);
        return;
      }

      if (data.type === "audio" && data.data) {
        const blob = new Blob([Uint8Array.from(atob(data.data), (c) => c.charCodeAt(0))], {
          type: data.mime ?? "audio/mpeg",
        });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        adjustSpeaking(1);
        const cleanup = () => {
          URL.revokeObjectURL(url);
          adjustSpeaking(-1);
        };
        audio.onended = cleanup;
        audio.onerror = cleanup;
        audio.play().catch(() => cleanup());
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
  }, [adjustSpeaking]);

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

      setMessages((prev) => [...prev, { id: uid(), role: "user", content: text, timestamp: new Date() }]);

      wsRef.current.send(JSON.stringify({ type: "message", content: text, history, provider }));
    },
    []
  );

  const clearMessages = useCallback(() => setMessages([]), []);

  return {
    status,
    messages,
    sendMessage,
    clearMessages,
    connect,
    reconnectCount,
    isSpeaking,
    multimodal,
  };
}

