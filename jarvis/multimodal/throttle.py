"""Simple rate limiter for multimodal WS broadcasts."""

from __future__ import annotations

import time


class TokenBucket:
    """Allows up to `rate` operations per second (burst up to `capacity`)."""

    def __init__(self, rate: float = 5.0, capacity: float = 5.0) -> None:
        self.rate = max(0.1, rate)
        self.capacity = max(1.0, capacity)
        self._tokens = capacity
        self._last = time.monotonic()

    def consume(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = now - self._last
        self._last = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False
