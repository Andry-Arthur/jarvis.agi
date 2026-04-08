"""News integration via NewsAPI and RSS feeds.

NEWSAPI_KEY is optional — without it, JARVIS falls back to public RSS feeds.
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

_DEFAULT_RSS_FEEDS = {
    "world": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "tech": "https://feeds.arstechnica.com/arstechnica/index",
    "science": "https://www.sciencedaily.com/rss/all.xml",
    "business": "https://feeds.bbci.co.uk/news/business/rss.xml",
}


class NewsHeadlinesTool(Tool):
    name = "news_headlines"
    description = "Get the latest news headlines on a topic or from a category."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Topic to search (e.g. 'AI', 'stock market')",
            },
            "category": {
                "type": "string",
                "description": "Category: world, tech, science, business (used as fallback)",
            },
            "max_results": {"type": "integer", "description": "Max articles (default 5)"},
        },
    }

    async def execute(
        self, query: str = "", category: str = "world", max_results: int = 5
    ) -> str:
        api_key = os.getenv("NEWSAPI_KEY", "")
        if api_key:
            return await self._from_newsapi(query, max_results, api_key)
        return await self._from_rss(category, max_results)

    async def _from_newsapi(self, query: str, max_results: int, api_key: str) -> str:
        try:
            import httpx

            params: dict = {"apiKey": api_key, "pageSize": max_results, "language": "en"}
            if query:
                url = "https://newsapi.org/v2/everything"
                params["q"] = query
                params["sortBy"] = "publishedAt"
            else:
                url = "https://newsapi.org/v2/top-headlines"
                params["country"] = "us"

            resp = httpx.get(url, params=params, timeout=10)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            if not articles:
                return "No news articles found."
            lines = [
                f"• {a['title']} — {a['source']['name']} ({a.get('publishedAt', '')[:10]})"
                for a in articles
            ]
            return "\n".join(lines)
        except Exception as exc:
            logger.error("NewsAPI failed: %s", exc)
            return f"Error fetching news: {exc}"

    async def _from_rss(self, category: str, max_results: int) -> str:
        try:
            import xml.etree.ElementTree as ET

            import httpx

            feed_url = _DEFAULT_RSS_FEEDS.get(category, _DEFAULT_RSS_FEEDS["world"])
            resp = httpx.get(feed_url, timeout=10, follow_redirects=True)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")[:max_results]
            lines = []
            for item in items:
                title = item.findtext("title", "").strip()
                pub_date = item.findtext("pubDate", "")[:16]
                lines.append(f"• {title} ({pub_date})")
            return "\n".join(lines) or "No articles found."
        except Exception as exc:
            logger.error("RSS feed failed: %s", exc)
            return f"Error fetching RSS: {exc}"


class NewsIntegration(Integration):
    name = "news"

    def is_configured(self) -> bool:
        return True  # RSS always works; NewsAPI is optional

    def get_tools(self) -> list[Tool]:
        return [NewsHeadlinesTool()]
