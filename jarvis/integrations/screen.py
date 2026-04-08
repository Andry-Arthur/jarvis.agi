"""Screen vision integration — capture and OCR the desktop.

Requires:
  pip install Pillow pytesseract mss
  Tesseract OCR binary: https://github.com/UB-Mannheim/tesseract/wiki (Windows)
                         brew install tesseract (macOS)
                         apt install tesseract-ocr (Linux)
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


class ScreenCaptureTool(Tool):
    name = "screen_capture"
    description = "Take a screenshot of the entire screen or a region and save it."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to save the screenshot (default: screen_capture.png)",
            },
            "monitor": {
                "type": "integer",
                "description": "Monitor index (0 = all monitors, 1 = primary, 2 = secondary, etc.)",
            },
        },
    }

    async def execute(self, path: str = "screen_capture.png", monitor: int = 1) -> str:
        try:
            import mss
            import mss.tools

            with mss.mss() as sct:
                if monitor == 0:
                    screenshot = sct.grab(sct.monitors[0])
                else:
                    idx = min(monitor, len(sct.monitors) - 1)
                    screenshot = sct.grab(sct.monitors[idx])
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)
            return f"Screenshot saved to: {path}"
        except Exception as exc:
            logger.error("screen_capture failed: %s", exc)
            return f"Error capturing screen: {exc}"


class ScreenReadTextTool(Tool):
    name = "screen_read_text"
    description = "Capture the screen and extract all visible text using OCR."
    parameters = {
        "type": "object",
        "properties": {
            "monitor": {"type": "integer", "description": "Monitor index (default 1)"},
            "lang": {
                "type": "string",
                "description": "OCR language code (default 'eng')",
            },
        },
    }

    async def execute(self, monitor: int = 1, lang: str = "eng") -> str:
        try:
            import mss
            import mss.tools
            import pytesseract
            from PIL import Image

            tesseract_cmd = os.getenv("TESSERACT_CMD", "")
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            with mss.mss() as sct:
                idx = min(monitor, len(sct.monitors) - 1)
                screenshot = sct.grab(sct.monitors[idx])
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            text = pytesseract.image_to_string(img, lang=lang)
            return text.strip() or "(no text detected)"
        except Exception as exc:
            logger.error("screen_read_text failed: %s", exc)
            return f"Error reading screen text: {exc}"


class ScreenFindElementTool(Tool):
    name = "screen_find_element"
    description = "Find the screen coordinates of an element matching a text string."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to search for on screen"},
            "monitor": {"type": "integer", "description": "Monitor index (default 1)"},
        },
        "required": ["text"],
    }

    async def execute(self, text: str, monitor: int = 1) -> str:
        try:
            import mss
            import pytesseract
            from PIL import Image

            tesseract_cmd = os.getenv("TESSERACT_CMD", "")
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            with mss.mss() as sct:
                idx = min(monitor, len(sct.monitors) - 1)
                screenshot = sct.grab(sct.monitors[idx])
                img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            matches = []
            for i, word in enumerate(data["text"]):
                if text.lower() in word.lower():
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    conf = data["conf"][i]
                    matches.append(f"'{word}' at ({x}, {y}) [confidence: {conf}%]")

            if not matches:
                return f"Text '{text}' not found on screen."
            return "\n".join(matches)
        except Exception as exc:
            logger.error("screen_find_element failed: %s", exc)
            return f"Error finding element: {exc}"


class ScreenIntegration(Integration):
    name = "screen"

    def is_configured(self) -> bool:
        try:
            import mss  # noqa: F401
            return True
        except ImportError:
            return False

    def get_tools(self) -> list[Tool]:
        return [ScreenCaptureTool(), ScreenReadTextTool(), ScreenFindElementTool()]
