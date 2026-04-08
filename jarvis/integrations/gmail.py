"""Gmail integration — read, search, and send emails."""

from __future__ import annotations

import base64
import logging
import os
from email.mime.text import MIMEText
from typing import Any

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
TOKEN_FILE = ".jarvis/gmail_token.json"


def _build_service():
    """Return an authorised Gmail service, running OAuth flow if needed."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            secret_file = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _decode_body(payload: dict) -> str:
    """Extract plain-text body from a Gmail message payload."""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
    return ""


# ── Tools ─────────────────────────────────────────────────────────────────────


class GmailReadTool(Tool):
    name = "gmail_read_inbox"
    description = "Read the most recent emails from Gmail inbox."
    parameters = {
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Number of emails to fetch (default 5).",
                "default": 5,
            }
        },
    }

    async def run(self, max_results: int = 5) -> str:
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._fetch, max_results
        )

    def _fetch(self, max_results: int) -> str:
        service = _build_service()
        result = service.users().messages().list(
            userId="me", maxResults=max_results, labelIds=["INBOX"]
        ).execute()
        messages = result.get("messages", [])
        if not messages:
            return "Inbox is empty."

        summaries = []
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = _decode_body(msg["payload"])[:300]
            summaries.append(
                f"From: {headers.get('From', '?')}\n"
                f"Subject: {headers.get('Subject', '(no subject)')}\n"
                f"Date: {headers.get('Date', '?')}\n"
                f"Preview: {body.strip()}\n"
            )
        return "\n---\n".join(summaries)


class GmailSearchTool(Tool):
    name = "gmail_search"
    description = "Search Gmail using a Gmail search query (e.g. 'from:boss@company.com')."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Gmail search query string."},
            "max_results": {"type": "integer", "description": "Max emails to return.", "default": 5},
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
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        if not messages:
            return f"No emails found for query: {query}"

        summaries = []
        for m in messages:
            msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            body = _decode_body(msg["payload"])[:300]
            summaries.append(
                f"From: {headers.get('From', '?')}\n"
                f"Subject: {headers.get('Subject', '(no subject)')}\n"
                f"Preview: {body.strip()}"
            )
        return "\n---\n".join(summaries)


class GmailSendTool(Tool):
    name = "gmail_send"
    description = "Send an email via Gmail."
    parameters = {
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address."},
            "subject": {"type": "string", "description": "Email subject line."},
            "body": {"type": "string", "description": "Plain-text email body."},
        },
        "required": ["to", "subject", "body"],
    }

    async def run(self, to: str, subject: str, body: str) -> str:
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(
            None, self._send, to, subject, body
        )

    def _send(self, to: str, subject: str, body: str) -> str:
        service = _build_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"Email sent to {to} with subject '{subject}'."


# ── Integration bundle ────────────────────────────────────────────────────────


class GmailIntegration(Integration):
    @property
    def name(self) -> str:
        return "Gmail"

    def is_configured(self) -> bool:
        secret = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
        return os.path.exists(secret) or os.path.exists(TOKEN_FILE)

    def get_tools(self) -> list[Tool]:
        return [GmailReadTool(), GmailSearchTool(), GmailSendTool()]
