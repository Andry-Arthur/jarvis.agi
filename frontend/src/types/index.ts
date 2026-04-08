export type Role = "user" | "assistant" | "tool_call" | "tool_result";

export interface Message {
  id: string;
  role: Role;
  content: string;
  model?: string;
  toolName?: string;
  timestamp: Date;
}

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export type Provider = "openai" | "anthropic" | "ollama";

export interface Integration {
  name: string;
  configured: boolean;
  icon?: string;
  description?: string;
}

export interface WsInboundMessage {
  type: "tool_call" | "tool_result" | "done" | "audio" | "error" | "pong";
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  model?: string;
  data?: string;
  mime?: string;
}

export interface WsOutboundMessage {
  type: "message" | "ping";
  content?: string;
  history?: Array<{ role: string; content: string }>;
  provider?: Provider;
}
