"""Proactive agent mode — scheduled background briefings and alerts.

JARVIS runs jobs without being asked, then pushes results via WebSocket
or stores them as notifications.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine

from apscheduler.triggers.interval import IntervalTrigger

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

    def clear_subscribers(self) -> None:
        self._subscribers.clear()

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
        self._news_region: str = ""
        self._local_news_use_planner: bool = False
        self._economic_use_planner: bool = True
        self._travel_use_planner: bool = True

    def apply_autonomous_config(self, cfg: dict[str, Any]) -> None:
        """Register scheduled jobs from merged autonomous settings (see autonomous_config)."""
        if not cfg.get("enabled"):
            return

        mb = cfg.get("morning_briefing") or {}
        if mb.get("enabled"):
            self.start_morning_briefing(
                hour=int(mb.get("hour", 8)),
                minute=int(mb.get("minute", 0)),
            )

        im = cfg.get("inbox_monitor") or {}
        if im.get("enabled"):
            self.start_inbox_monitor(interval_minutes=int(im.get("interval_minutes", 30)))

        cc = cfg.get("calendar_conflicts") or {}
        if cc.get("enabled"):
            self.start_calendar_conflict_check(
                interval_minutes=int(cc.get("interval_minutes", 60))
            )

        ln = cfg.get("local_news") or {}
        if ln.get("enabled"):
            self._news_region = str(ln.get("region") or "")
            self._local_news_use_planner = bool(ln.get("use_planner", False))
            self.start_local_news_digest(
                interval_hours=int(ln.get("interval_hours", 4)),
                use_planner=self._local_news_use_planner,
            )

        et = cfg.get("economic_trends") or {}
        if et.get("enabled"):
            self._economic_use_planner = bool(et.get("use_planner", True))
            self.start_economic_digest(
                interval_hours=int(et.get("interval_hours", 12)),
                use_planner=self._economic_use_planner,
            )

        tp = cfg.get("travel_planning") or {}
        if tp.get("enabled"):
            self._travel_use_planner = bool(tp.get("use_planner", True))
            self.start_travel_planning(
                day_of_week=str(tp.get("day_of_week", "mon")),
                hour=int(tp.get("hour", 9)),
                minute=int(tp.get("minute", 0)),
                use_planner=self._travel_use_planner,
            )

    def start_local_news_digest(self, interval_hours: int = 4, use_planner: bool = False) -> None:
        job_id = "local_news_digest"
        self._local_news_use_planner = use_planner
        self.scheduler._scheduler.add_job(
            self._run_local_news,
            trigger=IntervalTrigger(hours=max(1, interval_hours)),
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._jobs.append(job_id)
        logger.info("Local news digest scheduled every %d h", interval_hours)

    def start_economic_digest(self, interval_hours: int = 12, use_planner: bool = True) -> None:
        job_id = "economic_trends"
        self._economic_use_planner = use_planner
        self.scheduler._scheduler.add_job(
            self._run_economic_digest,
            trigger=IntervalTrigger(hours=max(1, interval_hours)),
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
        )
        self._jobs.append(job_id)
        logger.info("Economic trends digest scheduled every %d h", interval_hours)

    def start_travel_planning(
        self,
        day_of_week: str = "mon",
        hour: int = 9,
        minute: int = 0,
        use_planner: bool = True,
    ) -> None:
        job_id = "travel_planning"
        self._travel_use_planner = use_planner
        self.scheduler._scheduler.add_job(
            self._run_travel_planning,
            trigger="cron",
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            id=job_id,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._jobs.append(job_id)
        logger.info(
            "Travel planning scheduled: %s at %02d:%02d (planner=%s)",
            day_of_week,
            hour,
            minute,
            use_planner,
        )

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

    async def run_goal(self, goal: str, title: str, use_planner: bool = False) -> None:
        """Run a goal with optional multi-step planner; publish briefing or alert."""
        try:
            if use_planner:
                from jarvis.core.planner import Planner

                text = await Planner(agent=self.agent).run(goal)
            else:
                text = await self.agent.run(goal)
            await self.bus.publish(
                Notification(title=title, body=text, kind="briefing")
            )
        except Exception as exc:
            logger.error("Proactive goal failed (%s): %s", title, exc)
            await self.bus.publish(
                Notification(
                    title=f"{title} (Error)", body=str(exc), kind="alert"
                )
            )

    async def _run_local_news(self) -> None:
        region = self._news_region.strip()
        region_hint = f" Focus on: {region}." if region else ""
        goal = (
            "Automated local news digest. Use news tools or browser to summarize "
            "relevant local or regional headlines and one-line context each."
            + region_hint
            + " Keep under 800 words. If tools are unavailable, say what to configure."
        )
        await self.run_goal(goal, title="Local news digest", use_planner=self._local_news_use_planner)

    async def _run_economic_digest(self) -> None:
        goal = (
            "Summarize major economic and market trends relevant to a general reader today. "
            "Use web/news/finance tools if available. Be concise (under 800 words); cite themes, not investment advice."
        )
        await self.run_goal(goal, title="Economic trends", use_planner=self._economic_use_planner)

    async def _run_travel_planning(self) -> None:
        goal = (
            "Review upcoming travel using calendar and email tools if configured. "
            "Produce a draft itinerary or packing checklist for trips in the next 14 days. "
            "If no trips, reply briefly that nothing is scheduled."
        )
        await self.run_goal(goal, title="Travel planning", use_planner=self._travel_use_planner)

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
