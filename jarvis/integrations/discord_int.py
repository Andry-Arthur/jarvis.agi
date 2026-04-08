"""Discord integration — send and read messages via a bot token.

The bot requires the following permissions:
  - Send Messages
  - Read Message History
  - View Channels

Invite URL template:
  https://discord.com/api/oauth2/authorize?client_id=YOUR_APP_ID&permissions=68608&scope=bot
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

DISCORD_API = "https://discord.com/api/v10"


def _headers() -> dict[str, str]:
    token = os.getenv("DISCORD_BOT_TOKEN", "")
    return {"Authorization": f"Bot {token}", "Content-Type": "application/json"}


# ── Tools ─────────────────────────────────────────────────────────────────────


class DiscordSendTool(Tool):
    name = "discord_send_message"
    description = "Send a message to a Discord channel."
    parameters = {
        "type": "object",
        "properties": {
            "channel_id": {
                "type": "string",
                "description": "The Discord channel ID to send the message to.",
            },
            "message": {"type": "string", "description": "The text message to send."},
        },
        "required": ["channel_id", "message"],
    }

    async def run(self, channel_id: str, message: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                headers=_headers(),
                json={"content": message},
            )
        if r.status_code == 200:
            return f"Message sent to channel {channel_id}."
        return f"Failed to send message: {r.status_code} {r.text}"


class DiscordReadTool(Tool):
    name = "discord_read_channel"
    description = "Read recent messages from a Discord channel."
    parameters = {
        "type": "object",
        "properties": {
            "channel_id": {"type": "string", "description": "The Discord channel ID."},
            "limit": {
                "type": "integer",
                "description": "Number of recent messages to retrieve (default 10).",
                "default": 10,
            },
        },
        "required": ["channel_id"],
    }

    async def run(self, channel_id: str, limit: int = 10) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                headers=_headers(),
                params={"limit": min(limit, 100)},
            )
        if r.status_code != 200:
            return f"Failed to read channel: {r.status_code} {r.text}"

        messages = r.json()
        if not messages:
            return "No messages in this channel."

        lines = []
        for m in reversed(messages):
            author = m.get("author", {}).get("username", "unknown")
            content = m.get("content", "")
            lines.append(f"{author}: {content}")
        return "\n".join(lines)


class DiscordDMTool(Tool):
    name = "discord_send_dm"
    description = "Send a direct message to a Discord user by their user ID."
    parameters = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "description": "The Discord user ID."},
            "message": {"type": "string", "description": "The message text to send."},
        },
        "required": ["user_id", "message"],
    }

    async def run(self, user_id: str, message: str) -> str:
        async with httpx.AsyncClient() as client:
            # Open a DM channel first
            r = await client.post(
                f"{DISCORD_API}/users/@me/channels",
                headers=_headers(),
                json={"recipient_id": user_id},
            )
            if r.status_code != 200:
                return f"Could not open DM: {r.status_code} {r.text}"
            channel_id = r.json()["id"]

            # Send the message
            r2 = await client.post(
                f"{DISCORD_API}/channels/{channel_id}/messages",
                headers=_headers(),
                json={"content": message},
            )
        if r2.status_code == 200:
            return f"DM sent to user {user_id}."
        return f"Failed to send DM: {r2.status_code} {r2.text}"


# ── Integration bundle ────────────────────────────────────────────────────────


class DiscordIntegration(Integration):
    @property
    def name(self) -> str:
        return "Discord"

    def is_configured(self) -> bool:
        return bool(os.getenv("DISCORD_BOT_TOKEN"))

    def get_tools(self) -> list[Tool]:
        return [DiscordSendTool(), DiscordReadTool(), DiscordDMTool()]
