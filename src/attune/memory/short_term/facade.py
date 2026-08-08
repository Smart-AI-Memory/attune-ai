"""RedisShortTermMemory facade - composes all specialized modules.

This facade provides the same public API as the original RedisShortTermMemory
class while delegating to specialized modules for implementation.

The facade pattern allows:
1. Backward compatibility: All existing imports continue to work
2. Incremental refactoring: Methods can be extracted one at a time
3. Clear separation of concerns: Each module handles one responsibility

Architecture:
    RedisShortTermMemory (facade)
    ├── BaseOperations (base.py)
    ├── CacheManager (caching.py)
    ├── DataSanitizer (security.py)
    ├── WorkingMemory (working.py)
    ├── PatternStaging (patterns.py)
    ├── ConflictNegotiation (conflicts.py)
    ├── SessionManager (sessions.py)
    ├── BatchOperations (batch.py)
    ├── Pagination (pagination.py)
    ├── PubSubManager (pubsub.py)
    ├── StreamManager (streams.py)
    ├── TimelineManager (timelines.py)
    ├── QueueManager (queues.py)
    ├── TransactionManager (transactions.py)
    └── CrossSessionManager (cross_session.py)

Usage:
    # During transition, use the facade:
    from attune.memory.short_term import RedisShortTermMemory

    # This import works the same as before the refactoring
    memory = RedisShortTermMemory(config=config)
    memory.stash("key", "value")
    memory.retrieve("key")

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from attune.memory.features import MemoryFeatures
from attune.memory.short_term.base import (
    REDIS_AVAILABLE,  # noqa: F401 - re-exported
    BaseOperations,
)
from attune.memory.short_term.batch import BatchOperations
from attune.memory.short_term.caching import CacheManager
from attune.memory.short_term.conflicts import ConflictNegotiation
from attune.memory.short_term.cross_session import CrossSessionManager
from attune.memory.short_term.pagination import Pagination
from attune.memory.short_term.patterns import PatternStaging
from attune.memory.short_term.pubsub import PubSubManager
from attune.memory.short_term.queues import QueueManager
from attune.memory.short_term.security import DataSanitizer
from attune.memory.short_term.sessions import SessionManager
from attune.memory.short_term.streams import StreamManager
from attune.memory.short_term.timelines import TimelineManager
from attune.memory.short_term.transactions import TransactionManager
from attune.memory.short_term.working import WorkingMemory

# Module-level logger for backward compatibility
logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from attune.memory.types import (
        AgentCredentials,
        ConflictContext,
        PaginatedResult,
        RedisConfig,
        StagedPattern,
        TimeWindowQuery,
        TTLStrategy,
    )


class RedisShortTermMemory:
    """Facade composing all short-term memory operations.

    This class maintains the same public API as the original
    RedisShortTermMemory while delegating to specialized modules.
    Each module handles a single responsibility:

    - BaseOperations: Connection management, basic CRUD
    - CacheManager: Local LRU cache layer
    - DataSanitizer: PII scrubbing, secrets detection
    - WorkingMemory: Stash/retrieve agent data
    - PatternStaging: Stage/promote/reject patterns
    - ConflictNegotiation: Conflict resolution workflow
    - SessionManager: Collaboration sessions
    - BatchOperations: Bulk stash/retrieve
    - Pagination: SCAN-based key iteration
    - PubSubManager: Real-time messaging
    - StreamManager: Ordered event logs
    - TimelineManager: Time-window queries
    - QueueManager: Task queues
    - TransactionManager: Atomic operations
    - CrossSessionManager: Cross-session coordination

    Example:
        >>> from attune.memory.short_term import RedisShortTermMemory
        >>> from attune.memory.types import RedisConfig
        >>> config = RedisConfig(use_mock=True)
        >>> memory = RedisShortTermMemory(config=config)
        >>> memory.stash("key", {"data": 123}, credentials)
        True
        >>> memory.retrieve("key", credentials)
        {'data': 123}

    """

    # Key prefixes for backward compatibility
    # These match BaseOperations prefixes for tests that reference them directly
    PREFIX_WORKING = "empathy:working:"
    PREFIX_STAGED = "empathy:staged:"
    PREFIX_CONFLICT = "empathy:conflict:"
    PREFIX_COORDINATION = "empathy:coordination:"
    PREFIX_SESSION = "empathy:session:"
    PREFIX_PUBSUB = "empathy:pubsub:"
    PREFIX_STREAM = "empathy:stream:"
    PREFIX_TIMELINE = "empathy:timeline:"
    PREFIX_QUEUE = "empathy:queue:"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
        use_mock: bool = False,
        config: RedisConfig | None = None,
        enable_local_cache: bool = True,
        local_cache_max_size: int = 1000,
    ) -> None:
        """Initialize Redis short-term memory facade.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            use_mock: Use in-memory mock for testing
            config: Full RedisConfig for advanced settings (overrides other args)
            enable_local_cache: Enable local LRU cache layer
            local_cache_max_size: Maximum entries in local cache

        Raises:
            ImportError: If Redis package is not installed (when use_mock=False)

        """
        # Check Redis availability — auto-enable mock mode if Redis unavailable
        if not use_mock and (config is None or not config.use_mock):
            if not MemoryFeatures.check_redis():
                import logging

                logging.getLogger(__name__).warning(
                    "Redis not available — falling back to in-memory mock mode. "
                    "Set ATTUNE_REDIS_MOCK=true to silence this warning.",
                )
                use_mock = True

        # Initialize base operations (handles connection, basic CRUD)
        self._base = BaseOperations(
            host=host,
            port=port,
            db=db,
            password=password,
            use_mock=use_mock,
            config=config,
        )

        # Initialize local cache layer
        self._cache = CacheManager(
            enabled=enable_local_cache,
            max_size=local_cache_max_size,
        )

        # Initialize security sanitizer. Both gates ON: PII is scrubbed in
        # place, secrets fail closed (SecurityError). memory-security-hardening
        # R2/D3 — a prior bug passed self._base as the first positional
        # (pii_scrub_enabled), leaving secrets_detection_enabled at its False
        # default, so this tier silently stored secrets.
        self._security = DataSanitizer(
            pii_scrub_enabled=True,
            secrets_detection_enabled=True,
        )

        # Initialize working memory (stash/retrieve)
        self._working = WorkingMemory(self._base, self._security)

        # Initialize pattern staging
        self._patterns = PatternStaging(self._base)

        # Initialize conflict negotiation
        self._conflicts = ConflictNegotiation(self._base)

        # Initialize session management
        self._sessions = SessionManager(self._base)

        # Initialize batch operations
        self._batch = BatchOperations(self._base)

        # Initialize pagination
        self._pagination = Pagination(self._base)

        # Initialize pub/sub
        self._pubsub = PubSubManager(self._base)

        # Initialize streams
        self._streams = StreamManager(self._base)

        # Initialize timelines
        self._timelines = TimelineManager(self._base)

        # Initialize queues
        self._queues = QueueManager(self._base)

        # Initialize transactions (needs cache for invalidation)
        self._transactions = TransactionManager(self._base, self._cache)

        # Initialize cross-session coordination
        self._cross_session = CrossSessionManager(self._base)

    # =========================================================================
    # Properties - delegate to base operations
    # =========================================================================

    @property
    def use_mock(self) -> bool:
        """Whether using mock storage instead of Redis."""
        return self._base.use_mock

    @property
    def client(self) -> Any:
        """Get the Redis client instance."""
        return self._base.client

    @property
    def _client(self) -> Any:
        """Get the Redis client instance (backward compatibility alias)."""
        return self._base._client

    @property
    def _config(self) -> Any:
        """Get the RedisConfig instance (for testing/debugging)."""
        return self._base._config

    @property
    def metrics(self) -> Any:
        """Get Redis metrics instance."""
        return self._base.metrics

    @property
    def _subscriptions(self) -> dict:
        """Expose pubsub subscriptions for backward compatibility."""
        return self._pubsub._subscriptions

    # =========================================================================
    # Working Memory Operations - delegate to WorkingMemory
    # =========================================================================

    def stash(
        self,
        key: str,
        data: Any,
        credentials: AgentCredentials,
        ttl: TTLStrategy | None = None,
        skip_sanitization: bool = False,
    ) -> bool:
        """Stash data in short-term memory."""
        from attune.memory.types import TTLStrategy as TTL

        effective_ttl = ttl if ttl is not None else TTL.WORKING_RESULTS
        return self._working.stash(key, data, credentials, effective_ttl, skip_sanitization)

    def retrieve(
        self,
        key: str,
        credentials: AgentCredentials,
        agent_id: str | None = None,
    ) -> Any | None:
        """Retrieve data from short-term memory."""
        return self._working.retrieve(key, credentials, agent_id)

    def clear_working_memory(self, credentials: AgentCredentials) -> int:
        """Clear all working memory for an agent."""
        return self._working.clear(credentials)

    # =========================================================================
    # Pattern Staging Operations - delegate to PatternStaging
    # =========================================================================

    def stage_pattern(
        self,
        pattern: StagedPattern,
        credentials: AgentCredentials,
    ) -> bool:
        """Stage a pattern for validation."""
        return self._patterns.stage_pattern(pattern, credentials)

    def get_staged_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
    ) -> StagedPattern | None:
        """Retrieve a staged pattern."""
        return self._patterns.get_staged_pattern(pattern_id, credentials)

    def list_staged_patterns(
        self,
        credentials: AgentCredentials,
    ) -> list[StagedPattern]:
        """List all staged patterns awaiting validation."""
        return self._patterns.list_staged_patterns(credentials)

    def promote_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
    ) -> StagedPattern | None:
        """Promote staged pattern (remove from staging for library add)."""
        return self._patterns.promote_pattern(pattern_id, credentials)

    def reject_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
        reason: str = "",
    ) -> bool:
        """Reject a staged pattern."""
        return self._patterns.reject_pattern(pattern_id, credentials, reason)

    # =========================================================================
    # Conflict Negotiation Operations - delegate to ConflictNegotiation
    # =========================================================================

    def create_conflict_context(
        self,
        conflict_id: str,
        positions: dict,
        interests: dict,
        credentials: AgentCredentials,
        batna: str | None = None,
    ) -> ConflictContext | None:
        """Create a conflict negotiation context."""
        return self._conflicts.create_conflict_context(  # type: ignore[arg-type]
            conflict_id, positions, interests, credentials, batna
        )

    def get_conflict_context(
        self,
        conflict_id: str,
        credentials: AgentCredentials,
    ) -> ConflictContext | None:
        """Retrieve a conflict context."""
        return self._conflicts.get_conflict_context(conflict_id, credentials)

    def resolve_conflict(
        self,
        conflict_id: str,
        resolution: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Mark a conflict as resolved."""
        return self._conflicts.resolve_conflict(conflict_id, resolution, credentials)

    def list_active_conflicts(
        self,
        credentials: AgentCredentials,
    ) -> list[ConflictContext]:
        """List all active (unresolved) conflicts."""
        return self._conflicts.list_active_conflicts(credentials)

    def send_signal(
        self,
        signal_type: str,
        data: Any,
        credentials: AgentCredentials,
        target_agent: str | None = None,
    ) -> bool:
        """Send a coordination signal to other agents."""
        import json
        from datetime import datetime

        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot send signals. "
                "Requires CONTRIBUTOR tier or higher.",
            )
        target = target_agent or "broadcast"
        key = f"{self.PREFIX_COORDINATION}{signal_type}:{credentials.agent_id}:{target}"
        payload = {
            "signal_type": signal_type,
            "from_agent": credentials.agent_id,
            "to_agent": target_agent,
            "data": data,
            "sent_at": datetime.now().isoformat(),
        }
        return bool(self._base._set(key, json.dumps(payload), 300))

    def receive_signals(
        self,
        credentials: AgentCredentials,
        signal_type: str | None = None,
    ) -> list[dict]:
        """Receive coordination signals addressed to this agent."""
        import json

        if signal_type:
            pattern = f"{self.PREFIX_COORDINATION}{signal_type}:*:{credentials.agent_id}"
        else:
            pattern = f"{self.PREFIX_COORDINATION}*:{credentials.agent_id}"
        broadcast_pattern = f"{self.PREFIX_COORDINATION}*:*:broadcast"
        keys = set(self._base._keys(pattern)) | set(self._base._keys(broadcast_pattern))
        signals = []
        for raw in self._base._mget(sorted(keys)):
            if raw:
                signals.append(json.loads(raw))
        return signals

    # =========================================================================
    # Session Management Operations - delegate to SessionManager
    # =========================================================================

    def create_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
        metadata: dict | None = None,
    ) -> dict | None:
        """Create a collaboration session."""
        return self._sessions.create_session(session_id, credentials, metadata)  # type: ignore[return-value]

    def join_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Join an existing session."""
        return self._sessions.join_session(session_id, credentials)

    def get_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> dict | None:
        """Get session details."""
        return self._sessions.get_session(session_id, credentials)

    def leave_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Leave a session."""
        return self._sessions.leave_session(session_id, credentials)

    def list_sessions(
        self,
        credentials: AgentCredentials,
    ) -> list[dict]:
        """List all active sessions."""
        return self._sessions.list_sessions()

    # =========================================================================
    # Base Operations - delegate to BaseOperations
    # =========================================================================

    def ping(self) -> bool:
        """Check Redis connection health."""
        return self._base.ping()

    def get_stats(self) -> dict:
        """Get memory statistics."""
        stats = self._base.get_stats()
        stats["local_cache"] = self._cache.get_stats()
        return stats

    def get_metrics(self) -> dict:
        """Get operation metrics for observability."""
        return self._base.get_metrics()

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._base.reset_metrics()

    def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        self._pubsub.close()
        self._base.close()

    # =========================================================================
    # Batch Operations - delegate to BatchOperations
    # =========================================================================

    def stash_batch(
        self,
        items: list[tuple[str, Any]],
        credentials: AgentCredentials,
        ttl: TTLStrategy | None = None,
    ) -> int:
        """Stash multiple items in a single operation."""
        from attune.memory.types import TTLStrategy as TTL

        effective_ttl = ttl if ttl is not None else TTL.WORKING_RESULTS
        return self._batch.stash_batch(items, credentials, effective_ttl)

    def retrieve_batch(
        self,
        keys: list[str],
        credentials: AgentCredentials,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve multiple items in a single operation."""
        return self._batch.retrieve_batch(keys, credentials, agent_id)

    # =========================================================================
    # Pagination Operations - delegate to Pagination
    # =========================================================================

    def list_staged_patterns_paginated(
        self,
        credentials: AgentCredentials,
        cursor: str = "0",
        count: int = 100,
    ) -> PaginatedResult:
        """List staged patterns with pagination using SCAN."""
        return self._pagination.list_staged_patterns_paginated(credentials, cursor, count)

    def scan_keys(
        self,
        pattern: str,
        cursor: str = "0",
        count: int = 100,
    ) -> PaginatedResult:
        """Scan keys matching a pattern with pagination."""
        return self._pagination.scan_keys(pattern, cursor, count)

    # =========================================================================
    # Pub/Sub Operations - delegate to PubSubManager
    # =========================================================================

    def publish(
        self,
        channel: str,
        message: dict,
        credentials: AgentCredentials,
    ) -> int:
        """Publish a message to a channel."""
        return self._pubsub.publish(channel, message, credentials)

    def subscribe(
        self,
        channel: str,
        handler: Callable[[dict], None],
        credentials: AgentCredentials | None = None,
    ) -> bool:
        """Subscribe to a channel for real-time notifications."""
        return self._pubsub.subscribe(channel, handler, credentials)

    def unsubscribe(self, channel: str) -> bool:
        """Unsubscribe from a channel."""
        return self._pubsub.unsubscribe(channel)

    def close_pubsub(self) -> None:
        """Close pubsub connection and stop listener thread."""
        self._pubsub.close()

    # =========================================================================
    # Stream Operations - delegate to StreamManager
    # =========================================================================

    def stream_append(
        self,
        stream_name: str,
        data: dict,
        credentials: AgentCredentials,
        max_len: int = 10000,
    ) -> str | None:
        """Append an entry to a Redis Stream."""
        return self._streams.append(stream_name, data, credentials, max_len)

    def stream_read(
        self,
        stream_name: str,
        credentials: AgentCredentials,
        start_id: str = "0",
        count: int = 100,
    ) -> list[tuple[str, dict]]:
        """Read entries from a Redis Stream."""
        return self._streams.read(stream_name, credentials, start_id, count)

    def stream_read_new(
        self,
        stream_name: str,
        credentials: AgentCredentials,
        block_ms: int = 0,
        count: int = 100,
    ) -> list[tuple[str, dict]]:
        """Read only new entries from a stream (blocking read)."""
        return self._streams.read_new(stream_name, credentials, block_ms, count)

    # =========================================================================
    # Timeline Operations - delegate to TimelineManager
    # =========================================================================

    def timeline_add(
        self,
        timeline_name: str,
        event_id: str,
        data: dict,
        credentials: AgentCredentials,
        timestamp: datetime | None = None,
    ) -> bool:
        """Add an event to a timeline (sorted set by timestamp)."""
        return self._timelines.add(timeline_name, event_id, data, credentials, timestamp)

    def timeline_query(
        self,
        timeline_name: str,
        credentials: AgentCredentials,
        query: TimeWindowQuery | None = None,
    ) -> list[dict]:
        """Query events from a timeline within a time window."""
        return self._timelines.query(timeline_name, credentials, query)

    def timeline_count(
        self,
        timeline_name: str,
        credentials: AgentCredentials,
        query: TimeWindowQuery | None = None,
    ) -> int:
        """Count events in a timeline within a time window."""
        return self._timelines.count(timeline_name, credentials, query)

    # =========================================================================
    # Queue Operations - delegate to QueueManager
    # =========================================================================

    def queue_push(
        self,
        queue_name: str,
        task: dict,
        credentials: AgentCredentials,
        priority: bool = False,
    ) -> int:
        """Push a task to a queue."""
        return self._queues.push(queue_name, task, credentials, priority)

    def queue_pop(
        self,
        queue_name: str,
        credentials: AgentCredentials,
        timeout: int = 0,
    ) -> dict | None:
        """Pop a task from a queue."""
        return self._queues.pop(queue_name, credentials, timeout)

    def queue_length(self, queue_name: str) -> int:
        """Get the length of a queue."""
        return self._queues.length(queue_name)

    def queue_peek(
        self,
        queue_name: str,
        credentials: AgentCredentials,
        count: int = 1,
    ) -> list[dict]:
        """Peek at tasks in a queue without removing them."""
        return self._queues.peek(queue_name, credentials, count)

    # =========================================================================
    # Transaction Operations - delegate to TransactionManager
    # =========================================================================

    def atomic_promote_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
        min_confidence: float = 0.0,
    ) -> tuple[bool, StagedPattern | None, str]:
        """Atomically promote a pattern with validation."""
        return self._transactions.atomic_promote_pattern(pattern_id, credentials, min_confidence)

    # =========================================================================
    # Cross-Session Operations - delegate to CrossSessionManager
    # =========================================================================

    def enable_cross_session(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Enable cross-session data sharing."""
        return bool(self._cross_session.enable(session_id, credentials))  # type: ignore[arg-type]

    def cross_session_available(
        self,
        session_id: str,
        credentials: AgentCredentials,
    ) -> bool:
        """Check if cross-session is available."""
        return self._cross_session.available()

    # =========================================================================
    # Cache Operations - expose cache stats
    # =========================================================================

    def get_cache_stats(self) -> dict:
        """Get local cache statistics."""
        return self._cache.get_stats()

    def clear_cache(self) -> int:
        """Clear local cache."""
        return self._cache.clear()

    # =========================================================================
    # Internal - for backward compatibility with tests
    # =========================================================================

    @property
    def _mock_storage(self) -> dict:
        """Access mock storage for testing."""
        return self._base._mock_storage

    @property  # type: ignore[no-redef]
    def _client(self) -> Any:
        """Access Redis client for testing."""
        return self._base._client

    @property
    def _metrics(self) -> Any:
        """Access metrics for testing."""
        return self._base._metrics

    @property
    def _pii_scrubber(self) -> Any:
        """Access PII scrubber for testing."""
        return self._security._pii_scrubber

    @_pii_scrubber.setter
    def _pii_scrubber(self, value: Any) -> None:
        """Set PII scrubber for testing."""
        self._security._pii_scrubber = value

    @property
    def _secrets_detector(self) -> Any:
        """Access secrets detector for testing."""
        return self._security._secrets_detector

    @_secrets_detector.setter
    def _secrets_detector(self, value: Any) -> None:
        """Set secrets detector for testing."""
        self._security._secrets_detector = value

    def _delete(self, key: str) -> bool:
        """Delete a key from Redis (internal method for testing)."""
        return self._base._delete(key)

    def _keys(self, pattern: str) -> list[str]:
        """List keys matching pattern (internal method for testing)."""
        return self._base._keys(pattern)
