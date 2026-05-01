"use client";

import { useQuery } from "@tanstack/react-query";
import { Camera, Mic, Plug, RefreshCw, Sparkles, Wrench } from "lucide-react";
import { apiUrl } from "../lib/apiBase";
import type { Integration, MultimodalStateSummary } from "../types";

interface Props {
  reconnectCount: number;
  multimodal?: MultimodalStateSummary | null;
}

async function fetchIntegrations(): Promise<Integration[]> {
  const res = await fetch(apiUrl("/api/integrations"));
  if (!res.ok) throw new Error("fetch failed");
  const data = await res.json();
  return data.integrations ?? [];
}

async function fetchTools(): Promise<unknown[]> {
  const res = await fetch(apiUrl("/api/integrations/tools"));
  if (!res.ok) throw new Error("fetch failed");
  const data = await res.json();
  return data.tools ?? [];
}

export function StatsBar({ reconnectCount, multimodal }: Props) {
  const { data: integrations = [] } = useQuery({
    queryKey: ["integrations"],
    queryFn: fetchIntegrations,
    refetchInterval: 30_000,
  });

  const { data: tools = [] } = useQuery({
    queryKey: ["tools"],
    queryFn: fetchTools,
    refetchInterval: 30_000,
  });

  const connectedCount = integrations.filter((i) => i.configured).length;

  const gesture =
    multimodal?.last_gesture != null && multimodal.last_gesture !== ""
      ? String(multimodal.last_gesture)
      : "—";
  const emotion =
    multimodal?.last_emotion != null && multimodal.last_emotion !== ""
      ? String(multimodal.last_emotion)
      : "—";

  const stats = [
    {
      icon: Plug,
      value: integrations.length > 0 ? `${connectedCount}/${integrations.length}` : "—",
      label: "integrations",
    },
    {
      icon: Wrench,
      value: tools.length > 0 ? String(tools.length) : "—",
      label: "tools",
    },
    {
      icon: Camera,
      value: gesture,
      label: "gesture",
    },
    {
      icon: Mic,
      value: emotion,
      label: "tone",
    },
    ...(multimodal != null && multimodal.event_count != null && multimodal.event_count > 0
      ? [
          {
            icon: Sparkles,
            value: String(multimodal.event_count),
            label: "mm_events",
          },
        ]
      : []),
    ...(reconnectCount > 0 ? [{ icon: RefreshCw, value: String(reconnectCount), label: "reconnects" }] : []),
  ];

  return (
    <div className="flex items-center gap-5 border-b border-border bg-surface-muted/80 px-4 py-1.5 backdrop-blur-sm">
      {stats.map(({ icon: Icon, value, label }) => (
        <div key={label} className="flex items-center gap-1.5 text-xs text-muted">
          <Icon className="h-3.5 w-3.5 shrink-0 text-jarvis-600/80" />
          <span className="font-medium text-fg">{value}</span>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

