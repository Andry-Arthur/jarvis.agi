"""Load autonomous-loop settings from config/settings.yaml with env overrides."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "morning_briefing": {"enabled": False, "hour": 8, "minute": 0},
    "inbox_monitor": {"enabled": False, "interval_minutes": 30},
    "calendar_conflicts": {"enabled": False, "interval_minutes": 60},
    "local_news": {
        "enabled": False,
        "interval_hours": 4,
        "region": "",
        "use_planner": False,
    },
    "economic_trends": {"enabled": False, "interval_hours": 12, "use_planner": True},
    "travel_planning": {
        "enabled": False,
        "day_of_week": "mon",
        "hour": 9,
        "minute": 0,
        "use_planner": True,
    },
    "ambient": {"enabled": False},
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _settings_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "settings.yaml"


def load_autonomous_settings() -> dict[str, Any]:
    """Return merged autonomous config (defaults + YAML + environment)."""
    cfg = _deep_merge({}, _DEFAULTS)

    path = _settings_path()
    if path.exists():
        try:
            import yaml

            with open(path, encoding="utf-8") as f:
                doc = yaml.safe_load(f) or {}
            raw = doc.get("autonomous")
            if isinstance(raw, dict):
                cfg = _deep_merge(cfg, raw)
        except Exception as exc:
            logger.warning("Could not load autonomous settings from %s: %s", path, exc)

    # Environment overrides (truthy string enables master switch, etc.)
    def _env_bool(key: str) -> bool | None:
        v = os.getenv(key)
        if v is None:
            return None
        return v.lower() in ("1", "true", "yes", "on")

    eb = _env_bool("AUTONOMOUS_ENABLED")
    if eb is not None:
        cfg["enabled"] = eb

    v = os.getenv("AUTONOMOUS_NEWS_INTERVAL_HOURS")
    if v and v.isdigit():
        cfg.setdefault("local_news", {})["interval_hours"] = int(v)

    v = os.getenv("AUTONOMOUS_ECONOMICS_INTERVAL_HOURS")
    if v and v.isdigit():
        cfg.setdefault("economic_trends", {})["interval_hours"] = int(v)

    amb = _env_bool("AUTONOMOUS_AMBIENT_ENABLED")
    if amb is not None:
        cfg.setdefault("ambient", {})["enabled"] = amb

    return cfg


def is_autonomous_enabled() -> bool:
    return bool(load_autonomous_settings().get("enabled"))
