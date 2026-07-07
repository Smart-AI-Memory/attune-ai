"""Memory backend protocol for Attune AI.

Defines the formal interface that all memory backends
must implement. Both FileSessionMemory and
RedisShortTermMemory satisfy this protocol.

Plugins register backends via the
``attune.memory_backends`` entry-point group.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MemoryBackend(Protocol):
    """Protocol for short-term memory backends.

    Any class that implements these methods can be used
    as a drop-in memory backend (file-based, Redis,
    custom, etc.).

    Minimal example::

        class MyBackend:
            def stash(self, key, value, ttl=None,
                      agent_id=None):
                ...
            def retrieve(self, key, agent_id=None):
                ...
            # ... remaining methods
    """

    def stash(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        agent_id: str | None = None,
    ) -> bool:
        """Store data in working memory.

        Args:
            key: Storage key.
            value: Data to store.
            ttl: Time-to-live in seconds.
            agent_id: Agent identifier.

        Returns:
            True if stored successfully.

        """
        ...

    def retrieve(
        self,
        key: str,
        agent_id: str | None = None,
    ) -> Any | None:
        """Retrieve data from working memory.

        Args:
            key: Storage key.
            agent_id: Agent identifier.

        Returns:
            Stored value or None if not found/expired.

        """
        ...

    def delete(self, key: str) -> bool:
        """Delete a key from working memory.

        Args:
            key: Key to delete.

        Returns:
            True if deleted, False if not found.

        """
        ...

    def keys(self, pattern: str = "*") -> list[str]:
        """Get keys matching a glob pattern.

        Args:
            pattern: Glob-style pattern.

        Returns:
            List of matching key names.

        """
        ...

    def is_connected(self) -> bool:
        """Check if storage backend is available.

        Returns:
            True if the backend is operational.

        """
        ...

    def get_stats(self) -> dict:
        """Get backend statistics.

        Returns:
            Dictionary of current statistics.

        """
        ...

    def close(self) -> None:
        """Shut down the backend and release resources."""
        ...

    def supports_realtime(self) -> bool:
        """Whether the backend supports pub/sub.

        Returns:
            True if publish/subscribe is available.

        """
        ...

    def supports_distributed(self) -> bool:
        """Whether the backend supports distributed ops.

        Returns:
            True if multi-node coordination is available.

        """
        ...


@runtime_checkable
class SearchableMemoryBackend(MemoryBackend, Protocol):
    """Extended protocol for backends with semantic search.

    Adds long-term memory search and promotion on top of
    the base MemoryBackend interface. Implemented by
    backends that support vector similarity search (e.g.,
    Redis Agent Memory Server).

    Example::

        if isinstance(backend, SearchableMemoryBackend):
            results = backend.search("authentication bugs")
            backend.promote(session_id="session-123")
    """

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
            **filters: Backend-specific filters.

        Returns:
            List of matching memory records as dicts.

        """
        ...

    def remember(
        self,
        content: str,
        *,
        memory_id: str | None = None,
        session_id: str | None = None,
        topics: list[str] | None = None,
    ) -> bool:
        """Write a semantically-searchable long-term memory.

        Distinct from ``stash`` (key/value working memory): a
        ``remember`` write enters the long-term store that ``search``
        retrieves, so the content is recallable across sessions.

        Args:
            content: Text to store and embed.
            memory_id: Optional stable id (enables dedup on re-write).
            session_id: Originating session id.
            topics: Free-form tags carried on the record.

        Returns:
            True if the memory was written.

        """
        ...

    def promote(self, session_id: str | None = None) -> bool:
        """Promote working memories to long-term storage.

        Args:
            session_id: Session to promote. Uses default
                if None.

        Returns:
            True if promotion was triggered.

        """
        ...

    def prune(self, max_age_days: int | None = None) -> int:
        """Forget searchable findings older than ``max_age_days``.

        Applies the retention policy consistently across backends (file
        age-prune + AMS forget). When ``max_age_days`` is None, the
        backend's configured default is used. Best-effort; returns the
        number of entries pruned (0 if none / on failure), never raises.

        Args:
            max_age_days: Age threshold in days; None uses the backend default.

        Returns:
            Count of pruned entries (best-effort).

        """
        ...

    def forget(self, ids: list[str]) -> int:
        """Delete specific findings by record ID.

        The IDs are the ``id`` values returned by ``search`` / ``recent``.
        Complements ``prune`` (age-based sweep) with precise removal — the
        correction path when a stashed finding is wrong or stale (e.g. a
        task note whose PR has since merged). Best-effort; returns the
        number of entries deleted (0 on failure or empty input), never
        raises. Backends predating this method are handled by callers via
        ``getattr``.

        Args:
            ids: Record IDs to delete.

        Returns:
            Count of deleted entries (best-effort).

        """
        ...

    def recent(self, limit: int = 5, **filters: Any) -> list[dict]:
        """Return the most-recent findings without a query.

        Powers query-less recall (SessionStart): newest findings first.
        When a ``cwd`` filter is given, same-project findings are surfaced
        first (soft priority). Best-effort; returns ``[]`` when unavailable,
        never raises. Backends predating this method are handled by callers
        via ``getattr``.

        Args:
            limit: Max results.
            **filters: Optional soft filters (e.g. ``cwd``).

        Returns:
            Ranked memory records as dicts (newest first), or ``[]``.

        """
        ...


__all__ = ["MemoryBackend", "SearchableMemoryBackend"]
