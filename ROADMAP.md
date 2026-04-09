# JARVIS.AGI — Roadmap

> **Goal**: Build the best free, self-hosted AGI assistant — one that unifies every app you use, understands you deeply, and acts autonomously on your behalf.

This document tracks what has been built, what is actively being worked on, and where contributors can make the biggest impact. Items are ordered by priority within each phase.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Shipped and working |
| 🚧 | Partially implemented / needs polish |
| 🔲 | Planned, not yet started |
| 🔥 | High-priority for contributors |

---

## Phase 1 — Foundation ✅

Core infrastructure that everything else depends on.

| Feature | Status | Notes |
|---------|--------|-------|
| LLM router (OpenAI / Anthropic / Ollama) | ✅ | Fallback chain, configurable via `.env` |
| Token streaming (SSE-style chunks) | ✅ | All three providers support `stream_chat` |
| Retry + exponential backoff | ✅ | Transient errors auto-retried |
| Persistent memory (ChromaDB) | ✅ | Episodic conversation history |
| Task scheduler (APScheduler) | ✅ | Reminders, recurring tasks |
| Wake word detection | ✅ | "Hey Jarvis" via openWakeWord |
| Speech-to-text (faster-whisper) | ✅ | Local, CPU, supports WebM from browser |
| Text-to-speech (edge-tts) | ✅ | Free neural voices, streamed to browser |
| FastAPI server + WebSocket | ✅ | Real-time streaming, TTS audio delivery |
| React dashboard | ✅ | Chat, voice waveform, provider selector |
| pytest suite | ✅ | Unit tests for tools, memory, LLM, agent |
| Docker Compose deployment | ✅ | One-command self-hosting with Nginx |
| Hot-reload config endpoint | ✅ | `POST /api/config/reload` |

---

## Phase 2 — Integrations ✅

Tools JARVIS can call on your behalf.

| Integration | Status | Requires |
|-------------|--------|---------|
| Gmail (read / search / send / archive) | ✅ | Google OAuth credentials |
| Google Calendar (list / create / free slots) | ✅ | Google OAuth credentials |
| Google Drive (search / read / create) | ✅ | Google OAuth credentials |
| Discord (send / read channels) | ✅ | Discord bot token |
| YouTube (search / transcripts) | ✅ | YouTube Data API key |
| Instagram DMs | ✅ | Meta Graph API token |
| WhatsApp (send / read) | ✅ | WhatsApp Business API |
| Telegram (send / files) | ✅ | Telegram bot token |
| Spotify (play / search / playlists) | ✅ | Spotify OAuth |
| Slack (send / read channels) | ✅ | Slack bot token |
| Weather (current + forecast) | ✅ | None — uses open-meteo.com |
| News headlines | ✅ | Optional NewsAPI key |
| Notion (pages / databases) | ✅ | Notion integration token |
| GitHub (issues / PRs / repos) | ✅ | GitHub personal access token |
| Home Assistant (smart home) | ✅ | HA instance + long-lived token |
| Finance / budgeting (Plaid) | ✅ | Plaid API keys |

### Planned integrations 🔲

| Integration | Priority | Notes |
|-------------|----------|-------|
| Google Meet / Zoom | 🔥 | Join, transcribe, summarise meetings |
| Linear / Jira | 🔥 | Create and update tickets |
| Trello | Medium | Card management |
| Twitter / X | Medium | Read timeline, post tweets |
| Reddit | Medium | Subscribe to threads, summarise |
| Twilio SMS | Medium | Send/receive SMS |
| Apple Contacts / Reminders | Low | macOS only |
| Obsidian vault sync | Low | Markdown note management |

---

## Phase 3 — Computer & Web Control ✅

JARVIS can act on your computer like a human would.

| Feature | Status | Notes |
|---------|--------|-------|
| Browser automation (Playwright) | ✅ | Navigate, fill forms, extract text |
| File system (read / write / search) | ✅ | Sandboxed to configured dirs |
| Code execution sandbox | ✅ | Run Python + shell with timeout |
| Screen OCR (Tesseract) | ✅ | Read any text visible on screen |
| Computer control (PyAutoGUI) | ✅ | Click, type, drag, hotkeys |

### Planned improvements 🔲

| Feature | Priority | Notes |
|---------|----------|-------|
| Vision-guided browser agent | 🔥 | Use screenshots for element targeting, not just selectors |
| Sandboxed Docker code execution | 🔥 | Replace subprocess with Docker container for safety |
| Screen-diff alerting | Medium | Notify when a watched region changes |
| Voice-controlled form filling | Medium | "Fill in my address" by voice |

---

## Phase 4 — Intelligence Layer ✅

Features that make JARVIS genuinely smart and proactive.

| Feature | Status | Notes |
|---------|--------|-------|
| Proactive agent (ambient alerts) | ✅ | Morning briefing, urgent email watch |
| Multi-step planner | ✅ | Decompose goals into subtasks, execute |
| Multi-agent orchestration | ✅ | Specialist sub-agents per domain |
| Plugin system (dynamic tools) | ✅ | Drop `.py` files into `plugins/` dir |
| Knowledge base RAG | ✅ | Index docs (PDF, MD, DOCX) → semantic search |
| User profile + world model | ✅ | SQLite-backed facts about user |

### Planned improvements 🔲

| Feature | Priority | Notes |
|---------|----------|-------|
| Parallel tool execution | 🔥 | Run independent tools concurrently |
| Plan visualisation in UI | 🔥 | Show plan steps live as they execute |
| Adaptive tool selection | Medium | Learn which tools work for which queries |
| Long-horizon task resumption | Medium | Pick up abandoned plans after restart |
| Confidence scoring | Medium | Show uncertainty when JARVIS isn't sure |

---

## Phase 5 — Platform ✅

Deployment, configuration, and scale.

| Feature | Status | Notes |
|---------|--------|-------|
| Docker Compose stack | ✅ | JARVIS + Ollama + Nginx in one command |
| Nginx reverse proxy | ✅ | `/` → frontend, `/api` → backend |
| Speaker recognition | ✅ | Identify who is speaking by voice |

### Planned improvements 🔲

| Feature | Priority | Notes |
|---------|----------|-------|
| Mobile companion app | 🔥 | React Native, push notifications, voice |
| PWA (installable web app) | 🔥 | Offline support, home screen icon |
| User authentication | 🔥 | Multi-user support with per-user memory |
| Local model fine-tuning | Medium | Adapt a small model on your own data |
| Encrypted secret storage | Medium | Vault-style key management |
| Usage analytics dashboard | Low | Token spend, tool usage, latency charts |

---

## Phase 6 — AGI Frontier 🚧

Capabilities that push toward genuinely autonomous intelligence.

| Feature | Status | Notes |
|---------|--------|-------|
| Self-improvement loop | ✅ | Proposes + installs new tools via LLM |
| Continuous learning (world model) | ✅ | Extracts facts from every conversation |
| Emotion detection (voice tone) | ✅ | Adjusts response style to user mood |
| Multimodal input (images, PDFs, audio) | ✅ | Upload → describe / summarise |
| Ambient awareness | ✅ | Background monitors, proactive alerts |
| Ollama tool-calling (reliable) | 🚧 | Works but slow on CPU; set `OLLAMA_TOOLS_ENABLED=true` with a GPU |

### Planned 🔲

| Feature | Priority | Notes |
|---------|----------|-------|
| Real-time speech emotion feedback | 🔥 | Show detected emotion in UI |
| Autonomous goal management | 🔥 | User sets a goal; JARVIS pursues it over days |
| Vision understanding (webcam) | 🔥 | "What am I looking at?" from live camera |
| Personalized LLM fine-tuning | Medium | Train on user's writing style |
| Sleep / wake cycle awareness | Medium | Different behaviour morning vs evening |
| Memory summarisation + forgetting | Medium | Compress old memories, surface relevant ones |
| Cross-device sync | Low | Sync context between phone and desktop |
| Causal reasoning module | Low | Understand cause/effect chains |

---

## Performance Targets 🔲

These are milestones that define "top-of-the-line" quality.

| Metric | Current | Target |
|--------|---------|--------|
| Wake word → first token | ~4 s | < 1 s |
| Simple conversational reply (Ollama CPU) | ~3 s | < 2 s |
| Tool call round-trip (local) | ~5 s | < 3 s |
| Memory retrieval latency | < 100 ms | < 50 ms |
| WebSocket reconnect time | ~3 s | < 1 s |
| Frontend initial load | TBD | < 1 s |

---

## Known Issues 🔥

Issues that degrade the core experience and should be fixed before new features.

| Issue | Description | Good first issue? |
|-------|-------------|:-----------------:|
| `chunk` events not streamed in UI | Frontend ignores `chunk` WS messages; only `done` renders | Yes |
| Voice auto-send race condition | Transcript sometimes sends before `isWaiting` clears | Yes |
| Whisper reloads model per session | Model should persist across requests | Yes |
| Tool calling on CPU is slow | `OLLAMA_TOOLS_ENABLED=true` unusable without GPU | No |
| No error boundary in React | Unhandled JS errors crash the whole UI | Yes |
| Missing loading skeleton | No placeholder while messages load | Yes |

---

## Architecture Overview

```
jarvis/
├── core/
│   ├── agent.py          # Main LLM tool-calling loop (streaming)
│   ├── memory.py         # ChromaDB episodic memory
│   ├── tools.py          # Tool base class + registry
│   ├── scheduler.py      # APScheduler reminders
│   ├── planner.py        # Multi-step goal decomposer
│   ├── orchestrator.py   # Multi-agent coordinator
│   └── proactive.py      # Background ambient monitors
├── llm/
│   ├── base.py           # BaseLLM, LLMResponse, StreamChunk
│   ├── router.py         # Provider selection + fallback
│   ├── openai_llm.py
│   ├── anthropic_llm.py
│   └── ollama_llm.py
├── voice/
│   ├── wake_word.py      # openWakeWord "Hey Jarvis"
│   ├── stt.py            # faster-whisper (local)
│   └── tts.py            # edge-tts (free neural voices)
├── integrations/         # One file per service (Tool subclasses)
├── agi/
│   ├── world_model.py    # Persistent user knowledge (SQLite)
│   ├── self_improve.py   # Proposes + installs new tools
│   ├── emotion.py        # Voice tone emotion detection
│   ├── multimodal.py     # Image / PDF / audio processing
│   └── ambient.py        # Background monitors + alerts
├── api/
│   ├── main.py           # FastAPI lifespan + integration loading
│   ├── ws.py             # WebSocket handler (streaming, TTS, plans)
│   └── routes/           # REST endpoints (voice, config, AGI)
└── plugins/
    └── loader.py         # Dynamic tool loading from plugins/ dir

frontend/                 # React + Vite + TailwindCSS
```

---

## Contributing

1. **Fork** the repo and create a branch: `git checkout -b feat/my-feature`
2. **Pick an item** from the roadmap above — "Known Issues" and 🔥 items have the most impact
3. **Keep PRs focused** — one feature or fix per PR
4. **Add tests** for new tools in `tests/`
5. **Update `.env.example`** if you add new config keys
6. Open a **PR** against `main` and describe what you built and why

### Setting up a dev environment

```bash
git clone https://github.com/Andry-Arthur/jarvis.agi.git
cd jarvis.agi
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
# Add OLLAMA_MODEL=qwen2.5:1.5b for fast local responses
python -m jarvis serve
# In another terminal:
cd frontend && npm install && npm run dev
```

Run tests:

```bash
pytest
```

---

## Model Recommendations

| Use case | Recommended model | Speed on CPU |
|----------|------------------|-------------|
| Fast chat (default) | `qwen2.5:1.5b` | ~3 s |
| Better reasoning | `gemma2:2b` | ~8 s |
| Tool calling (needs GPU) | `llama3.1` | ~3.5 min CPU / ~10 s GPU |
| Best quality (cloud) | `gpt-4o` or `claude-opus-4-5` | <2 s |

---

*Last updated: April 2026*
