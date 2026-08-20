"""Pub/sub signaling for attune-redis.

Provides coordination signals between agents using
direct redis-py connections. AMS does not handle pub/sub,
so this module uses the Redis server directly.

Only initialized when ``REDIS_URL`` is configured.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class RedisSignalBus:
    """Thin pub/sub wrapper over redis-py.

    Example::

        bus = RedisSignalBus("redis://localhost:6379")
        bus.send("agent:updates", {"type": "task_complete"})
        bus.close()
    """

    def __init__(self, redis_url: str) -> None:
        """Initialize the signal bus.

        Args:
            redis_url: Redis connection URL.

        Raises:
            ImportError: If redis package is not installed.
        """
        import redis

        # Explicit bounds: without them the never-block contract is
        # decided by the installed redis-py, and the declared pin floor
        # (5.0.1) supplies none — a blackholed host blocks ~75s
        # (library-review H5).
        self._redis = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=5.0,
        )
        self._closed = False

    def send(self, channel: str, message: dict[str, Any]) -> int:
        """Publish a message to a channel.

        Args:
            channel: Channel name.
            message: Message payload (JSON-serializable).

        Returns:
            Number of subscribers that received the message.
        """
        return self._redis.publish(channel, json.dumps(message))

    def is_connected(self) -> bool:
        """Check if the Redis connection is healthy.

        Returns:
            True if Redis responds to PING.
        """
        try:
            return bool(self._redis.ping())
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Health check is best-effort
            return False

    def close(self) -> None:
        """Close the Redis connection."""
        if not self._closed:
            try:
                self._redis.close()
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Cleanup is best-effort
                logger.error("signal_bus_close_failed: %s", e)
            self._closed = True


__all__ = ["RedisSignalBus"]
