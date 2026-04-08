"""WhatsApp integration via whatsapp-web.py (puppeteer-based, free).

Set WHATSAPP_ENABLED=true in .env to activate.
On first run it will display a QR code in the terminal; scan with WhatsApp.
"""

from __future__ import annotations

import asyncio
import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

_client = None
_client_ready = asyncio.Event()


def _get_client():
    global _client
    if _client is not None:
        return _client

    try:
        from whatsapp import WhatsApp  # type: ignore[import]

        _client = WhatsApp()

        @_client.on_ready
        def on_ready():
            logger.info("WhatsApp client ready.")
            _client_ready.set()

        _client.initialize()
    except ImportError:
        logger.warning("whatsapp-web.py not installed. Run: pip install whatsapp-web.py")
        _client = None

    return _client


class WhatsAppSendMessageTool(Tool):
    name = "whatsapp_send_message"
    description = "Send a WhatsApp message to a phone number or contact."
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Phone number with country code (e.g. +1234567890) or contact name",
            },
            "message": {"type": "string", "description": "Text to send"},
        },
        "required": ["to", "message"],
    }

    async def execute(self, to: str, message: str) -> str:
        try:
            client = _get_client()
            if client is None:
                return "WhatsApp client not available. Install whatsapp-web.py."
            await asyncio.wait_for(_client_ready.wait(), timeout=30)
            client.send_message(to, message)
            return f"WhatsApp message sent to {to}."
        except Exception as exc:
            logger.error("whatsapp_send_message failed: %s", exc)
            return f"Error sending WhatsApp message: {exc}"


class WhatsAppReadMessagesTool(Tool):
    name = "whatsapp_read_messages"
    description = "Read recent WhatsApp messages from a chat."
    parameters = {
        "type": "object",
        "properties": {
            "contact": {"type": "string", "description": "Contact name or phone number"},
            "limit": {"type": "integer", "description": "Number of recent messages (default 10)"},
        },
        "required": ["contact"],
    }

    async def execute(self, contact: str, limit: int = 10) -> str:
        try:
            client = _get_client()
            if client is None:
                return "WhatsApp client not available."
            chats = client.get_chats()
            for chat in chats:
                if contact.lower() in chat.name.lower():
                    messages = chat.fetch_messages(limit=limit)
                    lines = [
                        f"[{m.timestamp}] {m.author or 'Me'}: {m.body}"
                        for m in messages
                    ]
                    return "\n".join(lines) or "No messages found."
            return f"No chat found for '{contact}'."
        except Exception as exc:
            logger.error("whatsapp_read_messages failed: %s", exc)
            return f"Error reading WhatsApp messages: {exc}"


class WhatsAppSendToGroupTool(Tool):
    name = "whatsapp_send_to_group"
    description = "Send a WhatsApp message to a group chat."
    parameters = {
        "type": "object",
        "properties": {
            "group_name": {"type": "string", "description": "Group chat name"},
            "message": {"type": "string", "description": "Text to send"},
        },
        "required": ["group_name", "message"],
    }

    async def execute(self, group_name: str, message: str) -> str:
        try:
            client = _get_client()
            if client is None:
                return "WhatsApp client not available."
            groups = [c for c in client.get_chats() if c.is_group]
            for group in groups:
                if group_name.lower() in group.name.lower():
                    group.send_message(message)
                    return f"Message sent to group '{group.name}'."
            return f"Group '{group_name}' not found."
        except Exception as exc:
            logger.error("whatsapp_send_to_group failed: %s", exc)
            return f"Error sending to group: {exc}"


class WhatsAppIntegration(Integration):
    name = "whatsapp"

    def is_configured(self) -> bool:
        return os.getenv("WHATSAPP_ENABLED", "").lower() in ("1", "true", "yes")

    def get_tools(self) -> list[Tool]:
        return [
            WhatsAppSendMessageTool(),
            WhatsAppReadMessagesTool(),
            WhatsAppSendToGroupTool(),
        ]
