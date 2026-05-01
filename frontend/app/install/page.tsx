"use client";

import {
  ArrowRight,
  Copy,
  ExternalLink,
  Github,
  Laptop,
  Server,
  Terminal,
} from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";

type Os = "windows" | "mac" | "linux";

function detectOs(): Os {
  const ua = typeof navigator === "undefined" ? "" : navigator.userAgent.toLowerCase();
  if (ua.includes("windows")) return "windows";
  if (ua.includes("mac os") || ua.includes("macintosh")) return "mac";
  return "linux";
}

function CommandBlock({ label, command }: { label: string; command: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-fg">{label}</span>
        <button
          type="button"
          onClick={() => void handleCopy()}
          className="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1 text-xs font-medium text-muted transition-colors hover:bg-surface-muted hover:text-fg"
          aria-label="Copy command"
        >
          <Copy className="h-3.5 w-3.5" />
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto rounded-xl border border-border bg-surface-muted p-3 text-xs text-fg">
        <code>{command}</code>
      </pre>
    </div>
  );
}

function OsTabs({ value, onChange }: { value: Os; onChange: (os: Os) => void }) {
  const items: Array<{ id: Os; label: string }> = [
    { id: "windows", label: "Windows" },
    { id: "mac", label: "macOS" },
    { id: "linux", label: "Linux" },
  ];

  return (
    <div className="inline-flex rounded-xl border border-border bg-surface p-1">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => onChange(item.id)}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            value === item.id
              ? "bg-jarvis-600 text-white shadow-sm"
              : "text-muted hover:bg-surface-muted hover:text-fg"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export default function InstallPage() {
  const [os, setOs] = useState<Os>(() => detectOs());

  const commands = useMemo(() => {
    const clone = "git clone https://github.com/Andry-Arthur/jarvis.agi.git";
    const cd = "cd jarvis.agi";
    const venvWin = "python -m venv .venv\r\n.venv\\Scripts\\activate";
    const venvUnix = "python3 -m venv .venv\nsource .venv/bin/activate";
    const deps = "pip install -r requirements.txt";
    const envWin = "copy .env.example .env";
    const envUnix = "cp .env.example .env";
    const serve = "python -m jarvis serve";
    const ui = "cd frontend\nnpm install\nnpm run dev";

    return {
      clone,
      cd,
      venv: os === "windows" ? venvWin : venvUnix,
      env: os === "windows" ? envWin : envUnix,
      deps,
      serve,
      ui,
    };
  }, [os]);

  return (
    <div className="min-h-screen bg-page text-fg">
      <header className="border-b border-border bg-surface/90 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-3 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-jarvis-600 shadow-sm">
              <Laptop className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-semibold leading-tight text-fg">Install JARVIS.AGI</h1>
              <p className="text-xs text-muted">
                A quick, local-first setup guide. No backend required for this page.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="https://github.com/Andry-Arthur/jarvis.agi"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium text-fg transition-colors hover:bg-surface-muted"
            >
              <Github className="h-4 w-4" />
              Repo
              <ExternalLink className="h-4 w-4 text-muted" />
            </a>
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 rounded-xl bg-jarvis-600 px-3 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-jarvis-500"
            >
              Continue setup
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl space-y-6 px-4 py-8">
        <section className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-fg">Quick start</h2>
              <p className="text-sm text-muted">
                You will run two things: the JARVIS API server on port{" "}
                <span className="font-medium text-fg">8000</span>, and the web UI on{" "}
                <span className="font-medium text-fg">5173</span>.
              </p>
            </div>
            <OsTabs value={os} onChange={setOs} />
          </div>

          <div className="mt-5 grid gap-5">
            <CommandBlock label="1) Clone the repo" command={commands.clone} />
            <CommandBlock label="2) Enter the folder" command={commands.cd} />
            <CommandBlock label="3) Create + activate a virtualenv" command={commands.venv} />
            <CommandBlock label="4) Install Python dependencies" command={commands.deps} />
            <CommandBlock label="5) Create your .env file" command={commands.env} />
            <CommandBlock label="6) Start the API server" command={commands.serve} />
            <CommandBlock label="7) Start the web dashboard (new terminal)" command={commands.ui} />
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
            <div className="flex items-center gap-2 text-fg">
              <Server className="h-5 w-5 text-jarvis-600" />
              <h2 className="text-lg font-semibold">Then onboard inside the app</h2>
            </div>
            <p className="mt-2 text-sm text-muted">
              Once the server is running, open the setup guide and connect your LLM provider keys.
              This next screen talks to your local JARVIS API.
            </p>
            <div className="mt-4 flex flex-col gap-2 sm:flex-row">
              <Link
                href="/onboarding"
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-jarvis-600 px-3 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-jarvis-500"
              >
                Open onboarding
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/"
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-surface px-3 py-2.5 text-sm font-medium text-fg transition-colors hover:bg-surface-muted"
              >
                Go to dashboard
              </Link>
            </div>
            <p className="mt-3 text-xs text-muted">
              If the onboarding page cannot connect, confirm{" "}
              <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-[11px]">
                python -m jarvis serve
              </code>{" "}
              is running and that port 8000 is not blocked.
            </p>
          </div>

          <div className="rounded-2xl border border-border bg-surface p-5 shadow-sm">
            <div className="flex items-center gap-2 text-fg">
              <Terminal className="h-5 w-5 text-jarvis-600" />
              <h2 className="text-lg font-semibold">Docker (API server only)</h2>
            </div>
            <p className="mt-2 text-sm text-muted">
              The repo includes a Dockerfile for the FastAPI server. The web UI is still run from{" "}
              <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-xs">
                frontend
              </code>{" "}
              (or hosted separately).
            </p>

            <div className="mt-4 space-y-4">
              <CommandBlock label="Build the image" command={"docker build -t jarvis-agi ."} />
              <CommandBlock label="Run the API on port 8000" command={"docker run --rm -p 8000:8000 jarvis-agi"} />
            </div>

            <p className="mt-3 text-xs text-muted">
              If you host the UI remotely, set your reverse proxy/rewrites so{" "}
              <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-[11px]">
                /api
              </code>{" "}
              and{" "}
              <code className="rounded border border-border bg-surface-muted px-1 py-0.5 text-[11px]">
                /ws
              </code>{" "}
              reach the backend.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}

