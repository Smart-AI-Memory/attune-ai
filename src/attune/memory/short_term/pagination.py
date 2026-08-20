"""SCAN-based pagination for large key sets.

This module provides cursor-based pagination using Redis SCAN:
- Paginated pattern listing
- Generic key scanning with filters

Benefits:
- Memory-efficient for large datasets
- Non-blocking (unlike KEYS command)
- Cursor-based for consistent iteration

Classes:
    Pagination: SCAN-based pagination operations

Example:
    >>> from attune.memory.short_term.pagination import Pagination
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> pagination = Pagination(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> result = pagination.list_staged_patterns_paginated(creds, "0", 10)
    >>> for pattern in result.items:
    ...     print(pattern.name)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from attune.memory.types import (
    AgentCredentials,
    PaginatedResult,
    StagedPattern,
    parse_stored_record,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class Pagination:
    """SCAN-based pagination operations.

    Provides memory-efficient pagination using Redis SCAN command
    instead of the blocking KEYS command. Suitable for large datasets.

    The class is designed to be composed with BaseOperations
    for dependency injection.

    Attributes:
        PREFIX_STAGED: Key prefix for staged patterns namespace

    Example:
        >>> pagination = Pagination(base_ops)
        >>> result = pagination.list_staged_patterns_paginated(creds, "0", 10)
        >>> while result.has_more:
        ...     for pattern in result.items:
        ...         process(pattern)
        ...     result = pagination.list_staged_patterns_paginated(creds, result.cursor, 10)

    """

    PREFIX_STAGED = "empathy:staged:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize pagination operations.

        Args:
            base: BaseOperations instance for storage access

        """
        self._base = base

    def list_staged_patterns_paginated(
        self,
        credentials: AgentCredentials,
        cursor: str = "0",
        count: int = 100,
    ) -> PaginatedResult:
        """List staged patterns with pagination using SCAN.

        More efficient than list_staged_patterns() for large datasets.

        Args:
            credentials: Agent credentials
            cursor: Pagination cursor (start with "0")
            count: Maximum items per page

        Returns:
            PaginatedResult with items, cursor, and has_more flag

        Example:
            >>> result = pagination.list_staged_patterns_paginated(creds, "0", 10)
            >>> for pattern in result.items:
            ...     print(pattern.name)
            >>> if result.has_more:
            ...     next_result = pagination.list_staged_patterns_paginated(
            ...         creds, result.cursor, 10
            ...     )

        """
        start_time = time.perf_counter()
        pattern = f"{self.PREFIX_STAGED}*"

        # Handle mock storage mode
        if self._base.use_mock:
            import fnmatch

            all_keys = [k for k in self._base._mock_storage.keys() if fnmatch.fnmatch(k, pattern)]
            start_idx = int(cursor)
            end_idx = start_idx + count
            page_keys = all_keys[start_idx:end_idx]

            patterns = []
            for key in page_keys:
                raw_value, expires = self._base._mock_storage[key]
                if expires is None or datetime.now().timestamp() < expires:
                    staged = parse_stored_record(StagedPattern, str(raw_value), key=str(key))
                    if staged is not None:
                        patterns.append(staged)

            new_cursor = str(end_idx) if end_idx < len(all_keys) else "0"
            has_more = end_idx < len(all_keys)

            latency_ms = (time.perf_counter() - start_time) * 1000
            self._base._metrics.record_operation("list_paginated", latency_ms)

            return PaginatedResult(
                items=patterns,
                cursor=new_cursor,
                has_more=has_more,
                total_scanned=len(page_keys),
            )

        # Handle real Redis client
        if self._base._client is None:
            return PaginatedResult(items=[], cursor="0", has_more=False)

        # Use SCAN for efficient iteration
        new_cursor, keys = self._base._client.scan(cursor=int(cursor), match=pattern, count=count)

        patterns = []
        for key in keys:
            raw = self._base._client.get(key)
            staged = parse_stored_record(StagedPattern, raw, key=str(key)) if raw else None
            if staged is not None:
                patterns.append(staged)

        has_more = new_cursor != 0

        latency_ms = (time.perf_counter() - start_time) * 1000
        self._base._metrics.record_operation("list_paginated", latency_ms)

        return PaginatedResult(
            items=patterns,
            cursor=str(new_cursor),
            has_more=has_more,
            total_scanned=len(keys),
        )

    def scan_keys(
        self,
        pattern: str,
        cursor: str = "0",
        count: int = 100,
    ) -> PaginatedResult:
        """Scan keys matching a pattern with pagination.

        Generic key scanning that can be used for any key namespace.

        Args:
            pattern: Key pattern (e.g., "empathy:working:*")
            cursor: Pagination cursor
            count: Items per page

        Returns:
            PaginatedResult with key strings

        Example:
            >>> result = pagination.scan_keys("empathy:session:*", "0", 50)
            >>> for key in result.items:
            ...     print(key)

        """
        # Handle mock storage mode
        if self._base.use_mock:
            import fnmatch

            all_keys = [k for k in self._base._mock_storage.keys() if fnmatch.fnmatch(k, pattern)]
            start_idx = int(cursor)
            end_idx = start_idx + count
            page_keys = all_keys[start_idx:end_idx]
            new_cursor = str(end_idx) if end_idx < len(all_keys) else "0"
            has_more = end_idx < len(all_keys)
            return PaginatedResult(items=page_keys, cursor=new_cursor, has_more=has_more)

        # Handle real Redis client
        if self._base._client is None:
            return PaginatedResult(items=[], cursor="0", has_more=False)

        new_cursor, keys = self._base._client.scan(cursor=int(cursor), match=pattern, count=count)
        return PaginatedResult(
            items=[str(k) for k in keys],
            cursor=str(new_cursor),
            has_more=new_cursor != 0,
        )
