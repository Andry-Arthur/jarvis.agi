import { ArrowUp, ChevronDown, Loader2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Message, Provider } from "../types";
import { VoiceWave } from "./VoiceWave";
import { MessageBubble } from "./MessageBubble";
import { useVoice } from "../hooks/useVoice";
import type { ConnectionStatus } from "../types";

interface Props {
  messages: Message[];
  status: ConnectionStatus;
  provider: Provider;
  onSend: (text: string, history: Array<{ role: string; content: string }>) => void;
}

export function ChatPanel({ messages, status, provider, onSend }: Props) {
  const [input, setInput] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const prevMsgCount = useRef(messages.length);

  // Auto-scroll on new messages
  useEffect(() => {
    if (messages.length !== prevMsgCount.current) {
      prevMsgCount.current = messages.length;
      listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [messages]);

  // Detect when assistant finishes responding
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last?.role === "assistant" || last?.role === "tool_result") {
      setIsWaiting(false);
    }
  }, [messages]);

  const buildHistory = useCallback(() => {
    return messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role as string, content: m.content }));
  }, [messages]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text || isWaiting || status !== "connected") return;
    setInput("");
    setIsWaiting(true);
    onSend(text, buildHistory());
  }, [input, isWaiting, status, onSend, buildHistory]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const { state: voiceState, volume, toggleRecording } = useVoice({
    onTranscript: (text) => {
      setInput(text);
      // Auto-send after voice transcription
      setTimeout(() => {
        setIsWaiting(true);
        onSend(text, buildHistory());
        setInput("");
      }, 100);
    },
  });

  const connected = status === "connected";

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Status bar */}
      <div className="flex items-center justify-between border-b border-gray-800 px-4 py-2">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              connected
                ? "bg-green-400"
                : status === "connecting"
                ? "animate-pulse bg-yellow-400"
                : "bg-red-400"
            }`}
          />
          <span className="text-xs text-gray-400 capitalize">{status}</span>
        </div>
        <span className="text-xs text-gray-500">{provider}</span>
      </div>

      {/* Message list */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-3 scrollbar-none"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 text-5xl">🤖</div>
            <h2 className="text-xl font-semibold text-gray-300">
              Hey, I'm JARVIS
            </h2>
            <p className="mt-2 max-w-sm text-sm text-gray-500">
              Your free, self-hosted AI agent. Ask me anything, or use the mic
              to talk to me.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {isWaiting && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking…
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-800 p-3">
        <div className="flex items-end gap-2 rounded-2xl border border-gray-700 bg-gray-800 px-3 py-2 focus-within:border-jarvis-600 transition-colors">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={connected ? "Message JARVIS…" : "Connecting…"}
            disabled={!connected || isWaiting}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-gray-100 placeholder-gray-500 outline-none disabled:opacity-50"
            style={{ maxHeight: "120px" }}
            onInput={(e) => {
              const el = e.currentTarget;
              el.style.height = "auto";
              el.style.height = `${el.scrollHeight}px`;
            }}
          />
          <div className="flex shrink-0 items-center gap-1.5 pb-0.5">
            <VoiceWave
              state={voiceState}
              volume={volume}
              onClick={toggleRecording}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || !connected || isWaiting}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-jarvis-600 text-white transition-colors hover:bg-jarvis-500 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          </div>
        </div>
        <p className="mt-1.5 text-center text-xs text-gray-600">
          JARVIS can make mistakes. Verify important info.
        </p>
      </div>
    </div>
  );
}
