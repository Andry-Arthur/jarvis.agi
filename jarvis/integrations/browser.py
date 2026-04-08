"""Web browser control via Playwright.

Install: pip install playwright && playwright install chromium

Set BROWSER_HEADLESS=false to see the browser window.
"""

from __future__ import annotations

import logging
import os
from typing import ClassVar

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() != "false"
_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT_MS", "15000"))


async def _get_page():
    """Get or create a persistent Playwright browser page."""
    from playwright.async_api import async_playwright

    # Use a module-level context so we don't launch a new browser per tool call
    if not hasattr(_get_page, "_browser"):
        _get_page._pw = await async_playwright().start()
        _get_page._browser = await _get_page._pw.chromium.launch(headless=_HEADLESS)
        _get_page._context = await _get_page._browser.new_context()
        _get_page._page = await _get_page._context.new_page()
        _get_page._page.set_default_timeout(_TIMEOUT)
    return _get_page._page


class BrowserNavigateTool(Tool):
    name = "browser_navigate"
    description = "Navigate the browser to a URL and return the page title."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to navigate to"},
        },
        "required": ["url"],
    }

    async def execute(self, url: str) -> str:
        try:
            page = await _get_page()
            await page.goto(url, wait_until="domcontentloaded")
            title = await page.title()
            return f"Navigated to: {url}\nTitle: {title}"
        except Exception as exc:
            logger.error("browser_navigate failed: %s", exc)
            return f"Error navigating to {url}: {exc}"


class BrowserClickTool(Tool):
    name = "browser_click"
    description = "Click an element on the current page using a CSS selector or text."
    parameters = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector, XPath, or visible text of the element to click",
            },
        },
        "required": ["selector"],
    }

    async def execute(self, selector: str) -> str:
        try:
            page = await _get_page()
            await page.click(selector)
            return f"Clicked: {selector}"
        except Exception as exc:
            logger.error("browser_click failed: %s", exc)
            return f"Error clicking '{selector}': {exc}"


class BrowserTypeTool(Tool):
    name = "browser_type"
    description = "Type text into a form field identified by a CSS selector."
    parameters = {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the input field"},
            "text": {"type": "string", "description": "Text to type"},
            "clear_first": {
                "type": "boolean",
                "description": "Clear the field before typing (default true)",
            },
        },
        "required": ["selector", "text"],
    }

    async def execute(self, selector: str, text: str, clear_first: bool = True) -> str:
        try:
            page = await _get_page()
            if clear_first:
                await page.fill(selector, "")
            await page.type(selector, text)
            return f"Typed '{text}' into {selector}"
        except Exception as exc:
            logger.error("browser_type failed: %s", exc)
            return f"Error typing into '{selector}': {exc}"


class BrowserScreenshotTool(Tool):
    name = "browser_screenshot"
    description = "Take a screenshot of the current browser page and save it."
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to save screenshot (default: screenshot.png)",
            },
        },
    }

    async def execute(self, path: str = "screenshot.png") -> str:
        try:
            page = await _get_page()
            await page.screenshot(path=path, full_page=True)
            return f"Screenshot saved to: {path}"
        except Exception as exc:
            logger.error("browser_screenshot failed: %s", exc)
            return f"Error taking screenshot: {exc}"


class BrowserExtractTextTool(Tool):
    name = "browser_extract_text"
    description = "Extract all visible text from the current page or a specific element."
    parameters = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector to extract text from (default: body)",
            },
            "max_chars": {
                "type": "integer",
                "description": "Maximum characters to return (default 5000)",
            },
        },
    }

    async def execute(self, selector: str = "body", max_chars: int = 5000) -> str:
        try:
            page = await _get_page()
            text = await page.inner_text(selector)
            if len(text) > max_chars:
                text = text[:max_chars] + "...[truncated]"
            return text
        except Exception as exc:
            logger.error("browser_extract_text failed: %s", exc)
            return f"Error extracting text: {exc}"


class BrowserFillFormTool(Tool):
    name = "browser_fill_form"
    description = "Fill multiple form fields at once and optionally submit."
    parameters = {
        "type": "object",
        "properties": {
            "fields": {
                "type": "object",
                "description": "Dict of {css_selector: value} pairs to fill",
            },
            "submit_selector": {
                "type": "string",
                "description": "Optional CSS selector of the submit button",
            },
        },
        "required": ["fields"],
    }

    async def execute(self, fields: dict, submit_selector: str = "") -> str:
        try:
            page = await _get_page()
            for selector, value in fields.items():
                await page.fill(selector, str(value))
            if submit_selector:
                await page.click(submit_selector)
                await page.wait_for_load_state("domcontentloaded")
                return f"Form filled and submitted. New page: {page.url}"
            return f"Filled {len(fields)} fields."
        except Exception as exc:
            logger.error("browser_fill_form failed: %s", exc)
            return f"Error filling form: {exc}"


class BrowserIntegration(Integration):
    name = "browser"

    def is_configured(self) -> bool:
        try:
            import playwright  # noqa: F401
            return True
        except ImportError:
            return False

    def get_tools(self) -> list[Tool]:
        return [
            BrowserNavigateTool(),
            BrowserClickTool(),
            BrowserTypeTool(),
            BrowserScreenshotTool(),
            BrowserExtractTextTool(),
            BrowserFillFormTool(),
        ]
