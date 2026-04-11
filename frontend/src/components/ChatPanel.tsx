import { ArrowUp, Loader2 } from "lucide-react";
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
  isSpeaking: boolean;
  onSend: (text: string, history: Array<{ role: string; content: string }>) => void;
}

export function ChatPanel({
  messages,
  status,
  provider,
  isSpeaking,
  onSend,
}: Props) {
  const [input, setInput] = useState("");
  const [isWaiting, setIsWaiting] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const prevMsgCount = useRef(messages.length);
  const historyRef = useRef<Array<{ role: string; content: string }>>([]);

  const buildHistory = useCallback(() => {
    return messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role as string, content: m.content }));
  }, [messages]);

  useEffect(() => {
    historyRef.current = buildHistory();
  }, [buildHistory]);

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
      if (!text || status !== "connected" || isWaiting) return;
      setIsWaiting(true);
      onSend(text, historyRef.current);
    },
  });

  const connected = status === "connected";
  const composerStatus = !connected
    ? null
    : voiceState === "recording"
    ? "Listening…"
    : voiceState === "processing"
    ? "Transcribing…"
    : isSpeaking
    ? "Playing reply…"
    : null;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Status bar */}
      <div className="flex items-center justify-between border-b border-border bg-surface/60 px-4 py-2 backdrop-blur-sm">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                connected
                  ? "bg-emerald-500"
                  : status === "connecting"
                  ? "animate-pulse bg-amber-400"
                  : "bg-red-500"
              }`}
            />
            <span className="text-xs text-muted capitalize">{status}</span>
          </div>
          {composerStatus && (
            <span className="truncate text-xs font-medium text-jarvis-600">{composerStatus}</span>
          )}
        </div>
        <span className="shrink-0 text-xs text-muted">{provider}</span>
      </div>

      {/* Message list */}
      <div
        ref={listRef}
        className="flex-1 space-y-3 overflow-y-auto px-4 py-4 scrollbar-none"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div
              className="mb-6 flex h-24 w-24 items-center justify-center rounded-full border-2 border-jarvis-400/40 bg-accent-muted shadow-[0_0_40px_rgba(26,140,245,0.15)]"
              aria-hidden
            >
              <div className="h-14 w-14 rounded-full border border-jarvis-500/50" />
            </div>
            <h2 className="text-xl font-semibold text-fg">Hey, I&apos;m JARVIS</h2>
            <p className="mt-2 max-w-sm text-sm text-muted">
              Your free, self-hosted AI agent. Ask me anything, or use the mic to talk to me.
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {isWaiting && (
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking…
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="border-t border-border bg-surface/90 p-3 backdrop-blur-sm">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface px-3 py-2 shadow-sm transition-colors focus-within:border-jarvis-400 focus-within:ring-1 focus-within:ring-jarvis-400/30">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={connected ? "Message JARVIS…" : "Connecting…"}
            disabled={!connected || isWaiting}
            rows={1}
            className="flex-1 resize-none bg-transparent text-sm text-fg placeholder:text-muted outline-none disabled:opacity-50"
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
              isSpeaking={isSpeaking}
              disabled={!connected || isWaiting || voiceState === "processing"}
              onClick={toggleRecording}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || !connected || isWaiting}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-jarvis-600 text-white transition-colors hover:bg-jarvis-500 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          </div>
        </div>
        <p className="mt-1.5 text-center text-xs text-muted">
          JARVIS can make mistakes. Verify important info.
        </p>
      </div>
    </div>
  );
}
