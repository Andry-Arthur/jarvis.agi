"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiUrl } from "../lib/apiBase";
import type { EnvVarsPatchResponse, EnvVarsResponse } from "../types";

async function fetchEnvVars(): Promise<EnvVarsResponse> {
  const res = await fetch(apiUrl("/api/config/env-vars"));
  if (!res.ok) throw new Error("Failed to fetch env vars");
  return res.json();
}

async function patchEnvVars(vars: Record<string, string>): Promise<EnvVarsPatchResponse> {
  const res = await fetch(apiUrl("/api/config/env-vars"), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ vars }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to save settings");
  }
  return res.json();
}

export function useEnvVars() {
  return useQuery({
    queryKey: ["env-vars"],
    queryFn: fetchEnvVars,
    staleTime: 10_000,
  });
}

export function usePatchEnvVars() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: patchEnvVars,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["env-vars"] });
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      queryClient.invalidateQueries({ queryKey: ["config"] });
      queryClient.invalidateQueries({ queryKey: ["tools"] });
    },
  });
}

