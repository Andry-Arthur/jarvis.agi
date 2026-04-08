"""Ambient awareness — always-on low-power monitoring mode.

JARVIS monitors for important events (urgent email, calendar alarm, price alert)
and proactively interrupts the user when something genuinely important occurs.

The ambient monitor runs lightweight checks on configurable intervals and 
publishes notifications via the ProactiveAgent notification bus.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Coroutine

logger = logging.getLogger(__name__)


@dataclass
class AmbientAlert:
    source: str
    title: str
    body: str
    priority: str = "medium"  # "low" | "medium" | "high" | "urgent"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AmbientMonitor:
    """Runs background monitoring checks and emits alerts on important events."""

    def __init__(
        self,
        agent,
        scheduler,
        on_alert: Callable[[AmbientAlert], Coroutine] | None = None,
    ) -> None:
        self.agent = agent
        self.scheduler = scheduler
        self._on_alert = on_alert or self._default_alert_handler
        self._checks: list[dict] = []
        self._running = False

    async def _default_alert_handler(self, alert: AmbientAlert) -> None:
        from jarvis.core.proactive import Notification, notification_bus

        notification = Notification(
            title=f"[{alert.source}] {alert.title}",
            body=alert.body,
            kind="alert" if alert.priority in ("high", "urgent") else "info",
        )
        await notification_bus.publish(notification)

    def register_check(
        self,
        name: str,
        prompt: str,
        interval_minutes: int,
        priority: str = "medium",
        trigger_keywords: list[str] | None = None,
    ) -> None:
        """Register a periodic monitoring check."""
        self._checks.append({
            "name": name,
            "prompt": prompt,
            "interval_minutes": interval_minutes,
            "priority": priority,
            "trigger_keywords": trigger_keywords or [],
        })

    def start_defaults(self) -> None:
        """Start the default set of ambient monitoring checks."""
        self.register_check(
            name="urgent_email",
            prompt=(
                "Check my inbox for any URGENT or time-sensitive emails received in the last "
                "15 minutes. Reply ONLY if something urgent was found, with a 1-sentence summary. "
                "Reply 'NOTHING_URGENT' if nothing important."
            ),
            interval_minutes=15,
            priority="high",
            trigger_keywords=["urgent", "asap", "emergency", "deadline", "important"],
        )
        self.register_check(
            name="upcoming_event",
            prompt=(
                "Check my calendar for any events starting in the next 15 minutes. "
                "If found, reply with the event name and time. "
                "Reply 'NO_UPCOMING_EVENTS' if nothing is starting soon."
            ),
            interval_minutes=10,
            priority="high",
            trigger_keywords=["meeting", "call", "event", "appointment"],
        )

        self._schedule_all()
        logger.info("Ambient monitor started with %d checks.", len(self._checks))

    def _schedule_all(self) -> None:
        for check in self._checks:
            job_id = f"ambient_{check['name']}"
            try:
                self.scheduler._scheduler.add_job(
                    self._run_check,
                    trigger="interval",
                    minutes=check["interval_minutes"],
                    id=job_id,
                    args=[check],
                    replace_existing=True,
                    coalesce=True,
                    max_instances=1,
                )
                logger.debug(
                    "Ambient check '%s' scheduled every %d min.",
                    check["name"], check["interval_minutes"],
                )
            except Exception as exc:
                logger.warning("Failed to schedule ambient check '%s': %s", check["name"], exc)

    async def _run_check(self, check: dict) -> None:
        try:
            response = await self.agent.run(check["prompt"])

            # Filter out non-alerts
            skip_signals = ["NOTHING_URGENT", "NO_UPCOMING_EVENTS", "no recent", "nothing"]
            if any(signal.lower() in response.lower() for signal in skip_signals):
                logger.debug("Ambient check '%s': no alert.", check["name"])
                return

            # Check for trigger keywords if configured
            if check["trigger_keywords"]:
                if not any(kw in response.lower() for kw in check["trigger_keywords"]):
                    return

            alert = AmbientAlert(
                source=check["name"],
                title=check["name"].replace("_", " ").title(),
                body=response[:500],
                priority=check["priority"],
            )
            await self._on_alert(alert)

        except Exception as exc:
            logger.error("Ambient check '%s' failed: %s", check["name"], exc)

    def stop(self) -> None:
        for check in self._checks:
            job_id = f"ambient_{check['name']}"
            try:
                self.scheduler._scheduler.remove_job(job_id)
            except Exception:
                pass
        logger.info("Ambient monitor stopped.")
