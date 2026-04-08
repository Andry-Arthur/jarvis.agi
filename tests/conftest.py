"""pytest configuration — register asyncio mode."""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "asyncio: mark test as an asyncio coroutine"
    )
