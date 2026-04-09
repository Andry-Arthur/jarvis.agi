"""Integration status and management endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Metadata for all integrations: env vars required and a short description.
_INTEGRATION_META: dict[str, dict] = {
    # Keys match exactly what each Integration subclass returns for self.name
    "Gmail": {
        "display_name": "Gmail",
        "description": "Read, search, and send emails from your Gmail account.",
        "icon": "📧",
        "category": "Communication",
        "env_vars": ["GOOGLE_CLIENT_SECRET_FILE"],
        "setup_hint": "Download credentials.json from Google Cloud Console (OAuth 2.0).",
    },
    "Discord": {
        "display_name": "Discord",
        "description": "Send and receive messages from Discord channels and DMs.",
        "icon": "💬",
        "category": "Communication",
        "env_vars": ["DISCORD_BOT_TOKEN"],
        "setup_hint": "Create a bot at discord.com/developers and copy the token.",
    },
    "YouTube": {
        "display_name": "YouTube",
        "description": "Search videos, retrieve transcripts, and manage your channel.",
        "icon": "▶️",
        "category": "Media",
        "env_vars": ["YOUTUBE_API_KEY", "GOOGLE_CLIENT_SECRET_FILE"],
        "setup_hint": "Enable YouTube Data API v3 in Google Cloud Console.",
    },
    "Instagram": {
        "display_name": "Instagram",
        "description": "Read and send Instagram direct messages.",
        "icon": "📸",
        "category": "Social",
        "env_vars": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"],
        "setup_hint": "Create a Meta developer app and generate a long-lived access token.",
    },
    "google_calendar": {
        "display_name": "Google Calendar",
        "description": "Create, read, and manage events on your Google Calendar.",
        "icon": "📅",
        "category": "Productivity",
        "env_vars": ["GMAIL_CREDENTIALS_FILE"],
        "setup_hint": "Enable Calendar API in Google Cloud Console and run OAuth flow.",
    },
    "google_drive": {
        "display_name": "Google Drive",
        "description": "Search, read, upload, and manage files in Google Drive.",
        "icon": "☁️",
        "category": "Productivity",
        "env_vars": ["GOOGLE_DRIVE_ENABLED", "GMAIL_CREDENTIALS_FILE"],
        "setup_hint": "Enable Drive API in Google Cloud Console. Set GOOGLE_DRIVE_ENABLED=true.",
    },
    "whatsapp": {
        "display_name": "WhatsApp",
        "description": "Send and receive WhatsApp messages via the Cloud API.",
        "icon": "💚",
        "category": "Communication",
        "env_vars": ["WHATSAPP_ENABLED", "WHATSAPP_TOKEN", "WHATSAPP_PHONE_ID"],
        "setup_hint": "Set up a Meta Business account and enable WhatsApp Cloud API.",
    },
    "telegram": {
        "display_name": "Telegram",
        "description": "Send and receive Telegram messages and commands.",
        "icon": "✈️",
        "category": "Communication",
        "env_vars": ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"],
        "setup_hint": "Create a bot via @BotFather and copy the token.",
    },
    "spotify": {
        "display_name": "Spotify",
        "description": "Control playback, search tracks, and manage playlists.",
        "icon": "🎵",
        "category": "Media",
        "env_vars": ["SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET", "SPOTIPY_REDIRECT_URI"],
        "setup_hint": "Create a Spotify Developer app at developer.spotify.com.",
    },
    "slack": {
        "display_name": "Slack",
        "description": "Send messages and interact with Slack channels.",
        "icon": "🔔",
        "category": "Communication",
        "env_vars": ["SLACK_BOT_TOKEN"],
        "setup_hint": "Create a Slack app, add Bot Token Scopes, and install to workspace.",
    },
    "browser": {
        "display_name": "Browser",
        "description": "Browse the web, click elements, and scrape page content.",
        "icon": "🌐",
        "category": "Automation",
        "env_vars": [],
        "setup_hint": "Requires Playwright: pip install playwright && playwright install chromium.",
    },
    "filesystem": {
        "display_name": "Filesystem",
        "description": "Read, write, and manage files in allowed directories.",
        "icon": "📁",
        "category": "System",
        "env_vars": ["FS_ALLOWED_DIRS"],
        "setup_hint": "Set FS_ALLOWED_DIRS to a comma-separated list of allowed paths.",
    },
    "code_exec": {
        "display_name": "Code Executor",
        "description": "Execute Python and shell code snippets safely.",
        "icon": "⚡",
        "category": "System",
        "env_vars": ["CODE_EXEC_TIMEOUT", "CODE_EXEC_WORKDIR"],
        "setup_hint": "Always enabled. Optionally set CODE_EXEC_WORKDIR and CODE_EXEC_TIMEOUT.",
    },
    "screen": {
        "display_name": "Screen",
        "description": "Capture screenshots and perform OCR on screen content.",
        "icon": "🖥️",
        "category": "Automation",
        "env_vars": ["TESSERACT_CMD"],
        "setup_hint": "Install Tesseract OCR and optionally set TESSERACT_CMD path.",
    },
    "computer_control": {
        "display_name": "Computer Control",
        "description": "Control mouse, keyboard, and windows via PyAutoGUI.",
        "icon": "🖱️",
        "category": "Automation",
        "env_vars": ["PYAUTOGUI_PAUSE"],
        "setup_hint": "Install pyautogui. Works on desktop environments only.",
    },
    "knowledge_base": {
        "display_name": "Knowledge Base",
        "description": "Index and search your personal knowledge base via ChromaDB.",
        "icon": "🧠",
        "category": "Memory",
        "env_vars": ["KB_DIR", "CHROMA_PERSIST_DIR"],
        "setup_hint": "Always enabled. Set KB_DIR to your knowledge directory.",
    },
    "weather": {
        "display_name": "Weather",
        "description": "Get current weather and forecasts via Open-Meteo (no API key needed).",
        "icon": "🌤️",
        "category": "Information",
        "env_vars": [],
        "setup_hint": "Always enabled — uses free Open-Meteo API, no key required.",
    },
    "news": {
        "display_name": "News",
        "description": "Fetch top headlines and articles from NewsAPI or free RSS feeds.",
        "icon": "📰",
        "category": "Information",
        "env_vars": ["NEWSAPI_KEY"],
        "setup_hint": "Optional: get a free API key at newsapi.org for more sources.",
    },
    "notion": {
        "display_name": "Notion",
        "description": "Read and create pages and databases in your Notion workspace.",
        "icon": "📝",
        "category": "Productivity",
        "env_vars": ["NOTION_TOKEN"],
        "setup_hint": "Create a Notion integration at notion.so/my-integrations and copy the token.",
    },
    "github": {
        "display_name": "GitHub",
        "description": "Browse repos, manage issues, PRs, and read code on GitHub.",
        "icon": "🐙",
        "category": "Development",
        "env_vars": ["GITHUB_TOKEN"],
        "setup_hint": "Generate a Personal Access Token at github.com/settings/tokens.",
    },
    "home_assistant": {
        "display_name": "Home Assistant",
        "description": "Control smart home devices and query entity states.",
        "icon": "🏠",
        "category": "Smart Home",
        "env_vars": ["HA_BASE_URL", "HA_TOKEN"],
        "setup_hint": "Generate a long-lived access token in Home Assistant profile settings.",
    },
    "finance": {
        "display_name": "Finance",
        "description": "Access bank accounts, transactions, and balances via Plaid.",
        "icon": "💰",
        "category": "Finance",
        "env_vars": ["PLAID_CLIENT_ID", "PLAID_SECRET"],
        "setup_hint": "Create a Plaid developer account at plaid.com/docs/quickstart.",
    },
}


def _build_all_integrations():
    """Instantiate all known integrations and return their status dicts."""
    from jarvis.integrations.gmail import GmailIntegration
    from jarvis.integrations.discord_int import DiscordIntegration
    from jarvis.integrations.youtube import YouTubeIntegration
    from jarvis.integrations.instagram import InstagramIntegration
    from jarvis.integrations.google_calendar import GoogleCalendarIntegration
    from jarvis.integrations.google_drive import GoogleDriveIntegration
    from jarvis.integrations.whatsapp import WhatsAppIntegration
    from jarvis.integrations.telegram import TelegramIntegration
    from jarvis.integrations.spotify import SpotifyIntegration
    from jarvis.integrations.slack import SlackIntegration
    from jarvis.integrations.browser import BrowserIntegration
    from jarvis.integrations.filesystem import FilesystemIntegration
    from jarvis.integrations.code_exec import CodeExecIntegration
    from jarvis.integrations.screen import ScreenIntegration
    from jarvis.integrations.computer_control import ComputerControlIntegration
    from jarvis.integrations.knowledge_base import KnowledgeBaseIntegration
    from jarvis.integrations.weather import WeatherIntegration
    from jarvis.integrations.news import NewsIntegration
    from jarvis.integrations.notion import NotionIntegration
    from jarvis.integrations.github_int import GitHubIntegration
    from jarvis.integrations.home_assistant import HomeAssistantIntegration
    from jarvis.integrations.finance import FinanceIntegration

    instances = [
        GmailIntegration(),
        DiscordIntegration(),
        YouTubeIntegration(),
        InstagramIntegration(),
        GoogleCalendarIntegration(),
        GoogleDriveIntegration(),
        WhatsAppIntegration(),
        TelegramIntegration(),
        SpotifyIntegration(),
        SlackIntegration(),
        BrowserIntegration(),
        FilesystemIntegration(),
        CodeExecIntegration(),
        ScreenIntegration(),
        ComputerControlIntegration(),
        KnowledgeBaseIntegration(),
        WeatherIntegration(),
        NewsIntegration(),
        NotionIntegration(),
        GitHubIntegration(),
        HomeAssistantIntegration(),
        FinanceIntegration(),
    ]

    results = []
    for integration in instances:
        base = integration.status()
        raw_name = base["name"]
        meta = _INTEGRATION_META.get(raw_name, {})
        entry = {**base, **meta}
        # Use display_name as the canonical name shown in the UI
        if "display_name" in meta:
            entry["name"] = meta["display_name"]
        results.append(entry)
    return results


@router.get("")
async def list_integrations():
    """Return the status of all configured integrations."""
    return {"integrations": _build_all_integrations()}


@router.get("/tools")
async def list_tools():
    """Return all tools currently registered in the agent."""
    from jarvis.api.main import app_state

    agent = app_state.get("agent")
    if agent is None:
        return {"tools": []}
    schemas = agent.tools.get_all_schemas()
    return {"tools": [s["function"] for s in schemas]}
