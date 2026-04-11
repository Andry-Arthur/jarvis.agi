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
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePatchEnvVars } from "../hooks/useEnvVars";
import { apiUrl } from "../lib/apiBase";
import { useOnboardingStore } from "../store/onboarding";
import { useProviderStore } from "../store/provider";

const STEPS = 7;

async function fetchConfig(): Promise<{ default_llm: string }> {
  const res = await fetch(apiUrl("/api/config"));
  if (!res.ok) throw new Error("offline");
  return res.json();
}

export function Onboarding() {
  const [searchParams] = useSearchParams();
  const reviewMode = searchParams.get("review") === "1";
  const navigate = useNavigate();
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
      return res.json() as Promise<import("../types").EnvVarsResponse>;
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
    if (step === 1 && apiCheck === "idle") {
      void runApiCheck();
    }
  }, [step, apiCheck, runApiCheck]);

  if (completed && !reviewMode) {
    return <Navigate to="/" replace />;
  }

  const goNext = () => setStep((s) => Math.min(s + 1, STEPS - 1));
  const goBack = () => setStep((s) => Math.max(s - 1, 0));

  const handleSkipAll = () => {
    skipSetup();
    navigate("/", { replace: true });
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
    navigate("/", { replace: true });
  };

  return (
    <div className="flex min-h-screen flex-col bg-hud-pane">
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
              <ProviderCard
                selected={provider === "openai"}
                onSelect={() => setProvider("openai")}
                icon={<Cloud className="h-5 w-5" />}
                title="OpenAI"
                subtitle="Cloud — GPT models. You need an API key from OpenAI."
              />
              <ProviderCard
                selected={provider === "anthropic"}
                onSelect={() => setProvider("anthropic")}
                icon={<Cloud className="h-5 w-5" />}
                title="Anthropic"
                subtitle="Cloud — Claude. You need an API key from Anthropic."
              />
              <ProviderCard
                selected={provider === "ollama"}
                onSelect={() => setProvider("ollama")}
                icon={<Laptop className="h-5 w-5" />}
                title="Ollama"
                subtitle="Runs on your computer — no cloud API key. Ollama must be installed."
              />
            </div>
            <div className="flex gap-2 pt-4">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium"
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
            <h2 className="text-lg font-semibold text-fg">Connect your account</h2>
            <p className="text-sm text-muted">
              Values are saved to your <code className="text-fg">.env</code> file on the machine
              running JARVIS. They are not sent to us.
            </p>

            {provider === "openai" && (
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-fg">OpenAI API key</span>
                <input
                  type="password"
                  autoComplete="off"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-..."
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
                />
              </label>
            )}
            {provider === "anthropic" && (
              <label className="block">
                <span className="mb-1 block text-sm font-medium text-fg">Anthropic API key</span>
                <input
                  type="password"
                  autoComplete="off"
                  value={anthropicKey}
                  onChange={(e) => setAnthropicKey(e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-fg outline-none focus:border-jarvis-500 focus:ring-1 focus:ring-jarvis-500/30"
                />
              </label>
            )}
            {provider === "ollama" && (
              <div className="space-y-3">
                <p className="text-sm text-muted">
                  Optional. Defaults work if Ollama is on this computer at the usual address.
                </p>
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-fg">Ollama URL</span>
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    placeholder="http://localhost:11434"
                    className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-jarvis-500"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-fg">Model name</span>
                  <input
                    type="text"
                    value={ollamaModel}
                    onChange={(e) => setOllamaModel(e.target.value)}
                    placeholder="e.g. llama3.1"
                    className="w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-jarvis-500"
                  />
                </label>
              </div>
            )}

            {saveError && (
              <p className="text-sm text-red-700">
                {(saveErr as Error)?.message ?? "Could not save. Is the API running?"}
              </p>
            )}

            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl border border-border bg-surface py-2.5 text-sm font-medium"
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </button>
              <button
                type="button"
                disabled={
                  savingKeys ||
                  (provider === "openai" && !openaiKey.trim() && !envVarsData?.vars.OPENAI_API_KEY?.is_set) ||
                  (provider === "anthropic" &&
                    !anthropicKey.trim() &&
                    !envVarsData?.vars.ANTHROPIC_API_KEY?.is_set)
                }
                onClick={handleSaveKeys}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white disabled:opacity-40"
              >
                {savingKeys ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Save & continue
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
            <button
              type="button"
              onClick={() => void refetchEnv()}
              className="text-xs text-jarvis-600 hover:underline"
            >
              Refresh saved keys
            </button>
          </section>
        )}

        {step === 4 && (
          <section className="space-y-4 text-center">
            <Plug className="mx-auto h-10 w-10 text-jarvis-600" />
            <h2 className="text-lg font-semibold text-fg">Apps & services</h2>
            <p className="text-sm text-muted">
              You can connect Gmail, Discord, and more later. Nothing else is required to start
              chatting.
            </p>
            <button
              type="button"
              onClick={() => {
                complete();
                navigate("/integrations", { replace: true });
              }}
              className="w-full rounded-xl border border-border bg-surface py-2.5 text-sm font-medium text-fg hover:bg-surface-muted"
            >
              Open Integrations
            </button>
            <button
              type="button"
              onClick={goNext}
              className="w-full rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white"
            >
              Skip for now
            </button>
            <button type="button" onClick={goBack} className="text-sm text-muted hover:text-fg">
              Back
            </button>
          </section>
        )}

        {step === 5 && (
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Mic className="h-6 w-6 text-jarvis-600" />
              <h2 className="text-lg font-semibold text-fg">Voice</h2>
            </div>
            <p className="text-sm text-muted">
              On the main screen you can use the microphone to speak to JARVIS. Your browser will ask
              for permission the first time — that&apos;s normal.
            </p>
            <button
              type="button"
              onClick={async () => {
                try {
                  const s = await navigator.mediaDevices.getUserMedia({ audio: true });
                  s.getTracks().forEach((t) => t.stop());
                } catch {
                  /* user denied or no mic — still allow continue */
                }
              }}
              className="w-full rounded-xl border border-border bg-surface py-2.5 text-sm font-medium hover:bg-surface-muted"
            >
              Test microphone permission
            </button>
            <div className="flex gap-2 pt-2">
              <button
                type="button"
                onClick={goBack}
                className="inline-flex flex-1 items-center justify-center rounded-xl border border-border py-2.5 text-sm"
              >
                Back
              </button>
              <button
                type="button"
                onClick={goNext}
                className="inline-flex flex-1 items-center justify-center rounded-xl bg-jarvis-600 py-2.5 text-sm font-medium text-white"
              >
                Continue
              </button>
            </div>
          </section>
        )}

        {step === 6 && (
          <section className="space-y-6 text-center">
            <CheckCircle2 className="mx-auto h-14 w-14 text-emerald-600" />
            <h2 className="text-xl font-bold text-fg">You&apos;re set up</h2>
            <p className="text-sm text-muted">
              Head to the dashboard to chat. You can reopen this guide anytime from the sidebar.
            </p>
            <button
              type="button"
              onClick={handleFinish}
              className="w-full rounded-xl bg-jarvis-600 py-3 text-sm font-medium text-white shadow-sm hover:bg-jarvis-500"
            >
              Start chatting
            </button>
          </section>
        )}
      </div>
    </div>
  );
}

function ProviderCard({
  selected,
  onSelect,
  icon,
  title,
  subtitle,
}: {
  selected: boolean;
  onSelect: () => void;
  icon: ReactNode;
  title: string;
  subtitle: string;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex w-full items-start gap-3 rounded-xl border p-4 text-left transition-colors ${
        selected
          ? "border-jarvis-500 bg-accent-muted ring-1 ring-jarvis-400/40"
          : "border-border bg-surface hover:bg-surface-muted"
      }`}
    >
      <div className="text-jarvis-600">{icon}</div>
      <div>
        <div className="font-semibold text-fg">{title}</div>
        <div className="text-xs text-muted">{subtitle}</div>
      </div>
    </button>
  );
}
