"""APScheduler-based task scheduler for JARVIS.

Allows scheduling one-off reminders and repeating tasks via natural language.
The scheduler runs in the same process as the agent/API.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Wraps APScheduler with a simple JARVIS-friendly API."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._started = False

    def start(self) -> None:
        if not self._started:
            try:
                asyncio.get_running_loop()
                # We're inside an asyncio event loop — use AsyncIOScheduler directly
                self._scheduler.start()
            except RuntimeError:
                # No running loop (CLI sync context) — swap to a thread-based scheduler
                from apscheduler.schedulers.background import BackgroundScheduler
                self._scheduler = BackgroundScheduler()
                self._scheduler.start()
            self._started = True
            logger.info("Task scheduler started.")

    def stop(self) -> None:
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------

    def schedule_once(
        self,
        callback: Callable,
        run_at: datetime,
        job_id: str | None = None,
        **kwargs,
    ) -> str:
        """Schedule a one-off callback at a specific datetime."""
        job = self._scheduler.add_job(
            callback,
            trigger=DateTrigger(run_date=run_at),
            id=job_id,
            replace_existing=True,
            kwargs=kwargs,
        )
        logger.info("Scheduled one-off job '%s' at %s", job.id, run_at)
        return job.id

    def schedule_in(
        self,
        callback: Callable,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        job_id: str | None = None,
        **kwargs,
    ) -> str:
        """Schedule a callback to run after a delay."""
        run_at = datetime.now() + timedelta(seconds=seconds, minutes=minutes, hours=hours)
        return self.schedule_once(callback, run_at=run_at, job_id=job_id, **kwargs)

    def schedule_repeating(
        self,
        callback: Callable,
        cron_expression: str,
        job_id: str | None = None,
        **kwargs,
    ) -> str:
        """Schedule a repeating callback using a cron expression.

        Example cron_expression: '0 9 * * 1-5'  (every weekday at 09:00)
        """
        fields = cron_expression.split()
        if len(fields) != 5:
            raise ValueError("cron_expression must have 5 fields: minute hour day month weekday")
        minute, hour, day, month, day_of_week = fields
        job = self._scheduler.add_job(
            callback,
            trigger=CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
            ),
            id=job_id,
            replace_existing=True,
            kwargs=kwargs,
        )
        logger.info("Scheduled repeating job '%s' with cron '%s'", job.id, cron_expression)
        return job.id

    def cancel(self, job_id: str) -> bool:
        try:
            self._scheduler.remove_job(job_id)
            logger.info("Cancelled job '%s'", job_id)
            return True
        except Exception:
            return False

    def list_jobs(self) -> list[dict]:
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": next_run.isoformat() if next_run else None,
                }
            )
        return jobs


# ── Tool wrapper ──────────────────────────────────────────────────────────────


from jarvis.core.tools import Tool  # noqa: E402


class ReminderTool(Tool):
    name = "set_reminder"
    description = (
        "Set a reminder or scheduled task. "
        "Specify either 'in_minutes' / 'in_hours' for a delay, "
        "or 'cron' for a repeating schedule."
    )
    parameters = {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "The reminder message to display when triggered.",
            },
            "in_minutes": {
                "type": "integer",
                "description": "Fire the reminder after this many minutes.",
            },
            "in_hours": {
                "type": "integer",
                "description": "Fire the reminder after this many hours.",
            },
            "cron": {
                "type": "string",
                "description": "5-field cron expression for repeating reminders (e.g. '0 9 * * 1-5').",
            },
        },
        "required": ["message"],
    }

    def __init__(self, scheduler: TaskScheduler, notify_callback: Callable | None = None) -> None:
        self._scheduler = scheduler
        self._notify = notify_callback or (lambda msg: logger.info("REMINDER: %s", msg))

    async def execute(
        self,
        message: str,
        in_minutes: int | None = None,
        in_hours: int | None = None,
        cron: str | None = None,
    ) -> str:
        def fire():
            self._notify(message)

        if cron:
            job_id = self._scheduler.schedule_repeating(fire, cron_expression=cron)
            return f"Repeating reminder set (cron: {cron}). Job ID: {job_id}"

        minutes = (in_minutes or 0) + (in_hours or 0) * 60
        if minutes <= 0:
            minutes = 5  # default 5-minute reminder

        job_id = self._scheduler.schedule_in(fire, minutes=minutes)
        return f"Reminder set for {minutes} minute(s) from now. Job ID: {job_id}"


class ListRemindersTool(Tool):
    name = "list_reminders"
    description = "List all currently scheduled reminders."
    parameters = {"type": "object", "properties": {}}

    def __init__(self, scheduler: TaskScheduler) -> None:
        self._scheduler = scheduler

    async def execute(self) -> str:
        jobs = self._scheduler.list_jobs()
        if not jobs:
            return "No reminders scheduled."
        lines = [f"• [{j['id']}] next run: {j['next_run'] or 'unknown'}" for j in jobs]
        return "\n".join(lines)


class CancelReminderTool(Tool):
    name = "cancel_reminder"
    description = "Cancel a scheduled reminder by its job ID."
    parameters = {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "The job ID to cancel."},
        },
        "required": ["job_id"],
    }

    def __init__(self, scheduler: TaskScheduler) -> None:
        self._scheduler = scheduler

    async def execute(self, job_id: str) -> str:
        if self._scheduler.cancel(job_id):
            return f"Reminder {job_id} cancelled."
        return f"No reminder found with ID: {job_id}"
