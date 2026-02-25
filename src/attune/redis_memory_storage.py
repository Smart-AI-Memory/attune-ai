"""Deprecated — use attune_redis.AMSMemoryBackend.

REMOVE IN v4.0.0 — see docs/migration/redis-plugin-migration.md

Legacy storage engine kept for backward compatibility.
New code should use ``attune_redis.memory.AMSMemoryBackend``.

Copyright 2025-2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import warnings

warnings.warn(
    "attune.redis_memory_storage is deprecated. "
    "Use attune_redis.memory.AMSMemoryBackend instead.",
    DeprecationWarning,
    stacklevel=2,
)

import json  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Any  # noqa: E402

try:
    import redis  # noqa: E402

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .memory.types import AgentCredentials, TTLStrategy  # noqa: E402


class RedisStorageBase:
    """Base class providing Redis/mock storage operations.

    Handles connection setup and low-level get/set/delete/keys
    operations against either a real Redis instance or an
    in-memory mock for testing.

    This is not intended to be instantiated directly. Use
    RedisShortTermMemory instead.
    """

    # Key prefixes for namespacing
    PREFIX_WORKING = "empathy:working:"
    PREFIX_STAGED = "empathy:staged:"
    PREFIX_CONFLICT = "empathy:conflict:"
    PREFIX_COORDINATION = "empathy:coord:"
    PREFIX_SESSION = "empathy:session:"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        use_mock: bool = False,
    ):
        """Initialize Redis connection

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            use_mock: Use in-memory mock for testing

        """
        self.use_mock = use_mock or not REDIS_AVAILABLE

        if self.use_mock:
            self._mock_storage: dict[str, tuple[Any, float | None]] = {}
            self._client = None
        else:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
            )

    def _get(self, key: str) -> str | None:
        """Get value from Redis or mock"""
        if self.use_mock:
            if key in self._mock_storage:
                value, expires = self._mock_storage[key]
                if expires is None or datetime.now().timestamp() < expires:
                    return str(value) if value is not None else None
                del self._mock_storage[key]
            return None
        if self._client is None:
            return None
        result = self._client.get(key)
        return str(result) if result else None

    def _set(self, key: str, value: str, ttl: int | None = None) -> bool:
        """Set value in Redis or mock"""
        if self.use_mock:
            expires = datetime.now().timestamp() + ttl if ttl else None
            self._mock_storage[key] = (value, expires)
            return True
        if self._client is None:
            return False
        if ttl:
            self._client.setex(key, ttl, value)
            return True
        result = self._client.set(key, value)
        return bool(result)

    def _delete(self, key: str) -> bool:
        """Delete key from Redis or mock"""
        if self.use_mock:
            if key in self._mock_storage:
                del self._mock_storage[key]
                return True
            return False
        if self._client is None:
            return False
        return self._client.delete(key) > 0

    def _keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern"""
        if self.use_mock:
            import fnmatch

            return [k for k in self._mock_storage.keys() if fnmatch.fnmatch(k, pattern)]
        if self._client is None:
            return []
        # Use scan_iter instead of keys() to avoid blocking Redis
        # with O(n) scan
        keys = list(self._client.scan_iter(match=pattern, count=100))
        return [k.decode() if isinstance(k, bytes) else str(k) for k in keys]

    # === Working Memory (Stash/Retrieve) ===

    def stash(
        self,
        key: str,
        data: Any,
        credentials: AgentCredentials,
        ttl: TTLStrategy = TTLStrategy.WORKING_RESULTS,
    ) -> bool:
        """Stash data in short-term memory

        Args:
            key: Unique key for the data
            data: Data to store (will be JSON serialized)
            credentials: Agent credentials
            ttl: Time-to-live strategy

        Returns:
            True if successful

        Example:
            >>> memory.stash("analysis_v1", {"findings": [...]}, creds)

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} (Tier {credentials.tier.name}) "
                "cannot write to memory. Requires CONTRIBUTOR or higher.",
            )

        full_key = f"{self.PREFIX_WORKING}{credentials.agent_id}:{key}"
        payload = {
            "data": data,
            "agent_id": credentials.agent_id,
            "stashed_at": datetime.now().isoformat(),
        }
        return self._set(full_key, json.dumps(payload), ttl.value)

    def retrieve(
        self,
        key: str,
        credentials: AgentCredentials,
        agent_id: str | None = None,
    ) -> Any | None:
        """Retrieve data from short-term memory

        Args:
            key: Key to retrieve
            credentials: Agent credentials
            agent_id: Owner agent ID (defaults to credentials agent)

        Returns:
            Retrieved data or None if not found

        Example:
            >>> data = memory.retrieve("analysis_v1", creds)

        """
        owner = agent_id or credentials.agent_id
        full_key = f"{self.PREFIX_WORKING}{owner}:{key}"
        raw = self._get(full_key)

        if raw is None:
            return None

        payload = json.loads(raw)
        return payload.get("data")

    def clear_working_memory(self, credentials: AgentCredentials) -> int:
        """Clear all working memory for an agent

        Args:
            credentials: Agent credentials (must own the memory
                or be Steward)

        Returns:
            Number of keys deleted

        """
        pattern = f"{self.PREFIX_WORKING}{credentials.agent_id}:*"
        keys = self._keys(pattern)
        count = 0
        for key in keys:
            if self._delete(key):
                count += 1
        return count

    # === Health Check ===

    def ping(self) -> bool:
        """Check Redis connection health

        Returns:
            True if connected and responsive

        """
        if self.use_mock:
            return True
        if self._client is None:
            return False
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001
            # INTENTIONAL: Health check is best-effort. Connection
            # failure is non-fatal. Consumers will handle
            # disconnection gracefully.
            return False

    def get_stats(self) -> dict:
        """Get memory statistics

        Returns:
            Dict with memory stats

        """
        if self.use_mock:
            # Use generator expressions for memory-efficient counting
            return {
                "mode": "mock",
                "total_keys": len(self._mock_storage),
                "working_keys": sum(
                    1 for k in self._mock_storage if k.startswith(self.PREFIX_WORKING)
                ),
                "staged_keys": sum(
                    1 for k in self._mock_storage if k.startswith(self.PREFIX_STAGED)
                ),
                "conflict_keys": sum(
                    1 for k in self._mock_storage if k.startswith(self.PREFIX_CONFLICT)
                ),
            }

        if self._client is None:
            return {"mode": "disconnected", "error": "No Redis client"}
        info = self._client.info("memory")
        return {
            "mode": "redis",
            "used_memory": info.get("used_memory_human"),
            "peak_memory": info.get("used_memory_peak_human"),
            "total_keys": self._client.dbsize(),
            "working_keys": len(self._keys(f"{self.PREFIX_WORKING}*")),
            "staged_keys": len(self._keys(f"{self.PREFIX_STAGED}*")),
            "conflict_keys": len(self._keys(f"{self.PREFIX_CONFLICT}*")),
        }
