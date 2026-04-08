"""Spotify integration via spotipy (free, OAuth).

Required env vars:
  SPOTIPY_CLIENT_ID
  SPOTIPY_CLIENT_SECRET
  SPOTIPY_REDIRECT_URI  (default http://localhost:8888/callback)
"""

from __future__ import annotations

import logging
import os

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _sp():
    import spotipy  # type: ignore[import]
    from spotipy.oauth2 import SpotifyOAuth

    scope = (
        "user-read-playback-state "
        "user-modify-playback-state "
        "user-read-currently-playing "
        "playlist-modify-private "
        "playlist-modify-public "
        "user-library-read"
    )
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.environ["SPOTIPY_CLIENT_ID"],
            client_secret=os.environ["SPOTIPY_CLIENT_SECRET"],
            redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback"),
            scope=scope,
        )
    )


class SpotifyPlayTool(Tool):
    name = "spotify_play"
    description = "Play music on Spotify. Provide a track URI, album URI, or playlist URI."
    parameters = {
        "type": "object",
        "properties": {
            "uri": {
                "type": "string",
                "description": "Spotify URI (e.g. spotify:track:xxx) or search query",
            },
        },
        "required": ["uri"],
    }

    async def execute(self, uri: str) -> str:
        try:
            sp = _sp()
            if not uri.startswith("spotify:"):
                # Treat as search query — find first track
                results = sp.search(q=uri, type="track", limit=1)
                items = results["tracks"]["items"]
                if not items:
                    return f"No Spotify track found for '{uri}'."
                uri = items[0]["uri"]
                name = items[0]["name"]
                artist = items[0]["artists"][0]["name"]
                sp.start_playback(uris=[uri])
                return f"Playing: {name} by {artist}"
            sp.start_playback(uris=[uri])
            return f"Playing: {uri}"
        except Exception as exc:
            logger.error("spotify_play failed: %s", exc)
            return f"Error playing on Spotify: {exc}"


class SpotifyPauseTool(Tool):
    name = "spotify_pause"
    description = "Pause Spotify playback."
    parameters = {"type": "object", "properties": {}}

    async def execute(self) -> str:
        try:
            _sp().pause_playback()
            return "Spotify paused."
        except Exception as exc:
            return f"Error pausing Spotify: {exc}"


class SpotifySearchTrackTool(Tool):
    name = "spotify_search_track"
    description = "Search for tracks on Spotify and return results."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Number of results (default 5)"},
        },
        "required": ["query"],
    }

    async def execute(self, query: str, limit: int = 5) -> str:
        try:
            sp = _sp()
            results = sp.search(q=query, type="track", limit=limit)
            items = results["tracks"]["items"]
            if not items:
                return f"No tracks found for '{query}'."
            lines = []
            for item in items:
                artists = ", ".join(a["name"] for a in item["artists"])
                lines.append(f"• {item['name']} — {artists} ({item['uri']})")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("spotify_search_track failed: %s", exc)
            return f"Error searching Spotify: {exc}"


class SpotifyCreatePlaylistTool(Tool):
    name = "spotify_create_playlist"
    description = "Create a new Spotify playlist."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Playlist name"},
            "description": {"type": "string", "description": "Playlist description"},
            "public": {"type": "boolean", "description": "Whether to make it public (default false)"},
        },
        "required": ["name"],
    }

    async def execute(self, name: str, description: str = "", public: bool = False) -> str:
        try:
            sp = _sp()
            user_id = sp.current_user()["id"]
            playlist = sp.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description,
            )
            return f"Playlist '{name}' created: {playlist['external_urls']['spotify']}"
        except Exception as exc:
            logger.error("spotify_create_playlist failed: %s", exc)
            return f"Error creating playlist: {exc}"


class SpotifyAddToQueueTool(Tool):
    name = "spotify_add_to_queue"
    description = "Add a track to the Spotify playback queue."
    parameters = {
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "Spotify track URI or search query"},
        },
        "required": ["uri"],
    }

    async def execute(self, uri: str) -> str:
        try:
            sp = _sp()
            if not uri.startswith("spotify:"):
                results = sp.search(q=uri, type="track", limit=1)
                items = results["tracks"]["items"]
                if not items:
                    return f"No track found for '{uri}'."
                uri = items[0]["uri"]
            sp.add_to_queue(uri)
            return f"Added to queue: {uri}"
        except Exception as exc:
            logger.error("spotify_add_to_queue failed: %s", exc)
            return f"Error adding to queue: {exc}"


class SpotifyIntegration(Integration):
    name = "spotify"

    def is_configured(self) -> bool:
        return bool(os.getenv("SPOTIPY_CLIENT_ID") and os.getenv("SPOTIPY_CLIENT_SECRET"))

    def get_tools(self) -> list[Tool]:
        return [
            SpotifyPlayTool(),
            SpotifyPauseTool(),
            SpotifySearchTrackTool(),
            SpotifyCreatePlaylistTool(),
            SpotifyAddToQueueTool(),
        ]
