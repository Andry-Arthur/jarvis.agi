"""Instagram integration via Instagram Graph API.

Requires a long-lived access token from Meta for Developers:
  https://developers.facebook.com/docs/instagram-api/getting-started

Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_USER_ID in your .env file.
"""

from __future__ import annotations

import logging
import os

import httpx

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

GRAPH_API = "https://graph.instagram.com/v20.0"


def _token() -> str:
    return os.getenv("INSTAGRAM_ACCESS_TOKEN", "")


def _user_id() -> str:
    return os.getenv("INSTAGRAM_USER_ID", "")


# ── Tools ─────────────────────────────────────────────────────────────────────


class InstagramReadDMTool(Tool):
    name = "instagram_read_dms"
    description = "Read recent Instagram direct messages (DMs) from your inbox."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of recent conversations to fetch (default 5).",
                "default": 5,
            }
        },
    }

    async def execute(self, limit: int = 5) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GRAPH_API}/{_user_id()}/conversations",
                params={
                    "fields": "participants,messages{message,from,created_time}",
                    "access_token": _token(),
                    "limit": limit,
                },
            )
        if r.status_code != 200:
            return f"Instagram API error: {r.status_code} {r.text}"

        data = r.json().get("data", [])
        if not data:
            return "No Instagram DMs found."

        summaries = []
        for convo in data:
            participants = [p["username"] for p in convo.get("participants", {}).get("data", [])]
            messages = convo.get("messages", {}).get("data", [])
            latest = messages[0] if messages else {}
            summaries.append(
                f"Conversation with: {', '.join(participants)}\n"
                f"Latest message: {latest.get('message', '')}\n"
                f"From: {latest.get('from', {}).get('name', '?')}\n"
                f"At: {latest.get('created_time', '?')}"
            )
        return "\n---\n".join(summaries)


class InstagramSendDMTool(Tool):
    name = "instagram_send_dm"
    description = "Send a direct message to an Instagram user."
    parameters = {
        "type": "object",
        "properties": {
            "recipient_id": {
                "type": "string",
                "description": "The Instagram-scoped user ID of the recipient.",
            },
            "message": {"type": "string", "description": "The text message to send."},
        },
        "required": ["recipient_id", "message"],
    }

    async def execute(self, recipient_id: str, message: str) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GRAPH_API}/{_user_id()}/messages",
                params={"access_token": _token()},
                json={
                    "recipient": {"id": recipient_id},
                    "message": {"text": message},
                },
            )
        if r.status_code == 200:
            return f"DM sent to Instagram user {recipient_id}."
        return f"Failed to send DM: {r.status_code} {r.text}"


class InstagramPostsTool(Tool):
    name = "instagram_get_posts"
    description = "Retrieve recent posts from your own Instagram account."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of posts to fetch.", "default": 5}
        },
    }

    async def execute(self, limit: int = 5) -> str:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{GRAPH_API}/{_user_id()}/media",
                params={
                    "fields": "id,caption,media_type,timestamp,permalink",
                    "access_token": _token(),
                    "limit": limit,
                },
            )
        if r.status_code != 200:
            return f"Instagram API error: {r.status_code} {r.text}"

        posts = r.json().get("data", [])
        if not posts:
            return "No posts found."

        lines = []
        for p in posts:
            lines.append(
                f"[{p.get('media_type', '?')}] {p.get('timestamp', '')}\n"
                f"Caption: {(p.get('caption') or '')[:200]}\n"
                f"Link: {p.get('permalink', '')}"
            )
        return "\n---\n".join(lines)


# ── Integration bundle ────────────────────────────────────────────────────────


class InstagramIntegration(Integration):
    @property
    def name(self) -> str:
        return "Instagram"

    def is_configured(self) -> bool:
        return bool(_token() and _user_id())

    def get_tools(self) -> list[Tool]:
        return [InstagramReadDMTool(), InstagramSendDMTool(), InstagramPostsTool()]
