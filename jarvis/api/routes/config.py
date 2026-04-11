"""Hot-reload configuration endpoint."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from jarvis.api.main import app_state

logger = logging.getLogger(__name__)
router = APIRouter(tags=["config"])

ENV_FILE = Path(".env")

# All known env vars grouped by section.
# Used by GET /api/config/env-vars to return masked hints.
KNOWN_ENV_VARS: dict[str, dict] = {
    # ── LLM ──────────────────────────────────────────────────────────────
    "DEFAULT_LLM": {
        "label": "Default LLM Provider",
        "section": "LLM",
        "secret": False,
        "hint": "openai | anthropic | ollama",
    },
    "OPENAI_API_KEY": {
        "label": "OpenAI API Key",
        "section": "LLM",
        "secret": True,
        "hint": "sk-...",
    },
    "ANTHROPIC_API_KEY": {
        "label": "Anthropic API Key",
        "section": "LLM",
        "secret": True,
        "hint": "sk-ant-...",
    },
    "OLLAMA_BASE_URL": {
        "label": "Ollama Base URL",
        "section": "LLM",
        "secret": False,
        "hint": "http://localhost:11434",
    },
    "OLLAMA_MODEL": {
        "label": "Ollama Model",
        "section": "LLM",
        "secret": False,
        "hint": "qwen2.5:1.5b",
    },
    # ── Voice ─────────────────────────────────────────────────────────────
    "WHISPER_MODEL": {
        "label": "Whisper Model Size",
        "section": "Voice",
        "secret": False,
        "hint": "tiny | base | small | medium | large-v3",
    },
    "TTS_VOICE": {
        "label": "TTS Voice",
        "section": "Voice",
        "secret": False,
        "hint": "en-US-AriaNeural",
    },
    "WAKE_WORD_MODEL": {
        "label": "Wake Word Model",
        "section": "Voice",
        "secret": False,
        "hint": "hey_jarvis | hey_mycroft | alexa",
    },
    # ── Google ────────────────────────────────────────────────────────────
    "GMAIL_CREDENTIALS_FILE": {
        "label": "Google Credentials File",
        "section": "Google",
        "secret": False,
        "hint": "credentials.json",
    },
    "YOUTUBE_API_KEY": {
        "label": "YouTube API Key",
        "section": "Google",
        "secret": True,
        "hint": "AIza...",
    },
    "GOOGLE_DRIVE_ENABLED": {
        "label": "Google Drive Enabled",
        "section": "Google",
        "secret": False,
        "hint": "true | false",
    },
    # ── Discord ───────────────────────────────────────────────────────────
    "DISCORD_BOT_TOKEN": {
        "label": "Discord Bot Token",
        "section": "Discord",
        "secret": True,
        "hint": "MTI...",
    },
    # ── Telegram ──────────────────────────────────────────────────────────
    "TELEGRAM_BOT_TOKEN": {
        "label": "Telegram Bot Token",
        "section": "Telegram",
        "secret": True,
        "hint": "123456:ABC-...",
    },
    "TELEGRAM_CHAT_ID": {
        "label": "Telegram Chat ID",
        "section": "Telegram",
        "secret": False,
        "hint": "-100...",
    },
    # ── Spotify ───────────────────────────────────────────────────────────
    "SPOTIPY_CLIENT_ID": {
        "label": "Spotify Client ID",
        "section": "Spotify",
        "secret": True,
        "hint": "",
    },
    "SPOTIPY_CLIENT_SECRET": {
        "label": "Spotify Client Secret",
        "section": "Spotify",
        "secret": True,
        "hint": "",
    },
    "SPOTIPY_REDIRECT_URI": {
        "label": "Spotify Redirect URI",
        "section": "Spotify",
        "secret": False,
        "hint": "http://localhost:8888/callback",
    },
    # ── Slack ─────────────────────────────────────────────────────────────
    "SLACK_BOT_TOKEN": {
        "label": "Slack Bot Token",
        "section": "Slack",
        "secret": True,
        "hint": "xoxb-...",
    },
    # ── Instagram ─────────────────────────────────────────────────────────
    "INSTAGRAM_ACCESS_TOKEN": {
        "label": "Instagram Access Token",
        "section": "Instagram",
        "secret": True,
        "hint": "",
    },
    "INSTAGRAM_USER_ID": {
        "label": "Instagram User ID",
        "section": "Instagram",
        "secret": False,
        "hint": "",
    },
    # ── WhatsApp ──────────────────────────────────────────────────────────
    "WHATSAPP_ENABLED": {
        "label": "WhatsApp Enabled",
        "section": "WhatsApp",
        "secret": False,
        "hint": "true | false",
    },
    "WHATSAPP_TOKEN": {
        "label": "WhatsApp Token",
        "section": "WhatsApp",
        "secret": True,
        "hint": "",
    },
    "WHATSAPP_PHONE_ID": {
        "label": "WhatsApp Phone ID",
        "section": "WhatsApp",
        "secret": False,
        "hint": "",
    },
    # ── Notion ────────────────────────────────────────────────────────────
    "NOTION_TOKEN": {
        "label": "Notion Integration Token",
        "section": "Notion",
        "secret": True,
        "hint": "secret_...",
    },
    # ── GitHub ────────────────────────────────────────────────────────────
    "GITHUB_TOKEN": {
        "label": "GitHub Personal Access Token",
        "section": "GitHub",
        "secret": True,
        "hint": "ghp_...",
    },
    # ── Home Assistant ────────────────────────────────────────────────────
    "HA_BASE_URL": {
        "label": "Home Assistant URL",
        "section": "Home Assistant",
        "secret": False,
        "hint": "http://homeassistant.local:8123",
    },
    "HA_TOKEN": {
        "label": "Home Assistant Token",
        "section": "Home Assistant",
        "secret": True,
        "hint": "",
    },
    # ── Finance ───────────────────────────────────────────────────────────
    "PLAID_CLIENT_ID": {
        "label": "Plaid Client ID",
        "section": "Finance",
        "secret": True,
        "hint": "",
    },
    "PLAID_SECRET": {
        "label": "Plaid Secret",
        "section": "Finance",
        "secret": True,
        "hint": "",
    },
    # ── News ──────────────────────────────────────────────────────────────
    "NEWSAPI_KEY": {
        "label": "NewsAPI Key",
        "section": "News",
        "secret": True,
        "hint": "",
    },
    # ── Filesystem ────────────────────────────────────────────────────────
    "FS_ALLOWED_DIRS": {
        "label": "Allowed Directories",
        "section": "Filesystem",
        "secret": False,
        "hint": "~/Documents,~/Downloads",
    },
}


def _mask(value: str) -> str:
    """Return last 4 chars prefixed with bullets, e.g. '••••ab12'."""
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


class EnvVarStatus(BaseModel):
    label: str
    section: str
    secret: bool
    is_set: bool
    masked_value: str | None
    placeholder: str


class EnvVarsResponse(BaseModel):
    vars: dict[str, EnvVarStatus]


@router.get("/config/env-vars", response_model=EnvVarsResponse)
async def get_env_vars() -> EnvVarsResponse:
    """Return all known env var names with masked hints — never returns actual values."""
    result: dict[str, EnvVarStatus] = {}
    for key, meta in KNOWN_ENV_VARS.items():
        raw = os.getenv(key, "")
        is_set = bool(raw)
        result[key] = EnvVarStatus(
            label=meta["label"],
            section=meta["section"],
            secret=meta["secret"],
            is_set=is_set,
            masked_value=_mask(raw) if is_set else None,
            placeholder=meta["hint"],
        )
    return EnvVarsResponse(vars=result)


class EnvVarsPatchRequest(BaseModel):
    vars: dict[str, str]


class EnvVarsPatchResponse(BaseModel):
    saved: list[str]
    cleared: list[str]
    reloaded: bool
    providers: list[str]
    message: str


@router.patch("/config/env-vars", response_model=EnvVarsPatchResponse)
async def patch_env_vars(body: EnvVarsPatchRequest) -> EnvVarsPatchResponse:
    """Write env vars to .env file and hot-reload the agent."""
    from dotenv import load_dotenv, set_key, unset_key
    from jarvis.api.main import _build_agent

    # Reject unknown keys to prevent arbitrary writes
    unknown = [k for k in body.vars if k not in KNOWN_ENV_VARS]
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown env var(s): {', '.join(unknown)}",
        )

    # Ensure .env file exists
    if not ENV_FILE.exists():
        ENV_FILE.touch()

    env_path = str(ENV_FILE)
    saved: list[str] = []
    cleared: list[str] = []

    for key, value in body.vars.items():
        if value == "":
            # Empty string → remove the key
            unset_key(env_path, key)
            cleared.append(key)
        else:
            set_key(env_path, key, value)
            saved.append(key)

    # Hot-reload: re-read .env into os.environ and rebuild agent
    load_dotenv(dotenv_path=env_path, override=True)
    logger.info("Env vars updated: saved=%s cleared=%s", saved, cleared)

    providers: list[str] = []
    reloaded = False
    try:
        scheduler = app_state.get("scheduler")
        new_agent = _build_agent(scheduler=scheduler)
        app_state["agent"] = new_agent
        providers = list(new_agent.llm.available_providers)
        reloaded = True
    except Exception as exc:
        logger.warning("Agent rebuild failed after env update: %s", exc)

    changed = saved + cleared
    return EnvVarsPatchResponse(
        saved=saved,
        cleared=cleared,
        reloaded=reloaded,
        providers=providers,
        message=(
            f"Saved {len(saved)} var(s), cleared {len(cleared)}. "
            + (f"Agent rebuilt with providers: {', '.join(providers)}." if reloaded else "Agent reload failed — check logs.")
        ),
    )


class ConfigReloadResponse(BaseModel):
    status: str
    providers: list[str]
    message: str


@router.post("/config/reload", response_model=ConfigReloadResponse)
async def reload_config() -> ConfigReloadResponse:
    """Re-read .env and rebuild the agent without restarting the server."""
    from dotenv import load_dotenv
    from jarvis.api.main import _build_agent

    load_dotenv(override=True)
    logger.info("Config reloaded from .env")

    scheduler = app_state.get("scheduler")
    new_agent = _build_agent(scheduler=scheduler)
    app_state["agent"] = new_agent

    providers = list(new_agent.llm.available_providers)
    return ConfigReloadResponse(
        status="ok",
        providers=providers,
        message=f"Agent rebuilt. Active providers: {', '.join(providers)}",
    )


class ConfigResponse(BaseModel):
    default_llm: str
    ollama_model: str
    memory_enabled: bool
    wake_word_model: str
    tts_voice: str
    integrations_env: dict[str, bool]


@router.get("/config", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """Return current runtime configuration (no secrets)."""
    return ConfigResponse(
        default_llm=os.getenv("DEFAULT_LLM", "openai"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        memory_enabled=os.getenv("MEMORY_ENABLED", "true").lower() != "false",
        wake_word_model=os.getenv("WAKE_WORD_MODEL", "hey_jarvis"),
        tts_voice=os.getenv("TTS_VOICE", "en-US-AriaNeural"),
        integrations_env={
            "gmail": bool(os.getenv("GMAIL_CREDENTIALS_FILE")),
            "discord": bool(os.getenv("DISCORD_BOT_TOKEN")),
            "youtube": bool(os.getenv("YOUTUBE_API_KEY")),
            "instagram": bool(os.getenv("INSTAGRAM_USERNAME")),
            "google_calendar": bool(os.getenv("GOOGLE_CALENDAR_ID")),
            "google_drive": bool(os.getenv("GOOGLE_DRIVE_ENABLED")),
            "whatsapp": bool(os.getenv("WHATSAPP_ENABLED")),
            "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
            "spotify": bool(os.getenv("SPOTIPY_CLIENT_ID")),
            "slack": bool(os.getenv("SLACK_BOT_TOKEN")),
        },
    )
