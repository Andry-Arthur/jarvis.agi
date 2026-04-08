"""Computer control via pyautogui — mouse, keyboard, and screenshot automation.

Install: pip install pyautogui

IMPORTANT: pyautogui moves the actual mouse and types keystrokes. Always
confirm with the user before executing potentially destructive actions.
"""

from __future__ import annotations

import asyncio
import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

# Safety pause between pyautogui actions (seconds)
_PAUSE = float(os.getenv("PYAUTOGUI_PAUSE", "0.1"))


def _gui():
    import pyautogui

    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to abort
    pyautogui.PAUSE = _PAUSE
    return pyautogui


class MouseClickTool(Tool):
    name = "mouse_click"
    description = "Click at specific screen coordinates or on an image template."
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate"},
            "y": {"type": "integer", "description": "Y coordinate"},
            "button": {
                "type": "string",
                "description": "Mouse button: 'left', 'right', or 'middle' (default 'left')",
            },
            "clicks": {"type": "integer", "description": "Number of clicks (default 1)"},
        },
        "required": ["x", "y"],
    }

    async def execute(
        self, x: int, y: int, button: str = "left", clicks: int = 1
    ) -> str:
        try:
            gui = _gui()
            await asyncio.to_thread(gui.click, x, y, button=button, clicks=clicks)
            return f"Clicked at ({x}, {y}) with {button} button ({clicks}x)"
        except Exception as exc:
            logger.error("mouse_click failed: %s", exc)
            return f"Error clicking: {exc}"


class KeyboardTypeTool(Tool):
    name = "keyboard_type"
    description = "Type text at the current cursor position."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type"},
            "interval": {
                "type": "number",
                "description": "Seconds between keystrokes (default 0.05)",
            },
        },
        "required": ["text"],
    }

    async def execute(self, text: str, interval: float = 0.05) -> str:
        try:
            gui = _gui()
            await asyncio.to_thread(gui.typewrite, text, interval=interval)
            return f"Typed: {text}"
        except Exception as exc:
            logger.error("keyboard_type failed: %s", exc)
            return f"Error typing: {exc}"


class KeyboardHotkeyTool(Tool):
    name = "keyboard_hotkey"
    description = "Press a keyboard hotkey combination (e.g. ctrl+c, alt+tab)."
    parameters = {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of keys to press together (e.g. ['ctrl', 'c'])",
            },
        },
        "required": ["keys"],
    }

    async def execute(self, keys: list) -> str:
        try:
            gui = _gui()
            await asyncio.to_thread(gui.hotkey, *keys)
            return f"Pressed hotkey: {'+'.join(keys)}"
        except Exception as exc:
            logger.error("keyboard_hotkey failed: %s", exc)
            return f"Error pressing hotkey: {exc}"


class MouseMoveTool(Tool):
    name = "mouse_move"
    description = "Move the mouse cursor to specific screen coordinates."
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate"},
            "y": {"type": "integer", "description": "Y coordinate"},
            "duration": {
                "type": "number",
                "description": "Movement duration in seconds (default 0.25)",
            },
        },
        "required": ["x", "y"],
    }

    async def execute(self, x: int, y: int, duration: float = 0.25) -> str:
        try:
            gui = _gui()
            await asyncio.to_thread(gui.moveTo, x, y, duration=duration)
            return f"Mouse moved to ({x}, {y})"
        except Exception as exc:
            logger.error("mouse_move failed: %s", exc)
            return f"Error moving mouse: {exc}"


class TakeScreenshotTool(Tool):
    name = "take_screenshot"
    description = "Take a screenshot of the full screen and save it."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Save path (default: screenshot.png)"},
        },
    }

    async def execute(self, path: str = "screenshot.png") -> str:
        try:
            gui = _gui()
            img = await asyncio.to_thread(gui.screenshot)
            img.save(path)
            return f"Screenshot saved to: {path}"
        except Exception as exc:
            logger.error("take_screenshot failed: %s", exc)
            return f"Error taking screenshot: {exc}"


class ScrollTool(Tool):
    name = "scroll"
    description = "Scroll the mouse wheel at a position."
    parameters = {
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate to scroll at"},
            "y": {"type": "integer", "description": "Y coordinate to scroll at"},
            "clicks": {
                "type": "integer",
                "description": "Number of scroll clicks (positive = up, negative = down)",
            },
        },
        "required": ["clicks"],
    }

    async def execute(self, clicks: int, x: int = -1, y: int = -1) -> str:
        try:
            gui = _gui()
            if x >= 0 and y >= 0:
                await asyncio.to_thread(gui.scroll, clicks, x=x, y=y)
            else:
                await asyncio.to_thread(gui.scroll, clicks)
            return f"Scrolled {clicks} clicks"
        except Exception as exc:
            logger.error("scroll failed: %s", exc)
            return f"Error scrolling: {exc}"


class ComputerControlIntegration(Integration):
    name = "computer_control"

    def is_configured(self) -> bool:
        try:
            import pyautogui  # noqa: F401
            return True
        except ImportError:
            return False

    def get_tools(self) -> list[Tool]:
        return [
            MouseClickTool(),
            KeyboardTypeTool(),
            KeyboardHotkeyTool(),
            MouseMoveTool(),
            TakeScreenshotTool(),
            ScrollTool(),
        ]
