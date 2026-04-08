"""Slack integration via slack-sdk.

Required env vars:
  SLACK_BOT_TOKEN   — Bot OAuth token (xoxb-...)
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _client():
    from slack_sdk.web.async_client import AsyncWebClient

    return AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])


class SlackSendMessageTool(Tool):
    name = "slack_send_message"
    description = "Send a message to a Slack channel or user."
    parameters = {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "Channel name (e.g. #general) or user ID"},
            "text": {"type": "string", "description": "Message text (supports Markdown)"},
        },
        "required": ["channel", "text"],
    }

    async def execute(self, channel: str, text: str) -> str:
        try:
            client = _client()
            await client.chat_postMessage(channel=channel, text=text)
            return f"Message sent to {channel}."
        except Exception as exc:
            logger.error("slack_send_message failed: %s", exc)
            return f"Error sending Slack message: {exc}"


class SlackReadChannelTool(Tool):
    name = "slack_read_channel"
    description = "Read recent messages from a Slack channel."
    parameters = {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "Channel name or ID"},
            "limit": {"type": "integer", "description": "Number of messages (default 10)"},
        },
        "required": ["channel"],
    }

    async def execute(self, channel: str, limit: int = 10) -> str:
        try:
            client = _client()
            # Resolve channel name to ID if needed
            channel_id = channel
            if channel.startswith("#"):
                resp = await client.conversations_list(types="public_channel,private_channel")
                for ch in resp["channels"]:
                    if ch["name"] == channel.lstrip("#"):
                        channel_id = ch["id"]
                        break

            history = await client.conversations_history(channel=channel_id, limit=limit)
            messages = history.get("messages", [])
            if not messages:
                return f"No messages found in {channel}."
            lines = []
            for msg in reversed(messages):
                user = msg.get("user", "unknown")
                text = msg.get("text", "(no text)")
                ts = msg.get("ts", "")
                lines.append(f"[{ts}] {user}: {text}")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("slack_read_channel failed: %s", exc)
            return f"Error reading Slack channel: {exc}"


class SlackListChannelsTool(Tool):
    name = "slack_list_channels"
    description = "List available Slack channels."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Max channels to return (default 20)"},
        },
    }

    async def execute(self, limit: int = 20) -> str:
        try:
            client = _client()
            resp = await client.conversations_list(
                types="public_channel,private_channel", limit=limit
            )
            channels = resp.get("channels", [])
            if not channels:
                return "No channels found."
            lines = [f"• #{ch['name']} (ID: {ch['id']})" for ch in channels]
            return "\n".join(lines)
        except Exception as exc:
            logger.error("slack_list_channels failed: %s", exc)
            return f"Error listing channels: {exc}"


class SlackIntegration(Integration):
    name = "slack"

    def is_configured(self) -> bool:
        return bool(os.getenv("SLACK_BOT_TOKEN"))

    def get_tools(self) -> list[Tool]:
        return [
            SlackSendMessageTool(),
            SlackReadChannelTool(),
            SlackListChannelsTool(),
        ]
