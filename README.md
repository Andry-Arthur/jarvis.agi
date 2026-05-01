# JARVIS.AGI

> A free, self-hosted AI agent that unifies Gmail, Discord, YouTube, Instagram and more — with full voice control.

JARVIS.AGI is an open-source alternative to OpenClaw. It runs entirely on your own machine, supports multiple LLM backends, and connects to the apps you use every day through a voice-first interface and a modern web dashboard.

---

## Features

- **Voice Assistant** — Say "Hey Jarvis" and talk naturally. Wake word → STT → LLM → TTS pipeline runs locally.
- **Multi-model LLM** — Switch between OpenAI (GPT-4o), Anthropic (Claude), or local Ollama models at runtime.
- **Unified Integrations** — Gmail, Discord, YouTube, Instagram as callable tools.
- **Persistent Memory** — Remembers context across sessions via ChromaDB vector store.
- **Web Dashboard** — React UI with real-time WebSocket streaming, voice waveform, and settings.
- **Scheduled Tasks** — "Remind me at 9am" style tasks via APScheduler.
- **100% Free** — MIT licensed, self-hosted, no mandatory cloud services.

---

## Quick Start

### 1. Install Python dependencies

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Run in voice CLI mode

```bash
python -m jarvis
```

### 4. Run the API server

```bash
python -m jarvis serve
```

### 5. Run the web dashboard (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 (or visit http://localhost:5173/install for a guided install + onboarding front page).

---

## Voice Pipeline

```
Microphone → openWakeWord ("Hey Jarvis") → faster-whisper STT → Agent → edge-tts → Speaker
```

All STT processing is local (faster-whisper). TTS uses Microsoft Edge's free neural voices (requires internet).

---

## Integrations Setup

### Gmail & YouTube
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable Gmail API + YouTube Data API v3
3. Create OAuth 2.0 credentials → Download as `credentials.json`
4. Set `GOOGLE_CLIENT_SECRET_FILE=credentials.json` in `.env`

### Discord
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create an application → Bot → Copy token
3. Set `DISCORD_BOT_TOKEN=...` in `.env`
4. Invite the bot to your server with `bot` + `messages.read` scopes

### Instagram
1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create an app → Add Instagram Graph API
3. Generate a long-lived access token
4. Set `INSTAGRAM_ACCESS_TOKEN=...` and `INSTAGRAM_USER_ID=...` in `.env`

---

## Configuration

Edit `config/settings.yaml` or override any value via `.env`.

| Setting | Default | Description |
|---|---|---|
| `DEFAULT_LLM` | `openai` | LLM provider: `openai`, `anthropic`, `ollama` |
| `DEFAULT_MODEL` | `gpt-4o` | Model name |
| `WHISPER_MODEL` | `base` | Whisper model size |
| `TTS_VOICE` | `en-US-GuyNeural` | Edge TTS voice |
| `WAKE_WORD_MODEL` | *(built-in)* | Path to custom `.onnx` wake word model |

### Autonomous background mode

Scheduled digests (morning briefing, news, economics, travel, inbox/calendar checks, optional ambient monitoring) run **only while the API process is running** (`python -m jarvis serve`). They do not survive reboots unless you start the server at login or install it as a Windows Service, macOS `launchd` job, or systemd unit.

Configure in `config/settings.yaml` under `autonomous:` (master switch `enabled`, then per-job flags). Environment overrides include `AUTONOMOUS_ENABLED`, `AUTONOMOUS_NEWS_INTERVAL_HOURS`, `AUTONOMOUS_ECONOMICS_INTERVAL_HOURS`, and `AUTONOMOUS_AMBIENT_ENABLED`.

Use `GET /api/autonomous/status` to see whether autonomous mode is enabled, which runner is active, and upcoming scheduler jobs.

---

## Architecture

```
jarvis/
├── core/        # Agent loop, memory, tool registry
├── llm/         # OpenAI / Anthropic / Ollama providers + router
├── voice/       # Wake word, STT, TTS
├── integrations/# Gmail, Discord, YouTube, Instagram tools
└── api/         # FastAPI + WebSocket server

frontend/        # React + Vite + TailwindCSS dashboard
config/          # Default YAML settings
```

---

## License

MIT — use it however you like.
