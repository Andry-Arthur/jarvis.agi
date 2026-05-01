"use client";

import {
  ArrowLeft,
  ArrowRight,
  Bot,
  CheckCircle2,
  Cloud,
  Laptop,
  Loader2,
  Mic,
  Plug,
  RefreshCw,
  Server,
  Sparkles,
} from "lucide-react";
import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePatchEnvVars } from "../../hooks/useEnvVars";
import { apiUrl } from "../../lib/apiBase";
import { useOnboardingStore } from "../../store/onboarding";
import { useProviderStore } from "../../store/provider";
import type { EnvVarsResponse } from "../../types";

const STEPS = 7;

async function fetchConfig(): Promise<{ default_llm: string }> {
  const res = await fetch(apiUrl("/api/config"));
  if (!res.ok) throw new Error("offline");
  return res.json();
}

function Card({
  icon,
  title,
  subtitle,
  selected,
  onSelect,
}: {
  icon: ReactNode;
  title: string;
  subtitle: string;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`w-full rounded-xl border p-4 text-left shadow-sm transition-colors ${
        selected
          ? "border-jarvis-400 bg-accent-muted"
          : "border-border bg-surface hover:bg-surface-muted"
      }`}
    >
      <div className="flex items-start gap-3">
        <div
          className={`mt-0.5 flex h-9 w-9 items-center justify-center rounded-xl ${
            selected ? "bg-jarvis-600 text-white" : "bg-surface-muted text-jarvis-700"
          }`}
        >
          {icon}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-fg">{title}</h3>
            {selected && <CheckCircle2 className="h-5 w-5 text-emerald-600" />}
          </div>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
        </div>
      </div>
    </button>
  );
}

function StepIcon({ step }: { step: number }) {
  const icons = [Sparkles, Server, Cloud, Plug, Mic, Laptop, Bot] as const;
  const Icon = icons[Math.max(0, Math.min(step, icons.length - 1))];
  return <Icon className="h-6 w-6 text-jarvis-600" />;
}

export function Onboarding() {
  const searchParams = useSearchParams();
  const reviewMode = searchParams.get("review") === "1";
  const router = useRouter();
  const queryClient = useQueryClient();
  const completed = useOnboardingStore((s) => s.onboardingCompleted);
  const complete = useOnboardingStore((s) => s.complete);
  const skipSetup = useOnboardingStore((s) => s.skip);

  const provider = useProviderStore((s) => s.provider);
  const setProvider = useProviderStore((s) => s.setProvider);

  const [step, setStep] = useState(0);
  const [apiCheck, setApiCheck] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [apiError, setApiError] = useState<string | null>(null);

  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("");
  const [ollamaModel, setOllamaModel] = useState("");

  const { data: envVarsData, refetch: refetchEnv } = useQuery({
    queryKey: ["env-vars"],
    queryFn: async () => {
      const res = await fetch(apiUrl("/api/config/env-vars"));
      if (!res.ok) throw new Error("Failed to load env vars");
      return res.json() as Promise<EnvVarsResponse>;
    },
    enabled: step >= 3,
    staleTime: 5_000,
  });

  const { mutate: patchEnv, isPending: savingKeys, isError: saveError, error: saveErr } =
    usePatchEnvVars();

  const runApiCheck = useCallback(async () => {
    setApiCheck("loading");
    setApiError(null);
    try {
      await fetchConfig();
      setApiCheck("ok");
    } catch {
      setApiCheck("error");
      setApiError(
        "We could not reach JARVIS on this computer. Start the assistant (see the README), then check that this page is opened from the same machine and port 8000 is not blocked."
      );
    }
  }, []);

  useEffect(() => {
    if (step === 1 && apiCheck === "idle") void runApiCheck();
  }, [step, apiCheck, runApiCheck]);

  useEffect(() => {
    if (completed && !reviewMode) router.replace("/");
  }, [completed, reviewMode, router]);

  const goNext = () => setStep((s) => Math.min(s + 1, STEPS - 1));
  const goBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleSkipAll = () => {
    skipSetup();
    router.replace("/");
  };

  const handleSaveKeys = () => {
    const vars: Record<string, string> = {
      DEFAULT_LLM: provider,
    };
    if (provider === "openai") {
      if (!openaiKey.trim()) return;
      vars.OPENAI_API_KEY = openaiKey.trim();
    } else if (provider === "anthropic") {
      if (!anthropicKey.trim()) return;
      vars.ANTHROPIC_API_KEY = anthropicKey.trim();
    } else {
      if (ollamaUrl.trim()) vars.OLLAMA_BASE_URL = ollamaUrl.trim();
      if (ollamaModel.trim()) vars.OLLAMA_MODEL = ollamaModel.trim();
    }

    patchEnv(vars, {
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["env-vars"] });
        await queryClient.invalidateQueries({ queryKey: ["config"] });
        goNext();
      },
    });
  };

  const handleFinish = () => {
    complete();
    router.replace("/");
  };

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <header className="flex items-center justify-between border-b border-border bg-surface/90 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-jarvis-600">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <span className="font-semibold text-fg">Set up JARVIS</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-xs text-muted sm:inline">
            Step {step + 1} of {STEPS}
          </span>
          <button
            type="button"
            onClick={handleSkipAll}
            className="rounded-lg px-3 py-1.5 text-sm text-muted transition-colors hover:bg-surface-muted hover:text-fg"
          >
            Skip setup
          </button>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-lg flex-1 flex-col px-4 py-8">
        <div className="mb-6 h-1.5 overflow-hidden rounded-full bg-surface-muted">
          <div
            className="h-full rounded-full bg-jarvis-500 transition-all duration-300"
            style={{ width: `${((step + 1) / STEPS) * 100}%` }}
          />
        </div>

        {step === 0 && (
          <section className="space-y-4 text-center">
            <Sparkles className="mx-auto h-12 w-12 text-jarvis-600" />
            <h1 className="text-2xl font-bold text-fg">Welcome to JARVIS</h1>
            <p className="text-sm leading-relaxed text-muted">
              JARVIS runs on <strong className="text-fg">your computer</strong> — not in the cloud.
              This short guide helps you connect the assistant and your AI account. It usually takes
              just a few minutes.
            </p>
            <p className="text-sm text-muted">
              Need help installing?{" "}
              <Link className="font-medium text-jarvis-700 hover:underline" href="/install">
                Open the install page
              </Link>
              .
            </p>
            <button
              type="button"
              onClick={goNext}
              className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-jarvis-600 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-jarvis-500"
            >
              Let&apos;s go
              <ArrowRight className="h-4 w-4" />
            </button>
          </section>
        )}

        {step === 1 && (
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-fg">
              <Server className="h-6 w-6 text-jarvis-600" />
              <h2 className="text-lg font-semibold">Is the assistant running?</h2>
            </div>
            <p className="text-sm text-muted">
              The JARVIS app must be started on your PC (for example{" "}
              <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-xs">
                python -m jarvis serve
              </code>
              ). This page talks to it through your browser.
            </p>
            {apiCheck === "loading" && (
              <div className="flex items-center gap-2 text-sm text-muted">
                <Loader2 className="h-4 w-4 animate-spin" />
                Checking connection…
              </div>
            )}
            {apiCheck === "ok" && (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
                <CheckCircle2 className="h-5 w-5 shrink-0" />
                Connected. You&apos;re ready for the next step.
              </div>
            )}
            {apiCheck === "error" && (
              <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
                <p>{apiError}</p>
                <button
                  type="button"
                  onClick={() => void runApiCheck()}
                  className="inline-flex items-center gap-1 font-medium text-jarvis-700 hover:underline"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Try again
                </button>
              </div>
            )}
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium text-fg hover:bg-surface-muted"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                type="button"
                disabled={apiCheck !== "ok"}
                onClick={goNext}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
              >
                Continue
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </section>
        )}

        {step === 2 && (
          <section className="space-y-4">
            <h2 className="text-lg font-semibold text-fg">How should JARVIS think?</h2>
            <p className="text-sm text-muted">Pick one. You can change this later in the chat bar.</p>
            <div className="space-y-2">
              <Card
                selected={provider === "openai"}
                onSelect={() => setProvider("openai")}
                icon={<Cloud className="h-5 w-5" />}
                title="OpenAI"
                subtitle="Cloud — GPT models. You need an API key from OpenAI."
              />
              <Card
                selected={provider === "anthropic"}
                onSelect={() => setProvider("anthropic")}
                icon={<Cloud className="h-5 w-5" />}
                title="Anthropic"
                subtitle="Cloud — Claude models. You need an API key from Anthropic."
              />
              <Card
                selected={provider === "ollama"}
                onSelect={() => setProvider("ollama")}
                icon={<Laptop className="h-5 w-5" />}
                title="Ollama"
                subtitle="Local — run a model on your machine. No API key required."
              />
            </div>
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium text-fg hover:bg-surface-muted"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                type="button"
                onClick={goNext}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white"
              >
                Continue
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </section>
        )}

        {step === 3 && (
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-fg">
              <StepIcon step={step} />
              <h2 className="text-lg font-semibold">Add your keys</h2>
            </div>
            <p className="text-sm text-muted">
              These settings are saved to your local <code className="text-fg">.env</code> through the API.
            </p>

            {provider === "openai" && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-fg">OpenAI API key</label>
                <input
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
                />
              </div>
            )}
            {provider === "anthropic" && (
              <div className="space-y-2">
                <label className="text-sm font-medium text-fg">Anthropic API key</label>
                <input
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
                />
              </div>
            )}
            {provider === "ollama" && (
              <div className="space-y-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-fg">Ollama base URL</label>
                  <input
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                    className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-fg">Model</label>
                  <input
                    value={ollamaModel}
                    onChange={(e) => setOllamaModel(e.target.value)}
                    placeholder="llama3.1"
                    className="w-full rounded-xl border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
                  />
                </div>
              </div>
            )}

            {saveError && (
              <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
                {(saveErr as Error)?.message ?? "Failed to save keys"}
              </div>
            )}

            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium text-fg hover:bg-surface-muted"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                type="button"
                onClick={handleSaveKeys}
                disabled={savingKeys}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white disabled:opacity-50"
              >
                {savingKeys ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Save & Continue
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </section>
        )}

        {step === 4 && (
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-fg">
              <Mic className="h-6 w-6 text-jarvis-600" />
              <h2 className="text-lg font-semibold">Voice input (optional)</h2>
            </div>
            <p className="text-sm text-muted">
              You can use your microphone in the dashboard. If you prefer typing, skip this step.
            </p>
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium text-fg hover:bg-surface-muted"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                type="button"
                onClick={goNext}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white"
              >
                Continue
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </section>
        )}

        {step === 5 && (
          <section className="space-y-4">
            <div className="flex items-center gap-2 text-fg">
              <Plug className="h-6 w-6 text-jarvis-600" />
              <h2 className="text-lg font-semibold">Integrations (optional)</h2>
            </div>
            <p className="text-sm text-muted">
              You can connect Gmail, Discord, YouTube, and more later from the Integrations page.
            </p>
            <div className="rounded-xl border border-border bg-surface p-3 text-sm text-muted">
              <p className="font-medium text-fg">Tip</p>
              <p className="mt-1">
                After saving keys, restart the API server and click refresh in Integrations.
              </p>
            </div>
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium text-fg hover:bg-surface-muted"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                type="button"
                onClick={goNext}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white"
              >
                Continue
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </section>
        )}

        {step === 6 && (
          <section className="space-y-4 text-center">
            <Bot className="mx-auto h-12 w-12 text-jarvis-600" />
            <h2 className="text-xl font-semibold text-fg">You&apos;re ready</h2>
            <p className="text-sm text-muted">
              Setup is complete. Open the dashboard and start chatting with JARVIS.
            </p>
            <button
              type="button"
              onClick={handleFinish}
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl bg-jarvis-600 py-3 text-sm font-medium text-white shadow-sm transition-colors hover:bg-jarvis-500"
            >
              Go to dashboard
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => {
                void refetchEnv();
              }}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-surface py-3 text-sm font-medium text-fg hover:bg-surface-muted"
            >
              Refresh env vars
            </button>
            {envVarsData ? (
              <p className="text-xs text-muted">
                Loaded {Object.keys(envVarsData.vars ?? {}).length} env keys from API.
              </p>
            ) : null}
          </section>
        )}
      </div>
    </div>
  );
}

