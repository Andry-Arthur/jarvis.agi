import { Bot, ChevronDown, ChevronRight, Terminal, User, Wrench } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const [expanded, setExpanded] = useState(false);

  if (message.role === "tool_call") {
    return (
      <div className="flex items-start gap-2 py-1">
        <Wrench className="mt-0.5 h-4 w-4 shrink-0 text-yellow-500" />
        <span className="text-sm text-yellow-400">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </span>
      </div>
    );
  }

  if (message.role === "tool_result") {
    return (
      <div className="ml-6 mb-1">
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          {expanded ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
          <Terminal className="h-3 w-3" />
          <span>Tool result from {message.toolName}</span>
        </button>
        {expanded && (
          <pre className="mt-1 rounded bg-gray-800 p-2 text-xs text-gray-300 overflow-x-auto whitespace-pre-wrap">
            {message.content}
          </pre>
        )}
      </div>
    );
  }

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
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
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
        <div
          className={`mt-1 text-xs ${
            isUser ? "text-jarvis-200" : "text-gray-500"
          }`}
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
          {message.model && !isUser && (
            <span className="ml-2 opacity-60">{message.model}</span>
          )}
        </div>
      </div>
    </div>
  );
}
