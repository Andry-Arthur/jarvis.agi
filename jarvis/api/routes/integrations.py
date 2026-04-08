"""Integration status and management endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get("")
async def list_integrations():
    """Return the status of all configured integrations."""
    from jarvis.integrations.gmail import GmailIntegration
    from jarvis.integrations.discord_int import DiscordIntegration
    from jarvis.integrations.youtube import YouTubeIntegration
    from jarvis.integrations.instagram import InstagramIntegration

    integrations = [
        GmailIntegration(),
        DiscordIntegration(),
        YouTubeIntegration(),
        InstagramIntegration(),
    ]
    return {"integrations": [i.status() for i in integrations]}


@router.get("/tools")
async def list_tools():
    """Return all tools currently registered in the agent."""
    from jarvis.api.main import app_state

    agent = app_state.get("agent")
    if agent is None:
        return {"tools": []}
    schemas = agent.tools.get_all_schemas()
    return {"tools": [s["function"] for s in schemas]}
