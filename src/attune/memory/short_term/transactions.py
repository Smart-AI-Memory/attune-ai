"""Atomic operations using Redis transactions.

This module provides atomic multi-step operations using MULTI/EXEC:
- Pattern promotion with rollback on failure
- Consistent state updates across multiple keys

Use Cases:
- Pattern lifecycle (stage -> promote/reject)
- Session management with consistency guarantees
- Any multi-key operation requiring atomicity

Classes:
    TransactionManager: Atomic operations using Redis transactions

Example:
    >>> from attune.memory.short_term.transactions import TransactionManager
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> transactions = TransactionManager(base_ops, caching_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.VALIDATOR)
    >>> success, pattern, msg = transactions.atomic_promote_pattern("pat_123", creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import structlog

# Redis is optional - check availability
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    redis = None  # type: ignore[assignment]
    REDIS_AVAILABLE = False

from attune.memory.types import (
    AgentCredentials,
    StagedPattern,
    parse_stored_record,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations
    from attune.memory.short_term.caching import CacheManager as CachingOperations

logger = structlog.get_logger(__name__)


class TransactionManager:
    """Atomic operations using Redis transactions.

    Provides atomic multi-step operations using Redis WATCH/MULTI/EXEC
    for operations that need consistency guarantees across multiple keys.

    The class requires access to both BaseOperations and CachingOperations
    to coordinate atomic updates with local cache invalidation.

    Attributes:
        PREFIX_STAGED: Key prefix for staged patterns namespace

    Example:
        >>> transactions = TransactionManager(base_ops, caching_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.VALIDATOR)
        >>> success, pattern, msg = transactions.atomic_promote_pattern(
        ...     "pat_123", creds, min_confidence=0.7
        ... )
        >>> if success:
        ...     library.add(pattern)

    """

    PREFIX_STAGED = "empathy:staged:"

    def __init__(self, base: BaseOperations, caching: CachingOperations) -> None:
        """Initialize transaction manager.

        Args:
            base: BaseOperations instance for Redis client access
            caching: CachingOperations instance for cache invalidation

        """
        self._base = base
        self._caching = caching

    def atomic_promote_pattern(
        self,
        pattern_id: str,
        credentials: AgentCredentials,
        min_confidence: float = 0.0,
    ) -> tuple[bool, StagedPattern | None, str]:
        """Atomically promote a pattern with validation.

        Uses Redis transaction (WATCH/MULTI/EXEC) to ensure:
        - Pattern exists and meets confidence threshold
        - Pattern is removed from staging atomically
        - No race conditions with concurrent operations

        Args:
            pattern_id: Pattern to promote
            credentials: Must be VALIDATOR or higher
            min_confidence: Minimum confidence threshold

        Returns:
            Tuple of (success, pattern, message)

        Raises:
            ValueError: If pattern_id is empty or min_confidence out of range

        Example:
            >>> success, pattern, msg = transactions.atomic_promote_pattern(
            ...     "pat_123", creds, min_confidence=0.7
            ... )
            >>> if success:
            ...     library.add(pattern)

        """
        # Pattern 1: String ID validation
        if not pattern_id or not pattern_id.strip():
            raise ValueError(f"pattern_id cannot be empty. Got: {pattern_id!r}")

        # Pattern 4: Range validation
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError(f"min_confidence must be between 0.0 and 1.0, got {min_confidence}")

        if not credentials.can_validate():
            return False, None, "Requires VALIDATOR tier or higher"

        key = f"{self.PREFIX_STAGED}{pattern_id}"

        # Handle mock mode
        if self._base.use_mock:
            if key not in self._base._mock_storage:
                return False, None, "Pattern not found"
            value, expires = self._base._mock_storage[key]
            if expires and datetime.now().timestamp() >= expires:
                return False, None, "Pattern expired"
            pattern = parse_stored_record(StagedPattern, str(value), key=key)
            if pattern is None:
                return False, None, "Pattern could not be read"
            if pattern.confidence < min_confidence:
                return (
                    False,
                    None,
                    f"Confidence {pattern.confidence} below threshold {min_confidence}",
                )
            del self._base._mock_storage[key]
            # Also invalidate local cache
            self._caching.invalidate(key)
            return True, pattern, "Pattern promoted successfully"

        # Handle real Redis client
        if self._base._client is None:
            return False, None, "Redis not connected"

        # Use WATCH for optimistic locking
        try:
            self._base._client.watch(key)
            raw = self._base._client.get(key)

            if raw is None:
                self._base._client.unwatch()
                return False, None, "Pattern not found"

            pattern = parse_stored_record(StagedPattern, raw, key=key)
            if pattern is None:
                self._base._client.unwatch()
                return False, None, "Pattern could not be read"

            if pattern.confidence < min_confidence:
                self._base._client.unwatch()
                return (
                    False,
                    None,
                    f"Confidence {pattern.confidence} below threshold {min_confidence}",
                )

            # Execute atomic delete
            pipe = self._base._client.pipeline(True)
            pipe.delete(key)
            pipe.execute()

            # Also invalidate local cache
            self._caching.invalidate(key)

            return True, pattern, "Pattern promoted successfully"

        except redis.WatchError:
            return False, None, "Pattern was modified by another process"
        finally:
            try:
                self._base._client.unwatch()
            except Exception:  # noqa: BLE001
                # INTENTIONAL: Best effort cleanup - don't fail on unwatch errors
                pass
