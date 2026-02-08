"""Real-Time Event Streaming using Redis Streams.

Pattern 4 from Agent Coordination Architecture - Publish agent events
to Redis Streams for real-time monitoring and WebSocket consumption.

Events types:
- agent_heartbeat: Agent liveness updates
- coordination_signal: Inter-agent coordination messages
- workflow_progress: Workflow stage progress
- agent_error: Agent failures and errors

Usage:
    # Publish events
    streamer = EventStreamer()
    streamer.publish_event(
        event_type="agent_heartbeat",
        data={"agent_id": "worker-1", "status": "running", "progress": 0.5}
    )

    # Consume events (blocking)
    for event in streamer.consume_events(event_types=["agent_heartbeat"]):
        print(f"Received: {event}")

    # Get recent events (non-blocking)
    recent = streamer.get_recent_events(event_type="agent_heartbeat", count=100)

Copyright 2025 Smart-AI-Memory
Licensed under Fair Source License 0.9
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Event published to Redis Stream."""

    event_id: str  # Redis stream entry ID (e.g., "1706356800000-0")
    event_type: str  # "agent_heartbeat", "coordination_signal", etc.
    timestamp: datetime
    data: dict[str, Any]
    source: str = "attune"  # Source system

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": (
                self.timestamp.isoformat()
                if isinstance(self.timestamp, datetime)
                else self.timestamp
            ),
            "data": self.data,
            "source": self.source,
        }

    @classmethod
    def from_redis_entry(cls, event_id: str, entry_data: dict[bytes, bytes]) -> StreamEvent:
        """Create from Redis stream entry.

        Args:
            event_id: Redis stream entry ID
            entry_data: Raw entry data from Redis (bytes dict or str dict)

        Returns:
            StreamEvent instance
        """
        # Decode bytes to strings (handle both bytes and str)
        decoded = {}
        for k, v in entry_data.items():
            key = k.decode("utf-8") if isinstance(k, bytes) else k
            value = v.decode("utf-8") if isinstance(v, bytes) else v
            decoded[key] = value

        # Parse timestamp
        timestamp_str = decoded.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
        except (ValueError, AttributeError):
            timestamp = datetime.utcnow()

        # Parse data field (JSON)
        data_str = decoded.get("data", "{}")
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            data = {}

        return cls(
            event_id=event_id,
            event_type=decoded.get("event_type", "unknown"),
            timestamp=timestamp,
            data=data,
            source=decoded.get("source", "attune"),
        )


class EventStreamer:
    """Real-time event streaming using Redis Streams.

    Publishes events to Redis Streams and provides methods for consuming
    events via polling or blocking reads.

    Stream naming: stream:{event_type}
    Examples:
    - stream:agent_heartbeat
    - stream:coordination_signal
    - stream:workflow_progress
    """

    STREAM_PREFIX = "stream:"
    MAX_STREAM_LENGTH = 10000  # Trim streams to last 10K events
    DEFAULT_BLOCK_MS = 5000  # 5 seconds blocking read timeout

    def __init__(self, memory=None):
        """Initialize event streamer.

        Args:
            memory: Memory backend with Redis connection
        """
        self.memory = memory

        if self.memory is None:
            try:
                from attune.telemetry import UsageTracker

                tracker = UsageTracker.get_instance()
                if hasattr(tracker, "_memory"):
                    self.memory = tracker._memory
            except (ImportError, AttributeError):
                pass

        if self.memory is None:
            logger.warning("No memory backend available for event streaming")

    def _get_stream_key(self, event_type: str) -> str:
        """Get Redis stream key for an event type.

        Args:
            event_type: Type of event

        Returns:
            Stream key (e.g., "stream:agent_heartbeat")
        """
        return f"{self.STREAM_PREFIX}{event_type}"

    def publish_event(
        self,
        event_type: str,
        data: dict[str, Any],
        source: str = "attune",
    ) -> str:
        """Publish an event to Redis Stream.

        Args:
            event_type: Type of event (e.g., "agent_heartbeat", "coordination_signal")
            data: Event payload data
            source: Source system (default "attune")

        Returns:
            Event ID (Redis stream entry ID) if successful, empty string otherwise
        """
        if not self.memory or not hasattr(self.memory, "_client") or not self.memory._client:
            logger.debug("Cannot publish event: no Redis backend")
            return ""

        stream_key = self._get_stream_key(event_type)

        # Prepare entry data
        entry = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": json.dumps(data),
            "source": source,
        }

        try:
            # Add to stream with automatic trimming (MAXLEN)
            event_id = self.memory._client.xadd(
                stream_key,
                entry,
                maxlen=self.MAX_STREAM_LENGTH,
                approximate=True,  # Use ~ for performance
            )

            # Decode event_id if bytes
            if isinstance(event_id, bytes):
                event_id = event_id.decode("utf-8")

            logger.debug(f"Published event {event_type}: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return ""

    def consume_events(
        self,
        event_types: list[str] | None = None,
        block_ms: int | None = None,
        count: int = 10,
        start_id: str = "$",
    ) -> Iterator[StreamEvent]:
        """Consume events from Redis Streams (blocking iterator).

        Args:
            event_types: List of event types to consume (None = all types)
            block_ms: Blocking timeout in milliseconds (None = DEFAULT_BLOCK_MS)
            count: Number of events to read per batch
            start_id: Stream position to start from ("$" = new events only, "0" = all events)

        Yields:
            StreamEvent instances as they arrive

        Example:
            >>> streamer = EventStreamer()
            >>> for event in streamer.consume_events(event_types=["agent_heartbeat"]):
            ...     print(f"Agent {event.data['agent_id']} status: {event.data['status']}")
        """
        if not self.memory or not hasattr(self.memory, "_client") or not self.memory._client:
            logger.warning("Cannot consume events: no Redis backend")
            return

        block_ms = block_ms if block_ms is not None else self.DEFAULT_BLOCK_MS

        # Determine streams to read
        if event_types:
            streams = {self._get_stream_key(et): start_id for et in event_types}
        else:
            # Subscribe to all event streams (expensive - requires KEYS scan)
            all_streams = list(
                self.memory._client.scan_iter(match=f"{self.STREAM_PREFIX}*", count=100)
            )
            streams = {
                s.decode("utf-8") if isinstance(s, bytes) else s: start_id for s in all_streams
            }

        if not streams:
            logger.debug("No streams to consume")
            return

        # Track last IDs for each stream
        last_ids = streams.copy()

        try:
            while True:
                # XREAD: blocking read from multiple streams
                results = self.memory._client.xread(
                    last_ids,
                    count=count,
                    block=block_ms,
                )

                if not results:
                    # Timeout - no new events
                    continue

                # Process results
                for stream_key, entries in results:
                    # Decode stream key if bytes
                    if isinstance(stream_key, bytes):
                        stream_key = stream_key.decode("utf-8")

                    for event_id, entry_data in entries:
                        # Decode event_id if bytes
                        if isinstance(event_id, bytes):
                            event_id = event_id.decode("utf-8")

                        # Parse event
                        event = StreamEvent.from_redis_entry(event_id, entry_data)
                        yield event

                        # Update last_id for this stream
                        last_ids[stream_key] = event_id

        except KeyboardInterrupt:
            logger.info("Event consumption interrupted")
        except Exception as e:
            logger.error(f"Error consuming events: {e}")

    def get_recent_events(
        self,
        event_type: str,
        count: int = 100,
        start_id: str = "-",
        end_id: str = "+",
    ) -> list[StreamEvent]:
        """Get recent events from a stream (non-blocking).

        Args:
            event_type: Type of event to retrieve
            count: Maximum number of events to return
            start_id: Start position ("-" = oldest, specific ID = from that point)
            end_id: End position ("+" = newest, specific ID = up to that point)

        Returns:
            List of recent events (newest first)
        """
        if not self.memory or not hasattr(self.memory, "_client") or not self.memory._client:
            logger.debug("Cannot get recent events: no Redis backend")
            return []

        stream_key = self._get_stream_key(event_type)

        try:
            # XREVRANGE: get events in reverse chronological order
            results = self.memory._client.xrevrange(
                stream_key,
                max=end_id,
                min=start_id,
                count=count,
            )

            events = []
            for event_id, entry_data in results:
                # Decode event_id if bytes
                if isinstance(event_id, bytes):
                    event_id = event_id.decode("utf-8")

                event = StreamEvent.from_redis_entry(event_id, entry_data)
                events.append(event)

            return events

        except Exception as e:
            logger.error("Failed to get recent events for %s", event_type, exc_info=True)
            return []

    def get_stream_info(self, event_type: str) -> dict[str, Any]:
        """Get information about a stream.

        Args:
            event_type: Type of event stream

        Returns:
            Dictionary with stream info (length, first_entry, last_entry, etc.)
        """
        if not self.memory or not hasattr(self.memory, "_client") or not self.memory._client:
            return {}

        stream_key = self._get_stream_key(event_type)

        try:
            info = self.memory._client.xinfo_stream(stream_key)

            # Decode bytes keys/values
            decoded_info = {}
            for key, value in info.items():
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                decoded_info[key] = value

            return decoded_info

        except Exception as e:
            logger.debug(f"Failed to get stream info for {event_type}: {e}")
            return {}

    def delete_stream(self, event_type: str) -> bool:
        """Delete an event stream.

        Args:
            event_type: Type of event stream to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.memory or not hasattr(self.memory, "_client") or not self.memory._client:
            return False

        stream_key = self._get_stream_key(event_type)

        try:
            result = self.memory._client.delete(stream_key)
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete stream {event_type}: {e}")
            return False

    def trim_stream(self, event_type: str, max_length: int = 1000) -> int:
        """Trim a stream to a maximum length.

        Args:
            event_type: Type of event stream
            max_length: Maximum number of events to keep

        Returns:
            Number of events trimmed
        """
        if not self.memory or not hasattr(self.memory, "_client") or not self.memory._client:
            return 0

        stream_key = self._get_stream_key(event_type)

        try:
            # XTRIM: trim to approximate max length
            trimmed = self.memory._client.xtrim(
                stream_key,
                maxlen=max_length,
                approximate=True,
            )
            return trimmed
        except Exception as e:
            logger.error(f"Failed to trim stream {event_type}: {e}")
            return 0
