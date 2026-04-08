"""Notion integration via notion-client.

Required env vars:
  NOTION_TOKEN  — Integration token from https://www.notion.so/my-integrations
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _client():
    from notion_client import AsyncClient  # type: ignore[import]

    return AsyncClient(auth=os.environ["NOTION_TOKEN"])


class NotionSearchTool(Tool):
    name = "notion_search"
    description = "Search Notion pages and databases."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results (default 5)"},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, max_results: int = 5) -> str:
        try:
            client = _client()
            results = await client.search(query=query, page_size=max_results)
            items = results.get("results", [])
            if not items:
                return f"No Notion pages found for '{query}'."
            lines = []
            for item in items:
                obj_type = item.get("object", "unknown")
                title = _extract_title(item)
                page_id = item["id"]
                lines.append(f"• [{obj_type}] {title} (ID: {page_id})")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("notion_search failed: %s", exc)
            return f"Error searching Notion: {exc}"


class NotionReadPageTool(Tool):
    name = "notion_read_page"
    description = "Read the content of a Notion page by its ID."
    parameters = {
        "type": "object",
        "properties": {
            "page_id": {"type": "string", "description": "Notion page ID"},
        },
        "required": ["page_id"],
    }

    async def execute(self, page_id: str) -> str:
        try:
            client = _client()
            blocks = await client.blocks.children.list(block_id=page_id)
            texts = []
            for block in blocks.get("results", []):
                block_type = block.get("type", "")
                content = block.get(block_type, {})
                rich_text = content.get("rich_text", [])
                text = "".join(rt.get("plain_text", "") for rt in rich_text)
                if text:
                    texts.append(text)
            return "\n".join(texts) or "(empty page)"
        except Exception as exc:
            logger.error("notion_read_page failed: %s", exc)
            return f"Error reading Notion page: {exc}"


class NotionCreatePageTool(Tool):
    name = "notion_create_page"
    description = "Create a new Notion page in a parent database or page."
    parameters = {
        "type": "object",
        "properties": {
            "parent_id": {"type": "string", "description": "Parent database or page ID"},
            "title": {"type": "string", "description": "Page title"},
            "content": {"type": "string", "description": "Page content (plain text)"},
            "is_database": {
                "type": "boolean",
                "description": "True if parent is a database (default false)",
            },
        },
        "required": ["parent_id", "title"],
    }

    async def execute(
        self,
        parent_id: str,
        title: str,
        content: str = "",
        is_database: bool = False,
    ) -> str:
        try:
            client = _client()
            parent_key = "database_id" if is_database else "page_id"
            body: dict = {
                "parent": {parent_key: parent_id},
                "properties": {
                    "title": {"title": [{"text": {"content": title}}]}
                },
            }
            if content:
                body["children"] = [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": content}}]
                        },
                    }
                ]
            result = await client.pages.create(**body)
            return f"Notion page created: {result.get('url', result['id'])}"
        except Exception as exc:
            logger.error("notion_create_page failed: %s", exc)
            return f"Error creating Notion page: {exc}"


def _extract_title(item: dict) -> str:
    props = item.get("properties", {})
    for prop in props.values():
        if prop.get("type") == "title":
            rich_text = prop.get("title", [])
            return "".join(rt.get("plain_text", "") for rt in rich_text)
    return item.get("id", "Untitled")


class NotionIntegration(Integration):
    name = "notion"

    def is_configured(self) -> bool:
        return bool(os.getenv("NOTION_TOKEN"))

    def get_tools(self) -> list[Tool]:
        return [NotionSearchTool(), NotionReadPageTool(), NotionCreatePageTool()]
