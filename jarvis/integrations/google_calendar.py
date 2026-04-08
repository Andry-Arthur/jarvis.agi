"""Google Calendar integration.

Reuses the same OAuth credentials.json as Gmail (google-api-python-client).
Scopes required: https://www.googleapis.com/auth/calendar
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from jarvis.core.tools import Tool
from jarvis.integrations.base import Integration

logger = logging.getLogger(__name__)


def _get_service():
    """Build and return an authenticated Google Calendar service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    creds_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _calendar_id() -> str:
    return os.getenv("GOOGLE_CALENDAR_ID", "primary")


# -----------------------------------------------------------------------
# Tools
# -----------------------------------------------------------------------


class CalendarListEventsTool(Tool):
    name = "calendar_list_events"
    description = "List upcoming events on your Google Calendar."
    parameters = {
        "type": "object",
        "properties": {
            "days_ahead": {
                "type": "integer",
                "description": "How many days ahead to look (default 7)",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of events to return (default 10)",
            },
        },
    }

    async def execute(self, days_ahead: int = 7, max_results: int = 10) -> str:
        try:
            service = _get_service()
            now = datetime.now(timezone.utc)
            end = now + timedelta(days=days_ahead)
            result = (
                service.events()
                .list(
                    calendarId=_calendar_id(),
                    timeMin=now.isoformat(),
                    timeMax=end.isoformat(),
                    maxResults=max_results,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = result.get("items", [])
            if not events:
                return "No upcoming events found."
            lines = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date", ""))
                summary = event.get("summary", "(no title)")
                location = event.get("location", "")
                loc_str = f" @ {location}" if location else ""
                lines.append(f"• {summary}{loc_str} — {start}")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("calendar_list_events failed: %s", exc)
            return f"Error listing events: {exc}"


class CalendarCreateEventTool(Tool):
    name = "calendar_create_event"
    description = "Create a new event on Google Calendar."
    parameters = {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Event title"},
            "start": {
                "type": "string",
                "description": "Start datetime in ISO 8601 format, e.g. 2026-04-10T14:00:00",
            },
            "end": {
                "type": "string",
                "description": "End datetime in ISO 8601 format",
            },
            "description": {"type": "string", "description": "Event description"},
            "location": {"type": "string", "description": "Event location"},
        },
        "required": ["title", "start", "end"],
    }

    async def execute(
        self,
        title: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
    ) -> str:
        try:
            service = _get_service()
            tz = os.getenv("TIMEZONE", "UTC")
            event = {
                "summary": title,
                "start": {"dateTime": start, "timeZone": tz},
                "end": {"dateTime": end, "timeZone": tz},
            }
            if description:
                event["description"] = description
            if location:
                event["location"] = location
            created = (
                service.events()
                .insert(calendarId=_calendar_id(), body=event)
                .execute()
            )
            return f"Event created: {created.get('htmlLink', 'unknown link')}"
        except Exception as exc:
            logger.error("calendar_create_event failed: %s", exc)
            return f"Error creating event: {exc}"


class CalendarDeleteEventTool(Tool):
    name = "calendar_delete_event"
    description = "Delete a Google Calendar event by its ID."
    parameters = {
        "type": "object",
        "properties": {
            "event_id": {"type": "string", "description": "The event ID to delete"},
        },
        "required": ["event_id"],
    }

    async def execute(self, event_id: str) -> str:
        try:
            service = _get_service()
            service.events().delete(calendarId=_calendar_id(), eventId=event_id).execute()
            return f"Event {event_id} deleted."
        except Exception as exc:
            logger.error("calendar_delete_event failed: %s", exc)
            return f"Error deleting event: {exc}"


class CalendarFindFreeSlotTool(Tool):
    name = "calendar_find_free_slot"
    description = "Find the next available free time slot of a given duration."
    parameters = {
        "type": "object",
        "properties": {
            "duration_minutes": {
                "type": "integer",
                "description": "Duration of the slot in minutes",
            },
            "days_ahead": {
                "type": "integer",
                "description": "Search window in days (default 7)",
            },
        },
        "required": ["duration_minutes"],
    }

    async def execute(self, duration_minutes: int, days_ahead: int = 7) -> str:
        try:
            service = _get_service()
            now = datetime.now(timezone.utc)
            end_window = now + timedelta(days=days_ahead)
            body = {
                "timeMin": now.isoformat(),
                "timeMax": end_window.isoformat(),
                "items": [{"id": _calendar_id()}],
            }
            result = service.freebusy().query(body=body).execute()
            busy = result["calendars"][_calendar_id()]["busy"]

            # Walk through hours looking for a gap
            candidate = now
            duration = timedelta(minutes=duration_minutes)
            for slot in busy:
                busy_start = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
                if candidate + duration <= busy_start:
                    return f"Free slot found: {candidate.isoformat()} — {(candidate + duration).isoformat()}"
                busy_end = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
                if busy_end > candidate:
                    candidate = busy_end

            return f"Free slot found: {candidate.isoformat()} — {(candidate + duration).isoformat()}"
        except Exception as exc:
            logger.error("calendar_find_free_slot failed: %s", exc)
            return f"Error finding free slot: {exc}"


class GoogleCalendarIntegration(Integration):
    name = "google_calendar"

    def is_configured(self) -> bool:
        return bool(
            os.getenv("GMAIL_CREDENTIALS_FILE") or os.path.exists("credentials.json")
        )

    def get_tools(self) -> list[Tool]:
        return [
            CalendarListEventsTool(),
            CalendarCreateEventTool(),
            CalendarDeleteEventTool(),
            CalendarFindFreeSlotTool(),
        ]
