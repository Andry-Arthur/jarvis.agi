"""Hot-reload configuration endpoint."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter
from pydantic import BaseModel

from jarvis.api.main import app_state

logger = logging.getLogger(__name__)
router = APIRouter(tags=["config"])


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
