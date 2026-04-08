"""Telegram integration via python-telegram-bot.

Required env vars:
  TELEGRAM_BOT_TOKEN  — BotFather token
  TELEGRAM_CHAT_ID    — Default chat ID to send to (optional)
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _bot():
    from telegram import Bot

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return Bot(token=token)


class TelegramSendMessageTool(Tool):
    name = "telegram_send_message"
    description = "Send a Telegram message to a chat or user."
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {
                "type": "string",
                "description": "Telegram chat ID or @username (uses TELEGRAM_CHAT_ID if omitted)",
            },
            "text": {"type": "string", "description": "Message text (supports Markdown)"},
        },
        "required": ["text"],
    }

    async def execute(self, text: str, chat_id: str = "") -> str:
        try:
            bot = _bot()
            target = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
            if not target:
                return "No chat_id provided and TELEGRAM_CHAT_ID not set."
            await bot.send_message(chat_id=target, text=text, parse_mode="Markdown")
            return f"Message sent to {target}."
        except Exception as exc:
            logger.error("telegram_send_message failed: %s", exc)
            return f"Error sending Telegram message: {exc}"


class TelegramReadUpdatesTool(Tool):
    name = "telegram_read_updates"
    description = "Read recent incoming Telegram messages (updates)."
    parameters = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of updates to fetch (default 10)"},
        },
    }

    async def execute(self, limit: int = 10) -> str:
        try:
            bot = _bot()
            updates = await bot.get_updates(limit=limit)
            if not updates:
                return "No recent Telegram updates."
            lines = []
            for upd in updates:
                msg = upd.message
                if msg:
                    sender = msg.from_user.username or msg.from_user.first_name if msg.from_user else "unknown"
                    lines.append(f"[{msg.date}] @{sender}: {msg.text or '(no text)'}")
            return "\n".join(lines) or "No text messages found."
        except Exception as exc:
            logger.error("telegram_read_updates failed: %s", exc)
            return f"Error reading updates: {exc}"


class TelegramSendFileTool(Tool):
    name = "telegram_send_file"
    description = "Send a local file via Telegram."
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {"type": "string", "description": "Telegram chat ID"},
            "file_path": {"type": "string", "description": "Local path to file"},
            "caption": {"type": "string", "description": "Optional caption"},
        },
        "required": ["file_path"],
    }

    async def execute(self, file_path: str, chat_id: str = "", caption: str = "") -> str:
        try:
            bot = _bot()
            target = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
            if not target:
                return "No chat_id provided."
            with open(file_path, "rb") as f:
                await bot.send_document(chat_id=target, document=f, caption=caption or None)
            return f"File '{file_path}' sent to {target}."
        except Exception as exc:
            logger.error("telegram_send_file failed: %s", exc)
            return f"Error sending file: {exc}"


class TelegramIntegration(Integration):
    name = "telegram"

    def is_configured(self) -> bool:
        return bool(os.getenv("TELEGRAM_BOT_TOKEN"))

    def get_tools(self) -> list[Tool]:
        return [
            TelegramSendMessageTool(),
            TelegramReadUpdatesTool(),
            TelegramSendFileTool(),
        ]
