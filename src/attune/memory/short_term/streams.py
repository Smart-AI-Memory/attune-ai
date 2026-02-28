"""Redis Streams for ordered event logs.

This module provides stream operations for event sourcing:
- Append: Add events to stream with auto-generated IDs
- Read: Get events from specific position
- Read new: Block and wait for new events

Key Prefix: PREFIX_STREAM = "stream:"

Use Cases:
- Event sourcing
- Activity logs
- Message queues with persistence

Classes:
    StreamManager: Redis Streams operations

Example:
    >>> from attune.memory.short_term.streams import StreamManager
    >>> from attune.memory.types import AgentCredentials, AccessTier
    >>> streams = StreamManager(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> entry_id = streams.append("audit", {"action": "promoted"}, creds)
    >>> entries = streams.read("audit", creds, count=50)

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from attune.memory.types import (
    AgentCredentials,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class StreamManager:
    """Redis Streams operations for audit trails and event logs.

    Provides ordered, persistent event logging using Redis Streams.
    Features include automatic ID generation, max length trimming,
    and blocking reads for real-time event processing.

    The class manages its own mock stream storage for testing,
    composed with BaseOperations for Redis client access.

    Attributes:
        PREFIX_STREAM: Key prefix for stream names

    Example:
        >>> streams = StreamManager(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> entry_id = streams.append("audit", {"action": "pattern_promoted"}, creds)
        >>> entries = streams.read("audit", creds, count=100)
        >>> for eid, data in entries:
        ...     print(f"{eid}: {data}")

    """

    PREFIX_STREAM = "stream:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize stream manager.

        Args:
            base: BaseOperations instance for Redis client access

        """
        self._base = base
        self._mock_streams: dict[str, list[tuple[str, dict]]] = {}

    def append(
        self,
        stream_name: str,
        data: dict,
        credentials: AgentCredentials,
        max_len: int = 10000,
    ) -> str | None:
        """Append an entry to a Redis Stream for audit trails.

        Streams provide:
        - Ordered, persistent event log
        - Consumer groups for distributed processing
        - Time-based retention

        Args:
            stream_name: Name of the stream
            data: Event data to append
            credentials: Agent credentials (must be CONTRIBUTOR+)
            max_len: Maximum stream length (older entries trimmed)

        Returns:
            Entry ID if successful, None otherwise

        Raises:
            PermissionError: If credentials lack write access

        Example:
            >>> entry_id = streams.append(
            ...     "audit",
            ...     {"action": "pattern_promoted", "pattern_id": "xyz"},
            ...     creds
            ... )
            '1704067200000-0'

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot write to stream. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        start_time = time.perf_counter()
        full_stream = f"{self.PREFIX_STREAM}{stream_name}"

        entry = {
            "agent_id": credentials.agent_id,
            "timestamp": datetime.now().isoformat(),
            **{
                str(k): json.dumps(v) if isinstance(v, dict | list) else str(v)
                for k, v in data.items()
            },
        }

        # Handle mock mode
        if self._base.use_mock:
            if full_stream not in self._mock_streams:
                self._mock_streams[full_stream] = []
            entry_id = f"{int(datetime.now().timestamp() * 1000)}-0"
            self._mock_streams[full_stream].append((entry_id, entry))
            # Trim to max_len
            if len(self._mock_streams[full_stream]) > max_len:
                self._mock_streams[full_stream] = self._mock_streams[full_stream][-max_len:]
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._base._metrics.record_operation("stream_append", latency_ms)
            return entry_id

        # Handle real Redis client
        if self._base._client is None:
            return None

        entry_id = self._base._client.xadd(full_stream, entry, maxlen=max_len)
        latency_ms = (time.perf_counter() - start_time) * 1000
        self._base._metrics.record_operation("stream_append", latency_ms)

        return str(entry_id) if entry_id else None

    def read(
        self,
        stream_name: str,
        credentials: AgentCredentials,
        start_id: str = "0",
        count: int = 100,
    ) -> list[tuple[str, dict]]:
        """Read entries from a Redis Stream.

        Args:
            stream_name: Name of the stream
            credentials: Agent credentials
            start_id: Start reading from this ID ("0" = beginning)
            count: Maximum entries to read

        Returns:
            List of (entry_id, data) tuples

        Example:
            >>> entries = streams.read("audit", creds, count=50)
            >>> for entry_id, data in entries:
            ...     print(f"{entry_id}: {data}")

        """
        full_stream = f"{self.PREFIX_STREAM}{stream_name}"

        # Handle mock mode
        if self._base.use_mock:
            if full_stream not in self._mock_streams:
                return []
            entries = self._mock_streams[full_stream]
            # Filter by start_id (simple comparison)
            filtered = [(eid, data) for eid, data in entries if eid > start_id]
            return filtered[:count]

        # Handle real Redis client
        if self._base._client is None:
            return []

        result = self._base._client.xrange(full_stream, min=start_id, count=count)
        return [(str(entry_id), {str(k): v for k, v in data.items()}) for entry_id, data in result]

    def read_new(
        self,
        stream_name: str,
        credentials: AgentCredentials,
        block_ms: int = 0,
        count: int = 100,
    ) -> list[tuple[str, dict]]:
        """Read only new entries from a stream (blocking read).

        Blocks and waits for new entries to arrive. Useful for
        real-time event processing.

        Args:
            stream_name: Name of the stream
            credentials: Agent credentials
            block_ms: Milliseconds to block waiting (0 = no block)
            count: Maximum entries to read

        Returns:
            List of (entry_id, data) tuples

        Example:
            >>> # Wait up to 5 seconds for new entries
            >>> entries = streams.read_new("audit", creds, block_ms=5000)

        """
        full_stream = f"{self.PREFIX_STREAM}{stream_name}"

        # Handle mock mode - doesn't support blocking reads
        if self._base.use_mock:
            return []

        # Handle real Redis client
        if self._base._client is None:
            return []

        result = self._base._client.xread({full_stream: "$"}, block=block_ms, count=count)
        if not result:
            return []

        # Result format: [(stream_name, [(entry_id, data), ...])]
        entries = []
        for _stream, stream_entries in result:
            for entry_id, data in stream_entries:
                entries.append((str(entry_id), {str(k): v for k, v in data.items()}))
        return entries
