"""In-process rate limiter for MCP tool calls.

Lightweight token-bucket limiter that prevents runaway clients
from flooding the server with requests.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import time
from collections import defaultdict


class RateLimiter:
    """Simple sliding-window rate limiter.

    Tracks call timestamps per key and rejects calls that
    exceed the configured limit within the window.

    Args:
        max_calls: Maximum calls allowed per window.
        window_seconds: Length of the sliding window.

    Example:
        >>> limiter = RateLimiter(max_calls=10, window_seconds=60)
        >>> limiter.check("my_tool")  # True (allowed)

    """

    def __init__(
        self,
        max_calls: int = 60,
        window_seconds: float = 60.0,
    ) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._calls: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> bool:
        """Return True if the call is allowed, False if rate-limited.

        Args:
            key: Identifier to rate-limit (e.g. tool name).

        Returns:
            True if within limits, False if exceeded.

        """
        now = time.monotonic()
        calls = self._calls[key]
        # Prune entries outside the window
        self._calls[key] = [t for t in calls if now - t < self._window]
        if len(self._calls[key]) >= self._max:
            return False
        self._calls[key].append(now)
        return True
