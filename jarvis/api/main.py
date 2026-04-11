"""FastAPI application factory and startup."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Shared application state (agent, registry, etc.)
app_state: dict = {}


def _build_agent(scheduler=None):
    """Construct the agent with all configured tools."""
    from jarvis.core.agent import Agent
    from jarvis.core.memory import Memory
    from jarvis.core.tools import ToolRegistry
    from jarvis.llm.router import LLMRouter

    # LLM router
    router = LLMRouter.from_env()
    logger.info("LLM providers: %s", router.available_providers)

    # Tool registry — only register tools from configured integrations
    registry = ToolRegistry()

    from jarvis.integrations.browser import BrowserIntegration
    from jarvis.integrations.code_exec import CodeExecIntegration
    from jarvis.integrations.computer_control import ComputerControlIntegration
    from jarvis.integrations.discord_int import DiscordIntegration
    from jarvis.integrations.filesystem import FilesystemIntegration
    from jarvis.integrations.gmail import GmailIntegration
    from jarvis.integrations.google_calendar import GoogleCalendarIntegration
    from jarvis.integrations.google_drive import GoogleDriveIntegration
    from jarvis.integrations.instagram import InstagramIntegration
    from jarvis.integrations.knowledge_base import KnowledgeBaseIntegration
    from jarvis.integrations.screen import ScreenIntegration
    from jarvis.integrations.slack import SlackIntegration
    from jarvis.integrations.spotify import SpotifyIntegration
    from jarvis.integrations.telegram import TelegramIntegration
    from jarvis.integrations.whatsapp import WhatsAppIntegration
    from jarvis.integrations.youtube import YouTubeIntegration

    # Phase 5 integrations
    from jarvis.integrations.finance import FinanceIntegration
    from jarvis.integrations.github_int import GitHubIntegration
    from jarvis.integrations.home_assistant import HomeAssistantIntegration
    from jarvis.integrations.news import NewsIntegration
    from jarvis.integrations.notion import NotionIntegration
    from jarvis.integrations.weather import WeatherIntegration

    integrations = [
        GmailIntegration(),
        DiscordIntegration(),
        YouTubeIntegration(),
        InstagramIntegration(),
        # Phase 2
        GoogleCalendarIntegration(),
        GoogleDriveIntegration(),
        WhatsAppIntegration(),
        TelegramIntegration(),
        SpotifyIntegration(),
        SlackIntegration(),
        # Phase 3
        BrowserIntegration(),
        FilesystemIntegration(),
        CodeExecIntegration(),
        ScreenIntegration(),
        ComputerControlIntegration(),
        # Phase 4
        KnowledgeBaseIntegration(),
        # Phase 5
        WeatherIntegration(),
        NewsIntegration(),
        NotionIntegration(),
        GitHubIntegration(),
        HomeAssistantIntegration(),
        FinanceIntegration(),
    ]
    for integration in integrations:
        if integration.is_configured():
            registry.register_many(integration.get_tools())
            logger.info("Loaded integration: %s", integration.name)
        else:
            logger.info("Skipping unconfigured integration: %s", integration.name)

    # Scheduler tools
    if scheduler is not None:
        from jarvis.core.scheduler import (
            CancelReminderTool,
            ListRemindersTool,
            ReminderTool,
        )

        registry.register_many(
            [
                ReminderTool(scheduler),
                ListRemindersTool(scheduler),
                CancelReminderTool(scheduler),
            ]
        )
        logger.info("Scheduler tools registered.")

    # Memory
    memory_enabled = os.getenv("MEMORY_ENABLED", "true").lower() != "false"
    memory = Memory() if memory_enabled else None

    return Agent(llm_router=router, tool_registry=registry, memory=memory)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from dotenv import load_dotenv
    from jarvis.agi.world_model import WorldModel
    from jarvis.core.scheduler import TaskScheduler
    from jarvis.plugins.loader import PluginLoader

    load_dotenv()

    scheduler = TaskScheduler()
    scheduler.start()
    app_state["scheduler"] = scheduler

    agent = _build_agent(scheduler=scheduler)
    app_state["agent"] = agent

    # Load user plugins
    plugin_loader = PluginLoader()
    n_tools = plugin_loader.load_all(agent.tools)
    if n_tools:
        logger.info("Loaded %d tool(s) from plugins.", n_tools)
    app_state["plugin_loader"] = plugin_loader

    # World model
    world_model = WorldModel()
    app_state["world_model"] = world_model

    app_state["ws_clients"] = set()

    from jarvis.api.ws import broadcast_proactive_notification
    from jarvis.core.autonomous_bootstrap import start_autonomous, stop_autonomous
    from jarvis.core.autonomous_config import load_autonomous_settings
    from jarvis.core.proactive import notification_bus

    async def _push_notifications(notification):
        await broadcast_proactive_notification(notification)

    notification_bus.subscribe(_push_notifications)

    autonomous_cfg = load_autonomous_settings()
    start_autonomous(app_state, autonomous_cfg)

    logger.info("JARVIS.AGI API ready.")
    yield
    stop_autonomous(app_state)
    notification_bus.clear_subscribers()
    scheduler.stop()
    app_state.clear()


def create_app() -> FastAPI:
    from dotenv import load_dotenv

    load_dotenv()

    cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    cors_origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]

    app = FastAPI(
        title="JARVIS.AGI",
        description="Free, self-hosted AI agent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routes
    from jarvis.api.routes.agi import router as agi_router
    from jarvis.api.routes.chat import router as chat_router
    from jarvis.api.routes.config import router as config_router
    from jarvis.api.routes.integrations import router as integrations_router
    from jarvis.api.routes.proactive import router as proactive_router
    from jarvis.api.routes.reminders import router as reminders_router
    from jarvis.api.routes.voice import router as voice_router

    app.include_router(chat_router, prefix="/api")
    app.include_router(voice_router, prefix="/api")
    app.include_router(integrations_router, prefix="/api")
    app.include_router(reminders_router, prefix="/api")
    app.include_router(config_router, prefix="/api")
    app.include_router(proactive_router, prefix="/api")
    app.include_router(agi_router, prefix="/api")

    # WebSocket
    from jarvis.api.ws import handle_websocket

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        await handle_websocket(ws)

    @app.get("/")
    async def root():
        return {"name": "JARVIS.AGI", "version": "0.1.0", "status": "running"}

    return app
