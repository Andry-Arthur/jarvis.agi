"""Tests for autonomous config loading and env overrides."""

from __future__ import annotations

import pytest

from jarvis.core.autonomous_config import is_autonomous_enabled, load_autonomous_settings


def test_load_defaults_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AUTONOMOUS_ENABLED", raising=False)
    cfg = load_autonomous_settings()
    assert cfg["enabled"] is False
    assert cfg["local_news"]["interval_hours"] == 4
    assert is_autonomous_enabled() is False


def test_env_master_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONOMOUS_ENABLED", "true")
    assert load_autonomous_settings()["enabled"] is True
    assert is_autonomous_enabled() is True


def test_env_news_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONOMOUS_NEWS_INTERVAL_HOURS", "2")
    assert load_autonomous_settings()["local_news"]["interval_hours"] == 2


def test_env_ambient(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTONOMOUS_AMBIENT_ENABLED", "1")
    assert load_autonomous_settings()["ambient"]["enabled"] is True
