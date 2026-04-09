import {
  Bot,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Copy,
  Check,
  Terminal,
  User,
  Wrench,
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";

const RESULT_TRUNCATE_CHARS = 400;

function relativeTime(date: Date): string {
  const diffMs = Date.now() - date.getTime();
  const diffS = Math.floor(diffMs / 1000);
  if (diffS < 60) return "just now";
  const diffM = Math.floor(diffS / 60);
  if (diffM < 60) return `${diffM}m ago`;
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
      className="rounded p-1 text-gray-600 hover:text-gray-300 transition-colors"
      title="Copy"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
    </button>
  );
}

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const [argsExpanded, setArgsExpanded] = useState(false);
  const [resultExpanded, setResultExpanded] = useState(false);

  /* ── Tool call ── */
  if (message.role === "tool_call") {
    // Try to extract JSON args from content like: Calling **tool_name**\n{...}
    const rawContent = message.content;
    const jsonMatch = rawContent.match(/\{[\s\S]*\}/);
    const argsJson = jsonMatch ? jsonMatch[0] : null;
    let parsedArgs: Record<string, unknown> | null = null;
    if (argsJson) {
      try {
        parsedArgs = JSON.parse(argsJson);
      } catch {
        /* ignore */
      }
    }

    return (
      <div className="flex items-start gap-2 py-1">
        <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-yellow-900/40">
          <Wrench className="h-3 w-3 text-yellow-400" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-gray-500">Tool call</span>
            <code className="rounded bg-yellow-900/20 px-1.5 py-0.5 text-xs font-medium text-yellow-300">
              {message.toolName ?? "unknown"}
            </code>
            <span className="text-xs text-gray-600">{relativeTime(message.timestamp)}</span>
            {parsedArgs && (
              <button
                onClick={() => setArgsExpanded((v) => !v)}
                className="flex items-center gap-0.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
              >
                args
                {argsExpanded ? (
                  <ChevronUp className="h-3 w-3" />
                ) : (
                  <ChevronDown className="h-3 w-3" />
                )}
              </button>
            )}
          </div>
          {argsExpanded && parsedArgs && (
            <pre className="mt-1.5 rounded-lg bg-gray-900 p-2 text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap border border-gray-800">
              {JSON.stringify(parsedArgs, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  /* ── Tool result ── */
  if (message.role === "tool_result") {
    const content = message.content ?? "";
    const isTruncated = content.length > RESULT_TRUNCATE_CHARS;
    const displayContent =
      !resultExpanded && isTruncated
        ? content.slice(0, RESULT_TRUNCATE_CHARS) + "…"
        : content;

    return (
      <div className="ml-7 mb-1">
        <button
          onClick={() => setResultExpanded((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {resultExpanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          <Terminal className="h-3 w-3" />
          <span>
            Result from{" "}
            <code className="text-gray-400">{message.toolName ?? "tool"}</code>
          </span>
          {isTruncated && (
            <span className="text-gray-600">
              ({resultExpanded ? "collapse" : `${content.length} chars`})
            </span>
          )}
        </button>
        {resultExpanded && (
          <div className="relative mt-1.5">
            <pre className="rounded-lg border border-gray-800 bg-gray-900 p-3 text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap max-h-72 overflow-y-auto">
              {displayContent}
            </pre>
            <div className="absolute right-2 top-2">
              <CopyButton text={content} />
            </div>
          </div>
        )}
      </div>
    );
  }

  /* ── User / Assistant ── */
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white ${
          isUser ? "bg-gray-600" : "bg-jarvis-600"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Bubble */}
      <div className={`group relative max-w-[80%] ${isUser ? "" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "rounded-tr-sm bg-jarvis-600 text-white"
              : "rounded-tl-sm bg-gray-800 text-gray-100"
          }`}
        >
          {isUser ? (
            <span>{message.content}</span>
          ) : (
            <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-pre:bg-gray-900 prose-code:text-jarvis-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Footer: time + model + copy */}
        <div
          className={`mt-1 flex items-center gap-2 text-xs ${
            isUser ? "flex-row-reverse" : "flex-row"
          }`}
        >
          <span className={isUser ? "text-jarvis-200" : "text-gray-600"}>
            {relativeTime(message.timestamp)}
          </span>
          {message.model && !isUser && (
            <span className="rounded-full bg-gray-800 px-1.5 py-0.5 text-gray-500">
              {message.model}
            </span>
          )}
          {!isUser && (
            <span className="opacity-0 group-hover:opacity-100 transition-opacity">
              <CopyButton text={message.content} />
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
