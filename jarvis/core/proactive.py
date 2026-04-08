"""Proactive agent mode — scheduled background briefings and alerts.

JARVIS runs jobs without being asked, then pushes results via WebSocket
or stores them as notifications.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class Notification:
    title: str
    body: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    kind: str = "info"  # "info" | "alert" | "briefing"


class NotificationBus:
    """In-process pub/sub for proactive notifications."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[Notification], Coroutine]] = []
        self._history: list[Notification] = []

    def subscribe(self, handler: Callable[[Notification], Coroutine]) -> None:
        self._subscribers.append(handler)

    async def publish(self, notification: Notification) -> None:
        self._history.append(notification)
        for handler in self._subscribers:
            try:
                await handler(notification)
            except Exception as exc:
                logger.warning("Notification handler error: %s", exc)

    def get_history(self, limit: int = 20) -> list[dict]:
        return [
            {
                "title": n.title,
                "body": n.body,
                "timestamp": n.timestamp,
                "kind": n.kind,
            }
            for n in self._history[-limit:]
        ]


# Global bus — imported by the WebSocket handler and proactive jobs
notification_bus = NotificationBus()


class ProactiveAgent:
    """Runs background intelligence jobs on a schedule."""

    def __init__(self, agent, scheduler, bus: NotificationBus | None = None) -> None:
        self.agent = agent
        self.scheduler = scheduler
        self.bus = bus or notification_bus
        self._jobs: list[str] = []

    def start_morning_briefing(self, hour: int = 8, minute: int = 0) -> None:
        """Schedule a daily morning briefing at the given time."""
        job_id = "morning_briefing"
        self.scheduler._scheduler.add_job(
            self._run_briefing,
            trigger="cron",
            hour=hour,
            minute=minute,
            id=job_id,
            replace_existing=True,
        )
        self._jobs.append(job_id)
        logger.info("Morning briefing scheduled at %02d:%02d", hour, minute)

    def start_inbox_monitor(self, interval_minutes: int = 30) -> None:
        """Check inbox every N minutes and alert on important emails."""
        job_id = "inbox_monitor"
        self.scheduler._scheduler.add_job(
            self._run_inbox_check,
            trigger="interval",
            minutes=interval_minutes,
            id=job_id,
            replace_existing=True,
        )
        self._jobs.append(job_id)
        logger.info("Inbox monitor started (every %d min)", interval_minutes)

    def start_calendar_conflict_check(self, interval_minutes: int = 60) -> None:
        """Periodically check for calendar conflicts."""
        job_id = "calendar_conflicts"
        self.scheduler._scheduler.add_job(
            self._run_calendar_check,
            trigger="interval",
            minutes=interval_minutes,
            id=job_id,
            replace_existing=True,
        )
        self._jobs.append(job_id)
        logger.info("Calendar conflict check started (every %d min)", interval_minutes)

    async def run_now(self, prompt: str, title: str = "JARVIS") -> Notification:
        """Run an arbitrary proactive query and publish the result."""
        try:
            response = await self.agent.run(prompt)
            notification = Notification(title=title, body=response, kind="briefing")
            await self.bus.publish(notification)
            return notification
        except Exception as exc:
            logger.error("Proactive run failed: %s", exc)
            notification = Notification(
                title=f"{title} (Error)", body=str(exc), kind="alert"
            )
            await self.bus.publish(notification)
            return notification

    async def _run_briefing(self) -> None:
        await self.run_now(
            "Give me a concise morning briefing: check my calendar for today, "
            "summarise any important emails, and give me a brief weather update.",
            title="Morning Briefing",
        )

    async def _run_inbox_check(self) -> None:
        await self.run_now(
            "Check my inbox for any important or urgent emails received in the last 30 minutes. "
            "Only alert me if there is something genuinely important.",
            title="Inbox Alert",
        )

    async def _run_calendar_check(self) -> None:
        await self.run_now(
            "Check my calendar for the next 24 hours. Alert me only if there are any scheduling "
            "conflicts or events starting within the next hour.",
            title="Calendar Alert",
        )

    def stop_all(self) -> None:
        for job_id in self._jobs:
            try:
                self.scheduler._scheduler.remove_job(job_id)
            except Exception:
                pass
        self._jobs.clear()
