"""Batch operations for efficient bulk processing.

This module provides efficient batch operations using Redis pipelines:
- Batch stash: Store multiple items in single round-trip
- Batch retrieve: Get multiple items in single round-trip

Benefits:
- Reduces network round-trips
- Atomic execution (all or nothing)
- Better throughput for bulk operations

Classes:
    BatchOperations: Bulk stash/retrieve with Redis pipelines

Example:
    >>> from attune.memory.short_term.batch import BatchOperations
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> batch_ops = BatchOperations(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> items = [("key1", {"a": 1}), ("key2", {"b": 2})]
    >>> count = batch_ops.stash_batch(items, creds)
    >>> data = batch_ops.retrieve_batch(["key1", "key2"], creds)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any

import structlog

from attune.memory.types import (
    AgentCredentials,
    TTLStrategy,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class BatchOperations:
    """Batch operations using Redis pipelines.

    Provides efficient bulk stash/retrieve operations that reduce
    network round-trips by batching multiple operations into a
    single Redis pipeline execution.

    The class is designed to be composed with BaseOperations
    for dependency injection and access to Redis client.

    Attributes:
        PREFIX_WORKING: Key prefix for working memory namespace

    Example:
        >>> batch_ops = BatchOperations(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> items = [("analysis", {"score": 95}), ("summary", {"text": "..."})]
        >>> count = batch_ops.stash_batch(items, creds)
        2
        >>> batch_ops.retrieve_batch(["analysis", "summary"], creds)
        {'analysis': {'score': 95}, 'summary': {'text': '...'}}
    """

    PREFIX_WORKING = "empathy:working:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize batch operations.

        Args:
            base: BaseOperations instance for storage access
        """
        self._base = base

    def stash_batch(
        self,
        items: list[tuple[str, Any]],
        credentials: AgentCredentials,
        ttl: TTLStrategy = TTLStrategy.WORKING_RESULTS,
    ) -> int:
        """Stash multiple items in a single operation.

        Uses Redis pipeline for efficiency (reduces network round-trips).

        Args:
            items: List of (key, data) tuples
            credentials: Agent credentials
            ttl: Time-to-live strategy (applied to all items)

        Returns:
            Number of items successfully stashed

        Raises:
            TypeError: If items is not a list
            PermissionError: If credentials lack write access

        Example:
            >>> items = [("key1", {"a": 1}), ("key2", {"b": 2})]
            >>> count = batch_ops.stash_batch(items, creds)
            2
        """
        # Pattern 5: Type validation
        if not isinstance(items, list):
            raise TypeError(f"items must be list, got {type(items).__name__}")

        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot write to memory. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        if not items:
            return 0

        start_time = time.perf_counter()

        # Handle mock storage mode
        if self._base.use_mock:
            count = 0
            for key, data in items:
                full_key = f"{self.PREFIX_WORKING}{credentials.agent_id}:{key}"
                payload = {
                    "data": data,
                    "agent_id": credentials.agent_id,
                    "stashed_at": datetime.now().isoformat(),
                }
                expires = datetime.now().timestamp() + ttl.value
                self._base._mock_storage[full_key] = (json.dumps(payload), expires)
                count += 1
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._base._metrics.record_operation("stash_batch", latency_ms)
            return count

        # Handle real Redis client
        if self._base._client is None:
            return 0

        pipe = self._base._client.pipeline()
        for key, data in items:
            full_key = f"{self.PREFIX_WORKING}{credentials.agent_id}:{key}"
            payload = {
                "data": data,
                "agent_id": credentials.agent_id,
                "stashed_at": datetime.now().isoformat(),
            }
            pipe.setex(full_key, ttl.value, json.dumps(payload))

        results = pipe.execute()
        count = sum(1 for r in results if r)
        latency_ms = (time.perf_counter() - start_time) * 1000
        self._base._metrics.record_operation("stash_batch", latency_ms)

        logger.info("batch_stash_complete", count=count, total=len(items))
        return count

    def retrieve_batch(
        self,
        keys: list[str],
        credentials: AgentCredentials,
        agent_id: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve multiple items in a single operation.

        Uses Redis MGET for efficiency (single round-trip for all keys).

        Args:
            keys: List of keys to retrieve
            credentials: Agent credentials
            agent_id: Owner agent ID (defaults to credentials agent)

        Returns:
            Dict mapping key to data (missing keys omitted)

        Example:
            >>> data = batch_ops.retrieve_batch(["key1", "key2"], creds)
            >>> print(data["key1"])
            {'a': 1}
        """
        if not keys:
            return {}

        start_time = time.perf_counter()
        owner = agent_id or credentials.agent_id
        results: dict[str, Any] = {}

        # Handle mock storage mode
        if self._base.use_mock:
            for key in keys:
                full_key = f"{self.PREFIX_WORKING}{owner}:{key}"
                if full_key in self._base._mock_storage:
                    value, expires = self._base._mock_storage[full_key]
                    if expires is None or datetime.now().timestamp() < expires:
                        payload = json.loads(str(value))
                        results[key] = payload.get("data")
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._base._metrics.record_operation("retrieve_batch", latency_ms)
            return results

        # Handle real Redis client
        if self._base._client is None:
            return {}

        full_keys = [f"{self.PREFIX_WORKING}{owner}:{key}" for key in keys]
        values = self._base._client.mget(full_keys)

        for key, value in zip(keys, values, strict=False):
            if value:
                payload = json.loads(str(value))
                results[key] = payload.get("data")

        latency_ms = (time.perf_counter() - start_time) * 1000
        self._base._metrics.record_operation("retrieve_batch", latency_ms)
        return results
