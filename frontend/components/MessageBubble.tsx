"use client";

import {
  Bot,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Copy,
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
      className="rounded p-1 text-muted transition-colors hover:text-fg"
      title="Copy"
      type="button"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-600" />
      ) : (
        <Copy className="h-3.5 w-3.5" />
      )}
    </button>
  );
}

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const [argsExpanded, setArgsExpanded] = useState(false);
  const [resultExpanded, setResultExpanded] = useState(false);

  if (message.role === "tool_call") {
    const rawContent = message.content;
    const jsonMatch = rawContent.match(/\{[\s\S]*\}/);
    const argsJson = jsonMatch ? jsonMatch[0] : null;
    let parsedArgs: Record<string, unknown> | null = null;
    if (argsJson) {
      try {
        parsedArgs = JSON.parse(argsJson);
      } catch {
        // ignore
      }
    }

    return (
      <div className="flex items-start gap-2 py-1">
        <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-amber-100">
          <Wrench className="h-3 w-3 text-amber-700" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-muted">Tool call</span>
            <code className="rounded bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-900 ring-1 ring-amber-200/80">
              {message.toolName ?? "unknown"}
            </code>
            <span className="text-xs text-muted">{relativeTime(message.timestamp)}</span>
            {parsedArgs && (
              <button
                onClick={() => setArgsExpanded((v) => !v)}
                className="flex items-center gap-0.5 text-xs text-muted transition-colors hover:text-fg"
                type="button"
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
            <pre className="mt-1.5 overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-muted p-2 text-xs text-fg">
              {JSON.stringify(parsedArgs, null, 2)}
            </pre>
          )}
        </div>
      </div>
    );
  }

  if (message.role === "tool_result") {
    const content = message.content ?? "";
    const isTruncated = content.length > RESULT_TRUNCATE_CHARS;
    const displayContent =
      !resultExpanded && isTruncated ? content.slice(0, RESULT_TRUNCATE_CHARS) + "…" : content;

    return (
      <div className="mb-1 ml-7">
        <button
          onClick={() => setResultExpanded((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted transition-colors hover:text-fg"
          type="button"
        >
          {resultExpanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          <Terminal className="h-3 w-3" />
          <span>
            Result from <code className="text-fg">{message.toolName ?? "tool"}</code>
          </span>
          {isTruncated && (
            <span className="text-muted">
              ({resultExpanded ? "collapse" : `${content.length} chars`})
            </span>
          )}
        </button>
        {resultExpanded && (
          <div className="relative mt-1.5">
            <pre className="max-h-72 overflow-x-auto overflow-y-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-muted p-3 text-xs text-fg">
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

  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white ${
          isUser ? "bg-jarvis-700" : "bg-jarvis-600"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className="group relative max-w-[80%]">
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "rounded-tr-sm bg-jarvis-600 text-white shadow-sm"
              : "rounded-tl-sm border border-border bg-surface text-fg shadow-sm"
          }`}
        >
          {isUser ? (
            <span>{message.content}</span>
          ) : (
            <div className="prose prose-slate prose-sm max-w-none prose-p:my-1 prose-headings:text-fg prose-pre:border prose-pre:border-border prose-pre:bg-surface-muted prose-code:rounded prose-code:bg-surface-muted prose-code:px-1 prose-code:py-0.5 prose-code:text-jarvis-800 prose-code:before:content-none prose-code:after:content-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        <div className={`mt-1 flex items-center gap-2 text-xs ${isUser ? "flex-row-reverse" : ""}`}>
          <span className={isUser ? "text-jarvis-600/90" : "text-muted"}>
            {relativeTime(message.timestamp)}
          </span>
          {message.model && !isUser && (
            <span className="rounded-full bg-surface-muted px-1.5 py-0.5 text-muted">
              {message.model}
            </span>
          )}
          {!isUser && (
            <span className="opacity-0 transition-opacity group-hover:opacity-100">
              <CopyButton text={message.content} />
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

