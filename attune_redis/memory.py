"""AMS-backed memory backend for attune-redis.

Wraps the Redis Agent Memory Server via
``agent-memory-client`` to implement the
``MemoryBackend`` protocol.

Working memory stash/retrieve is mapped to the AMS
working memory ``data`` dict. Long-term semantic search
is exposed via the ``SearchableMemoryBackend`` extension.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from typing import Any

from .config import RedisPluginConfig

logger = logging.getLogger(__name__)


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine synchronously.

    Handles the case where we're already inside a running
    event loop (e.g. Jupyter, async web server) by using a
    thread pool executor.

    Args:
        coro: Awaitable coroutine to run.

    Returns:
        The coroutine's return value.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


class AMSMemoryBackend:
    """MemoryBackend implementation backed by Redis Agent Memory Server.

    Uses the AMS ``data`` dict on working memory sessions
    for key-value stash/retrieve operations, and AMS
    long-term memory for semantic search.

    Example::

        from attune_redis import AMSMemoryBackend
        from attune_redis.config import RedisPluginConfig

        config = RedisPluginConfig.from_env()
        backend = AMSMemoryBackend(config)

        backend.stash("results", {"score": 95})
        data = backend.retrieve("results")
        backend.close()
    """

    def __init__(self, config: RedisPluginConfig | None = None) -> None:
        """Initialize the AMS memory backend.

        Args:
            config: Plugin configuration. Uses env-based
                defaults if None.
        """
        from agent_memory_client import MemoryAPIClient

        self._config = config or RedisPluginConfig.from_env()
        self._client = MemoryAPIClient(
            base_url=self._config.ams_base_url,
        )
        self._session_id = self._config.default_session_id
        self._namespace = self._config.ams_namespace
        self._user_id = self._config.default_user_id
        self._closed = False

    # =========================================================================
    # MemoryBackend protocol methods
    # =========================================================================

    def stash(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        agent_id: str | None = None,
    ) -> bool:
        """Store data in AMS working memory.

        Maps to ``set_working_memory_data`` with
        ``preserve_existing=True`` so other keys are
        not overwritten.

        Args:
            key: Storage key.
            value: Data to store (must be JSON-compatible).
            ttl: Ignored (AMS manages TTL per-session).
            agent_id: Session ID override.

        Returns:
            True if stored successfully.
        """
        session_id = agent_id or self._session_id
        try:
            _run_sync(
                self._client.set_working_memory_data(
                    session_id=session_id,
                    data={key: value},
                    namespace=self._namespace,
                    preserve_existing=True,
                )
            )
            return True
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("stash_failed: key=%s error=%s", key, e)
            return False

    def retrieve(
        self,
        key: str,
        agent_id: str | None = None,
    ) -> Any | None:
        """Retrieve data from AMS working memory.

        Args:
            key: Storage key.
            agent_id: Session ID override.

        Returns:
            Stored value or None if not found.
        """
        session_id = agent_id or self._session_id
        try:
            response = _run_sync(
                self._client.get_working_memory(
                    session_id=session_id,
                    namespace=self._namespace,
                )
            )
            if response.data is None:
                return None
            return response.data.get(key)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("retrieve_failed: key=%s error=%s", key, e)
            return None

    def delete(self, key: str) -> bool:
        """Delete a key from AMS working memory.

        Updates the session's data dict with the key
        removed.

        Args:
            key: Key to delete.

        Returns:
            True if deleted, False if not found.
        """
        try:
            response = _run_sync(
                self._client.get_working_memory(
                    session_id=self._session_id,
                    namespace=self._namespace,
                )
            )
            data = response.data or {}
            if key not in data:
                return False
            del data[key]
            _run_sync(
                self._client.update_working_memory_data(
                    session_id=self._session_id,
                    data_updates=data,
                    namespace=self._namespace,
                    merge_strategy="replace",
                )
            )
            return True
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("delete_failed: key=%s error=%s", key, e)
            return False

    def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching a glob pattern.

        Args:
            pattern: Glob-style pattern.

        Returns:
            List of matching key names.
        """
        try:
            response = _run_sync(
                self._client.get_working_memory(
                    session_id=self._session_id,
                    namespace=self._namespace,
                )
            )
            data = response.data or {}
            if pattern == "*":
                return list(data.keys())
            return [k for k in data.keys() if fnmatch.fnmatch(k, pattern)]
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("keys_failed: pattern=%s error=%s", pattern, e)
            return []

    def is_connected(self) -> bool:
        """Check if AMS server is reachable.

        Returns:
            True if health check succeeds.
        """
        try:
            _run_sync(self._client.health_check())
            return True
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Health check is best-effort
            return False

    def get_stats(self) -> dict:
        """Get backend statistics.

        Returns:
            Dictionary with session count, connection
            status, and configuration.
        """
        stats: dict[str, Any] = {
            "mode": "ams",
            "base_url": self._config.ams_base_url,
            "namespace": self._namespace,
            "session_id": self._session_id,
            "connected": False,
        }
        try:
            _run_sync(self._client.health_check())
            stats["connected"] = True
            sessions = _run_sync(
                self._client.list_sessions(
                    namespace=self._namespace,
                )
            )
            stats["session_count"] = len(sessions.sessions)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Stats collection is best-effort
            logger.error("get_stats_failed: %s", e)
        return stats

    def close(self) -> None:
        """Close the AMS client and release resources."""
        if not self._closed:
            try:
                _run_sync(self._client.close())
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: Cleanup is best-effort
                logger.error("close_failed: %s", e)
            self._closed = True

    def supports_realtime(self) -> bool:
        """Whether the backend supports pub/sub.

        Returns:
            True if a Redis URL is configured for signaling.
        """
        return self._config.redis_url is not None

    def supports_distributed(self) -> bool:
        """Whether the backend supports distributed ops.

        Returns:
            True — AMS is HTTP-based and inherently
            supports multiple clients.
        """
        return True

    # =========================================================================
    # SearchableMemoryBackend extension methods
    # =========================================================================

    def search(
        self,
        query: str,
        limit: int = 10,
        **filters: Any,
    ) -> list[dict]:
        """Semantic search over long-term memories.

        Args:
            query: Natural language search query.
            limit: Maximum results to return.
            **filters: Additional AMS filters (topics,
                entities, memory_type, etc.).

        Returns:
            List of memory records as dicts.
        """
        try:
            results = _run_sync(
                self._client.search_long_term_memory(
                    text=query,
                    namespace={"eq": self._namespace},
                    limit=limit,
                    **filters,
                )
            )
            return [
                {
                    "id": r.id,
                    "text": r.text,
                    "topics": r.topics,
                    "entities": r.entities,
                    "memory_type": r.memory_type,
                    "created_at": (r.created_at.isoformat() if r.created_at else None),
                }
                for r in results.memories
            ]
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("search_failed: query=%s error=%s", query, e)
            return []

    def promote(self, session_id: str | None = None) -> bool:
        """Trigger promotion of working memories to long-term.

        Args:
            session_id: Session to promote. Uses default
                if None.

        Returns:
            True if promotion was triggered.
        """
        sid = session_id or self._session_id
        try:
            _run_sync(
                self._client.promote_working_memories_to_long_term(
                    session_id=sid,
                    namespace=self._namespace,
                )
            )
            return True
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("promote_failed: session=%s error=%s", sid, e)
            return False

    # =========================================================================
    # Context manager
    # =========================================================================

    def __enter__(self) -> AMSMemoryBackend:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, closing backend."""
        self.close()


__all__ = ["AMSMemoryBackend"]
