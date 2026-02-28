"""Time-window queries using Redis sorted sets.

This module provides timeline operations for time-series data:
- Add: Insert event with timestamp score
- Query: Get events in time window
- Count: Count events in time window

Key Prefix: PREFIX_TIMELINE = "timeline:"

Use Cases:
- Activity timelines
- Time-based analytics
- Rate limiting windows

Classes:
    TimelineManager: Redis sorted set operations for timelines

Example:
    >>> from attune.memory.short_term.timelines import TimelineManager
    >>> from attune.memory.types import AgentCredentials, AccessTier, TimeWindowQuery
    >>> timelines = TimelineManager(base_ops)
    >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
    >>> timelines.add("events", "evt_1", {"action": "login"}, creds)
    >>> events = timelines.query("events", creds, TimeWindowQuery(limit=50))

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0

"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

from attune.memory.types import (
    AgentCredentials,
    TimeWindowQuery,
)

if TYPE_CHECKING:
    from attune.memory.short_term.base import BaseOperations

logger = structlog.get_logger(__name__)


class TimelineManager:
    """Redis sorted set operations for timeline queries.

    Provides time-series event storage using Redis sorted sets,
    where events are scored by timestamp for efficient time-window queries.

    The class manages its own mock sorted set storage for testing,
    composed with BaseOperations for Redis client access.

    Attributes:
        PREFIX_TIMELINE: Key prefix for timeline names

    Example:
        >>> timelines = TimelineManager(base_ops)
        >>> creds = AgentCredentials("agent_1", AccessTier.CONTRIBUTOR)
        >>> timelines.add("agent_events", "evt_123", {"action": "login"}, creds)
        >>> query = TimeWindowQuery(limit=100)
        >>> events = timelines.query("agent_events", creds, query)

    """

    PREFIX_TIMELINE = "timeline:"

    def __init__(self, base: BaseOperations) -> None:
        """Initialize timeline manager.

        Args:
            base: BaseOperations instance for Redis client access

        """
        self._base = base
        self._mock_sorted_sets: dict[str, list[tuple[float, str]]] = {}

    def add(
        self,
        timeline_name: str,
        event_id: str,
        data: dict,
        credentials: AgentCredentials,
        timestamp: datetime | None = None,
    ) -> bool:
        """Add an event to a timeline (sorted set by timestamp).

        Args:
            timeline_name: Name of the timeline
            event_id: Unique event identifier
            data: Event data
            credentials: Agent credentials (must be CONTRIBUTOR+)
            timestamp: Event timestamp (defaults to now)

        Returns:
            True if added successfully

        Raises:
            PermissionError: If credentials lack write access

        Example:
            >>> timelines.add(
            ...     "audit_log",
            ...     "evt_001",
            ...     {"action": "pattern_promoted"},
            ...     creds
            ... )
            True

        """
        if not credentials.can_stage():
            raise PermissionError(
                f"Agent {credentials.agent_id} cannot write to timeline. "
                "Requires CONTRIBUTOR tier or higher.",
            )

        full_timeline = f"{self.PREFIX_TIMELINE}{timeline_name}"
        ts = timestamp or datetime.now()
        score = ts.timestamp()

        payload = json.dumps(
            {
                "event_id": event_id,
                "timestamp": ts.isoformat(),
                "agent_id": credentials.agent_id,
                "data": data,
            },
        )

        # Handle mock mode
        if self._base.use_mock:
            if full_timeline not in self._mock_sorted_sets:
                self._mock_sorted_sets[full_timeline] = []
            self._mock_sorted_sets[full_timeline].append((score, payload))
            self._mock_sorted_sets[full_timeline].sort(key=lambda x: x[0])
            return True

        # Handle real Redis client
        if self._base._client is None:
            return False

        self._base._client.zadd(full_timeline, {payload: score})
        return True

    def query(
        self,
        timeline_name: str,
        credentials: AgentCredentials,
        query: TimeWindowQuery | None = None,
    ) -> list[dict]:
        """Query events from a timeline within a time window.

        Args:
            timeline_name: Name of the timeline
            credentials: Agent credentials
            query: Time window query parameters

        Returns:
            List of events in the time window

        Example:
            >>> from datetime import datetime, timedelta
            >>> query = TimeWindowQuery(
            ...     start_time=datetime.now() - timedelta(hours=1),
            ...     end_time=datetime.now(),
            ...     limit=50
            ... )
            >>> events = timelines.query("agent_events", creds, query)

        """
        full_timeline = f"{self.PREFIX_TIMELINE}{timeline_name}"
        q = query or TimeWindowQuery()

        # Handle mock mode
        if self._base.use_mock:
            if full_timeline not in self._mock_sorted_sets:
                return []
            entries = self._mock_sorted_sets[full_timeline]
            filtered = [
                json.loads(payload)
                for score, payload in entries
                if q.start_score <= score <= q.end_score
            ]
            return filtered[q.offset : q.offset + q.limit]

        # Handle real Redis client
        if self._base._client is None:
            return []

        results = self._base._client.zrangebyscore(
            full_timeline,
            min=q.start_score,
            max=q.end_score,
            start=q.offset,
            num=q.limit,
        )

        return [json.loads(r) for r in results]

    def count(
        self,
        timeline_name: str,
        credentials: AgentCredentials,
        query: TimeWindowQuery | None = None,
    ) -> int:
        """Count events in a timeline within a time window.

        Args:
            timeline_name: Name of the timeline
            credentials: Agent credentials
            query: Time window query parameters

        Returns:
            Number of events in the time window

        Example:
            >>> count = timelines.count("agent_events", creds)
            >>> print(f"Total events: {count}")

        """
        full_timeline = f"{self.PREFIX_TIMELINE}{timeline_name}"
        q = query or TimeWindowQuery()

        # Handle mock mode
        if self._base.use_mock:
            if full_timeline not in self._mock_sorted_sets:
                return 0
            entries = self._mock_sorted_sets[full_timeline]
            return len([1 for score, _ in entries if q.start_score <= score <= q.end_score])

        # Handle real Redis client
        if self._base._client is None:
            return 0

        return int(self._base._client.zcount(full_timeline, q.start_score, q.end_score))
