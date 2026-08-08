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
import hashlib
import logging
import re
import threading
from typing import Any

from .config import RedisPluginConfig

logger = logging.getLogger(__name__)

#: Default retention for pruning long-term findings (days). Mirrors
#: ``attune.memory.session_stash.DEFAULT_TTL_DAYS`` — kept as a local
#: constant to avoid a cross-package import into attune-redis.
_DEFAULT_TTL_DAYS = 30

#: AMS hard-caps ``search_long_term_memory``'s ``limit`` at 100 — passing a
#: larger value is a request-validation error that returns nothing, not a
#: clamp. Every search/recency call must bound its limit by this.
_AMS_MAX_SEARCH_LIMIT = 100

#: Max search requests one ``recent()`` call may issue while walking
#: created_at windows backward. Typical calls need 1-3 (the newest window
#: usually holds enough); a 1k-record namespace with a lagging prune needs
#: ~10-25. Hitting the cap logs a warning — older records may then be
#: missed, which is exactly the failure this bound guards from being silent.
_RECENT_MAX_REQUESTS = 40


class _PersistentLoop:
    """A single event loop running in a daemon thread.

    ``MemoryAPIClient`` holds a persistent ``httpx.AsyncClient``
    bound to the event loop it was first used on. Running each
    coroutine via a fresh ``asyncio.run`` (which creates *and
    closes* a new loop per call) leaves that client bound to a
    closed loop, so the second call onward fails with
    ``RuntimeError: Event loop is closed``. Routing every
    coroutine through one long-lived loop keeps the client's
    connection pool valid for the backend's whole lifetime, and
    ``run_coroutine_threadsafe`` is safe to call whether or not
    the caller is itself inside a running loop.
    """

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="ams-backend-loop", daemon=True
        )
        self._thread.start()

    def run(self, coro: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()


_LOOP: _PersistentLoop | None = None
_LOOP_LOCK = threading.Lock()


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine synchronously on a persistent loop.

    Args:
        coro: Awaitable coroutine to run.

    Returns:
        The coroutine's return value.
    """
    global _LOOP
    with _LOOP_LOCK:
        if _LOOP is None:
            _LOOP = _PersistentLoop()
    return _LOOP.run(coro)


def _content_hash_id(content: str) -> str:
    """Derive a stable long-term-memory id from a finding's content.

    Used by ``remember`` when no explicit ``memory_id`` is given so that an
    identical re-write maps to the same id and upserts (instead of piling up
    duplicates), while distinct content yields a distinct id. Merge-avoidance
    of *similar* findings is handled separately by writing with
    ``deduplicate=False`` — the id is the upsert key, not the merge guard.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
    return f"sha256-{digest}"


def _cwd_from_topics(topics: list[str] | None) -> str | None:
    """Extract the ``cwd:<path>`` marker session_stash writes into topics.

    Mirrors ``attune.memory.file_stash._cwd_from_topics`` so AMS search
    results surface ``cwd`` the same way the file backend does — letting
    ``recall_entries``'s cwd soft-sort actually work for AMS users.
    """
    for t in topics or []:
        if isinstance(t, str) and t.startswith("cwd:"):
            return t[len("cwd:") :]
    return None


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
        from agent_memory_client import MemoryAPIClient, MemoryClientConfig

        self._config = config or RedisPluginConfig.from_env()
        self._client = MemoryAPIClient(MemoryClientConfig(base_url=self._config.ams_base_url))
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

        Maps to ``update_working_memory_data`` with
        ``merge_strategy="merge"`` so other keys are preserved.

        NOTE: ``set_working_memory_data(preserve_existing=True)`` was
        verified against AMS 0.14.0 to REPLACE the whole working-memory
        ``data`` dict on every call (``preserve_existing`` preserves the
        session's *messages/memories*, not existing data keys), so a second
        ``stash`` clobbered the first — breaking ``keys`` and multi-key
        ``retrieve``. ``update_working_memory_data(merge_strategy="merge")``
        is the server-side merge primitive that keeps prior keys.

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
                self._client.update_working_memory_data(
                    session_id=session_id,
                    data_updates={key: value},
                    namespace=self._namespace,
                    merge_strategy="merge",
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
            _, response = _run_sync(
                self._client.get_or_create_working_memory(
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

    def retrieve_many(self, keys: list[str], agent_id: str | None = None) -> dict[str, Any]:
        """Retrieve several working-memory keys in one AMS round-trip.

        :meth:`retrieve` fetches the session's whole working-memory
        ``data`` dict per call, so N lookups cost N HTTP round-trips —
        one fetch serves them all. Missing keys map to ``None``; on an
        AMS error every key maps to ``None`` (graceful degradation,
        matching :meth:`retrieve`).

        Args:
            keys: Storage keys to retrieve.
            agent_id: Session ID override.

        Returns:
            Mapping of each requested key to its stored value or None.
        """
        if not keys:
            return {}
        session_id = agent_id or self._session_id
        try:
            _, response = _run_sync(
                self._client.get_or_create_working_memory(
                    session_id=session_id,
                    namespace=self._namespace,
                )
            )
            data = response.data or {}
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("retrieve_many_failed: keys=%d error=%s", len(keys), e)
            return dict.fromkeys(keys)
        return {k: data.get(k) for k in keys}

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
            _, response = _run_sync(
                self._client.get_or_create_working_memory(
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
            _, response = _run_sync(
                self._client.get_or_create_working_memory(
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

    def remember(
        self,
        content: str,
        *,
        memory_id: str | None = None,
        session_id: str | None = None,
        topics: list[str] | None = None,
    ) -> bool:
        """Write a searchable long-term memory.

        Unlike ``stash`` (working-memory key/value ``data`` dict), this
        creates an AMS long-term memory record that semantic ``search``
        can retrieve. Embedding happens server-side on write, so the
        finding is recallable across sessions.

        Deduplication note (both verified against a live AMS): AMS's
        ``create_long_term_memory(deduplicate=True)`` — the client DEFAULT —
        applies *semantic* dedup that silently MERGES distinct-but-similar
        findings (two records near in embedding space), and a distinct ``id``
        does NOT prevent it (the merge is content-driven, not id-keyed). For
        an accumulate-style store of findings, losing distinct insights that
        way is the wrong default, so we pass ``deduplicate=False``. To keep
        exact re-writes from piling up duplicates, we also key each record on
        a stable id: a caller-supplied ``memory_id`` when given, otherwise a
        derived content hash. Same id → AMS upserts (no duplicate); distinct
        content → distinct id and (with dedup off) every distinct finding
        survives.

        Args:
            content: Text to store and embed.
            memory_id: Optional stable id. When omitted, a content-hash id
                is derived so identical re-writes upsert instead of
                duplicating.
            session_id: Session id override.
            topics: Free-form tags carried on the record.

        Returns:
            True if the memory was written.
        """
        from agent_memory_client.models import ClientMemoryRecord

        record_id = memory_id or _content_hash_id(content)
        record_kwargs: dict[str, Any] = {
            "id": record_id,
            "text": content,
            "session_id": session_id or self._session_id,
            "namespace": self._namespace,
            "user_id": self._user_id,
            "topics": list(topics or []),
        }
        try:
            _run_sync(
                self._client.create_long_term_memory(
                    [ClientMemoryRecord(**record_kwargs)],
                    deduplicate=False,
                )
            )
            return True
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("remember_failed: id=%s error=%s", record_id, e)
            return False

    def search(
        self,
        query: str,
        limit: int = 10,
        **filters: Any,
    ) -> list[dict]:
        """Semantic search over long-term memories.

        Args:
            query: Natural language search query.
            limit: Maximum results to return. Clamped to AMS's hard cap of
                100 (a larger value is a validation error, not a clamp).
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
                    limit=min(limit, _AMS_MAX_SEARCH_LIMIT),
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
                    "cwd": _cwd_from_topics(r.topics),
                    "created_at": (r.created_at.isoformat() if r.created_at else None),
                }
                for r in results.memories
            ]
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("search_failed: query=%s error=%s", query, e)
            return []

    def _fetch_created_between(self, lo: Any, hi: Any) -> list[Any]:
        """One empty-text search bounded to ``created_at`` in [lo, hi].

        The ``created_at`` bound MUST be a ``CreatedAt`` model built from
        datetime objects — a ``{"gte": <iso-string>}`` dict serializes
        incorrectly and silently drops matches (verified live on AMS 0.14.0).
        """
        from agent_memory_client.filters import CreatedAt

        results = _run_sync(
            self._client.search_long_term_memory(
                text="",
                namespace={"eq": self._namespace},
                created_at=CreatedAt(gte=lo, lte=hi),
                limit=_AMS_MAX_SEARCH_LIMIT,
            )
        )
        return list(results.memories)

    def recent(self, limit: int = 5, **filters: Any) -> list[dict]:
        """Most-recent long-term findings (no query) — powers SessionStart recall.

        Mirrors the file backend's ``recent``: newest-first, with same-project
        findings surfaced ahead of others when ``cwd`` is given (soft priority).
        Returns the same record shape as ``search`` plus ``ts`` (epoch float,
        the recency key promotion consumers order by).

        AMS has no query-less recency *list* primitive, and (verified live on
        0.14.0) every listing affordance breaks on a namespace larger than one
        100-record page: the server's ordering is relevance-based (not recency,
        even with ``server_side_recency``), a single page can simply omit the
        newest records (the 2026-07-04 R4 failure: 1000+ records, 5 fresh
        findings absent), and ``offset`` pagination re-serves earlier records
        instead of the missing ones. The one primitive that behaves is the
        ``created_at`` range filter: a window matching <=100 records returns
        ALL of them. So recency is reconstructed client-side by walking
        disjoint time windows backward from now (exponentially widening, then
        an unbounded tail), bisecting any window that fills a whole page
        (truncation ⇒ arbitrary selection ⇒ split until complete), and
        stopping once ``limit`` records are collected — every window still
        unvisited is strictly older, so the collected set IS the newest.
        Request-capped by :data:`_RECENT_MAX_REQUESTS`. Best-effort; returns
        ``[]`` on any AMS error, never raises.
        """
        from collections import deque
        from datetime import datetime, timedelta, timezone

        cwd = filters.get("cwd")
        now = datetime.now(timezone.utc)
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        min_slice = timedelta(seconds=1)

        # Disjoint windows, newest first: 6h, then x4 wider each step until
        # past the 30d TTL (+grace), then one unbounded tail for anything a
        # lagging prune left behind. Shared boundaries are deduped by id.
        bands: list[tuple[Any, Any]] = []
        hi = now + timedelta(minutes=5)  # tolerate small clock skew
        span = timedelta(hours=6)
        while (now - hi) < timedelta(days=45):
            lo = hi - span
            bands.append((lo, hi))
            hi = lo
            span *= 4
        bands.append((epoch, hi))

        collected: dict[str, Any] = {}
        requests = 0
        try:
            for band in bands:
                # LIFO stack, newer half pushed last so it is fetched first.
                stack = deque([band])
                while stack:
                    if requests >= _RECENT_MAX_REQUESTS:
                        logger.warning(
                            "recent: request cap (%d) hit scanning %s; " "older records skipped",
                            _RECENT_MAX_REQUESTS,
                            self._namespace,
                        )
                        break
                    lo, hi = stack.pop()
                    page = self._fetch_created_between(lo, hi)
                    requests += 1
                    if len(page) >= _AMS_MAX_SEARCH_LIMIT and (hi - lo) > min_slice:
                        mid = lo + (hi - lo) / 2
                        stack.append((lo, mid))
                        stack.append((mid, hi))
                        continue
                    for m in page:
                        collected.setdefault(m.id, m)
                if len(collected) >= limit or requests >= _RECENT_MAX_REQUESTS:
                    break
            if len(collected) < limit and requests < _RECENT_MAX_REQUESTS:
                # Catch records the created_at filter can't see (created_at
                # unset) via one unfiltered page; they sort last anyway.
                results = _run_sync(
                    self._client.search_long_term_memory(
                        text="",
                        namespace={"eq": self._namespace},
                        limit=_AMS_MAX_SEARCH_LIMIT,
                    )
                )
                for m in results.memories:
                    collected.setdefault(m.id, m)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("recent_failed: limit=%s error=%s", limit, e)
            return []

        memories = list(collected.values())
        # Newest-first by created_at (None sorts last via epoch-0 fallback).
        memories.sort(
            key=lambda m: (m.created_at.timestamp() if m.created_at else 0.0),
            reverse=True,
        )
        if cwd:
            # Stable secondary sort: cwd matches first, recency preserved within.
            memories.sort(key=lambda m: 0 if _cwd_from_topics(m.topics) == cwd else 1)
        return [
            {
                "id": m.id,
                "text": m.text,
                "topics": m.topics,
                "cwd": _cwd_from_topics(m.topics),
                "session_id": m.session_id,
                "ts": (m.created_at.timestamp() if m.created_at else None),
                "created_at": (m.created_at.isoformat() if m.created_at else None),
            }
            for m in memories[:limit]
        ]

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

    def prune(self, max_age_days: int | None = None) -> int:
        """Forget long-term findings older than ``max_age_days`` (default 30).

        Aligns AMS retention with the file backend's age-prune (consistent
        cross-backend policy). Scoped to this backend's namespace via AMS's
        ``ForgetPolicy(max_age_days=...)``. Best-effort; returns the number
        of memories deleted (0 on failure), never raises.
        """
        from agent_memory_client.models import ForgetPolicy

        age = _DEFAULT_TTL_DAYS if max_age_days is None else max(1, max_age_days)
        try:
            response = _run_sync(
                self._client.forget_long_term_memories(
                    ForgetPolicy(max_age_days=age),
                    namespace=self._namespace,
                )
            )
            return int(getattr(response, "deleted", 0) or 0)
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("prune_failed: max_age_days=%s error=%s", age, e)
            return 0

    def forget(self, ids: list[str]) -> int:
        """Delete specific long-term memories by record ID.

        The IDs are the ``id`` values returned by :meth:`search` /
        :meth:`recent`. Complements :meth:`prune` (age-based sweep)
        with precise removal — the correction path when a stashed
        finding turns out to be wrong or stale. Best-effort; returns
        the number of memories deleted (0 on failure or empty input),
        never raises.
        """
        if not ids:
            return 0
        try:
            response = _run_sync(self._client.delete_long_term_memories(ids))
            # AMS acks with a status string like "ok, deleted 3 memories"
            # (no numeric field) — parse the count out, falling back to
            # len(ids) on a bare "ok".
            status = str(getattr(response, "status", "") or "")
            match = re.search(r"deleted (\d+)", status)
            if match:
                return int(match.group(1))
            return len(ids) if status.startswith("ok") else 0
        except Exception as e:  # noqa: BLE001
            # INTENTIONAL: Graceful degradation for AMS HTTP errors
            logger.error("forget_failed: ids=%d error=%s", len(ids), e)
            return 0

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
