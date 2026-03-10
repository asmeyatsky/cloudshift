"""Simple in-memory rate limiter for auth and sensitive endpoints."""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimiter:
    """In-memory rate limit: max N attempts per key per window_sec seconds."""

    def __init__(self, max_attempts: int = 5, window_sec: float = 60.0) -> None:
        self._max = max_attempts
        self._window = window_sec
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window
        self._attempts[key] = [t for t in self._attempts[key] if t > cutoff]
        if len(self._attempts[key]) >= self._max:
            return False
        self._attempts[key].append(now)
        return True

    def reset(self) -> None:
        """Clear state (for tests)."""
        self._attempts.clear()


# Login limiter: 30/min per IP (behind LB/proxy many users can share one IP)
login_limiter = RateLimiter(max_attempts=30, window_sec=60.0)
