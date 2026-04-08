"""YouTube integration — search videos and retrieve transcripts."""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

YOUTUBE_API_SERVICE = "youtube"
YOUTUBE_API_VERSION = "v3"


def _build_service():
    from googleapiclient.discovery import build

    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if api_key:
        return build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION, developerKey=api_key)

    # Fall back to OAuth credentials (same as Gmail)
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    token_file = ".jarvis/youtube_token.json"
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret_file = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, scopes)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build(YOUTUBE_API_SERVICE, YOUTUBE_API_VERSION, credentials=creds)


# ── Tools ─────────────────────────────────────────────────────────────────────


class YouTubeSearchTool(Tool):
    name = "youtube_search"
    description = "Search YouTube for videos and return titles, channels, and URLs."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query string."},
            "max_results": {
                "type": "integer",
                "description": "Number of results to return (default 5).",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def run(self, query: str, max_results: int = 5) -> str:
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._search, query, max_results
        )

    def _search(self, query: str, max_results: int) -> str:
        service = _build_service()
        response = (
            service.search()
            .list(q=query, part="snippet", maxResults=max_results, type="video")
            .execute()
        )
        items = response.get("items", [])
        if not items:
            return f"No YouTube videos found for: {query}"

        lines = []
        for item in items:
            vid_id = item["id"]["videoId"]
            snippet = item["snippet"]
            lines.append(
                f"Title: {snippet['title']}\n"
                f"Channel: {snippet['channelTitle']}\n"
                f"URL: https://www.youtube.com/watch?v={vid_id}\n"
                f"Description: {snippet.get('description', '')[:150]}"
            )
        return "\n---\n".join(lines)


class YouTubeTranscriptTool(Tool):
    name = "youtube_get_transcript"
    description = (
        "Get the transcript/subtitles of a YouTube video by its URL or video ID. "
        "Useful for summarising or answering questions about a video's content."
    )
    parameters = {
        "type": "object",
        "properties": {
            "video_url_or_id": {
                "type": "string",
                "description": "Full YouTube URL or just the video ID (e.g. 'dQw4w9WgXcQ').",
            },
            "max_chars": {
                "type": "integer",
                "description": "Truncate transcript to this many characters (default 3000).",
                "default": 3000,
            },
        },
        "required": ["video_url_or_id"],
    }

    async def run(self, video_url_or_id: str, max_chars: int = 3000) -> str:
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._get_transcript, video_url_or_id, max_chars
        )

    def _extract_id(self, value: str) -> str:
        """Extract video ID from a URL or return the value as-is."""
        if "youtube.com/watch?v=" in value:
            return value.split("v=")[1].split("&")[0]
        if "youtu.be/" in value:
            return value.split("youtu.be/")[1].split("?")[0]
        return value.strip()

    def _get_transcript(self, video_url_or_id: str, max_chars: int) -> str:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

        vid_id = self._extract_id(video_url_or_id)
        try:
            transcript = YouTubeTranscriptApi.get_transcript(vid_id)
            text = " ".join(entry["text"] for entry in transcript)
            return text[:max_chars] + ("…" if len(text) > max_chars else "")
        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            return f"No transcript available for video {vid_id}: {exc}"
        except Exception as exc:
            return f"Error fetching transcript: {exc}"


# ── Integration bundle ────────────────────────────────────────────────────────


class YouTubeIntegration(Integration):
    @property
    def name(self) -> str:
        return "YouTube"

    def is_configured(self) -> bool:
        has_api_key = bool(os.getenv("YOUTUBE_API_KEY"))
        has_oauth = os.path.exists(os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json"))
        return has_api_key or has_oauth

    def get_tools(self) -> list[Tool]:
        return [YouTubeSearchTool(), YouTubeTranscriptTool()]
