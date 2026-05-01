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
  category?: string;
  env_vars?: string[];
  setup_hint?: string;
}

export interface EnvVarStatus {
  label: string;
  section: string;
  secret: boolean;
  is_set: boolean;
  masked_value: string | null;
  placeholder: string;
}

export interface EnvVarsResponse {
  vars: Record<string, EnvVarStatus>;
}

export interface EnvVarsPatchResponse {
  saved: string[];
  cleared: string[];
  reloaded: boolean;
  providers: string[];
  message: string;
}

export interface MultimodalStateSummary {
  event_count?: number;
  last_gesture?: string | null;
  last_emotion?: string | null;
  attention?: Record<string, unknown>;
  window_s?: number;
  calibration?: string | null;
  ts?: number;
}

export interface WsInboundMessage {
  type:
    | "tool_call"
    | "tool_result"
    | "done"
    | "audio"
    | "error"
    | "pong"
    | "notification"
    | "multimodal_state"
    | "chunk"
    | "plan_event";
  content?: string;
  name?: string;
  args?: Record<string, unknown>;
  result?: string;
  model?: string;
  data?: string;
  mime?: string;
  title?: string;
  body?: string;
  kind?: string;
  timestamp?: string;
  delta?: string;
  event_count?: number;
  last_gesture?: string | null;
  last_emotion?: string | null;
  attention?: Record<string, unknown>;
  window_s?: number;
  calibration?: string | null;
  ts?: number;
}

export interface WsOutboundMessage {
  type:
    | "message"
    | "ping"
    | "multimodal_batch"
    | "multimodal_event"
    | "multimodal_control";
  content?: string;
  history?: Array<{ role: string; content: string }>;
  provider?: Provider;
  events?: Array<Record<string, unknown>>;
  kind?: string;
  action?: string;
  message?: string;
}

