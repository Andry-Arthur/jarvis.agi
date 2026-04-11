"""Start and stop autonomous proactive jobs and optional ambient monitoring."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def start_autonomous(app_state: dict[str, Any], cfg: dict[str, Any]) -> None:
    """Attach ProactiveAgent (when enabled) and optional AmbientMonitor to app_state."""
    if not cfg.get("enabled"):
        logger.info("Autonomous loop disabled (autonomous.enabled=false).")
        return

    from jarvis.core.proactive import ProactiveAgent

    proactive = ProactiveAgent(
        agent=app_state["agent"],
        scheduler=app_state["scheduler"],
    )
    proactive.apply_autonomous_config(cfg)
    app_state["proactive_runner"] = proactive
    logger.info("Autonomous proactive jobs registered.")

    amb = cfg.get("ambient") or {}
    if amb.get("enabled"):
        from jarvis.agi.ambient import AmbientMonitor

        monitor = AmbientMonitor(
            agent=app_state["agent"],
            scheduler=app_state["scheduler"],
        )
        monitor.start_defaults()
        app_state["ambient_monitor"] = monitor


def stop_autonomous(app_state: dict[str, Any]) -> None:
    proactive = app_state.pop("proactive_runner", None)
    if proactive is not None:
        proactive.stop_all()

    ambient = app_state.pop("ambient_monitor", None)
    if ambient is not None:
        ambient.stop()
