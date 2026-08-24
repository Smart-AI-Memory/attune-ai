"""Unit tests for Event Streaming (Pattern 4).

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime
from unittest.mock import Mock

from attune.telemetry.event_streaming import EventStreamer, StreamEvent


class TestStreamEvent:
    """Test StreamEvent dataclass."""

    def test_stream_event_creation(self):
        """Test creating a StreamEvent."""
        event = StreamEvent(
            event_id="1706356800000-0",
            event_type="agent_heartbeat",
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            data={"agent_id": "test-agent", "status": "running"},
            source="attune",
        )

        assert event.event_id == "1706356800000-0"
        assert event.event_type == "agent_heartbeat"
        assert event.data["agent_id"] == "test-agent"
        assert event.source == "attune"

    def test_to_dict(self):
        """Test converting StreamEvent to dict."""
        event = StreamEvent(
            event_id="1706356800000-0",
            event_type="coordination_signal",
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            data={"signal_type": "task_complete"},
            source="attune",
        )

        event_dict = event.to_dict()

        assert event_dict["event_id"] == "1706356800000-0"
        assert event_dict["event_type"] == "coordination_signal"
        assert event_dict["timestamp"] == "2026-01-27T12:00:00"
        assert event_dict["data"] == {"signal_type": "task_complete"}
        assert event_dict["source"] == "attune"

    def test_from_redis_entry(self):
        """Test creating StreamEvent from Redis stream entry."""
        event_id = "1706356800000-0"
        entry_data = {
            b"event_type": b"agent_heartbeat",
            b"timestamp": b"2026-01-27T12:00:00",
            b"data": b'{"agent_id": "test-agent"}',
            b"source": b"attune",
        }

        event = StreamEvent.from_redis_entry(event_id, entry_data)

        assert event.event_id == "1706356800000-0"
        assert event.event_type == "agent_heartbeat"
        assert event.data == {"agent_id": "test-agent"}
        assert event.source == "attune"

    def test_from_redis_entry_with_invalid_data(self):
        """Test from_redis_entry handles invalid JSON gracefully."""
        event_id = "1706356800000-0"
        entry_data = {
            b"event_type": b"test_event",
            b"timestamp": b"invalid-timestamp",
            b"data": b"invalid-json",
            b"source": b"test",
        }

        event = StreamEvent.from_redis_entry(event_id, entry_data)

        assert event.event_id == "1706356800000-0"
        assert event.event_type == "test_event"
        assert event.data == {}  # Invalid JSON fallback
        assert isinstance(event.timestamp, datetime)  # Falls back to utcnow


class TestEventStreamer:
    """Test EventStreamer class."""

    def test_init_without_memory(self):
        """Test EventStreamer initialization without memory backend."""
        streamer = EventStreamer()

        assert streamer.memory is None

    def test_init_with_memory(self):
        """Test EventStreamer initialization with memory backend."""
        mock_memory = Mock()
        streamer = EventStreamer(memory=mock_memory)

        assert streamer.memory == mock_memory

    def test_get_stream_key(self):
        """Test stream key generation."""
        streamer = EventStreamer()

        key = streamer._get_stream_key("agent_heartbeat")
        assert key == "stream:agent_heartbeat"

        key = streamer._get_stream_key("coordination_signal")
        assert key == "stream:coordination_signal"

    def test_publish_event_without_memory(self):
        """Test publish_event returns empty string when no memory backend."""
        streamer = EventStreamer()

        event_id = streamer.publish_event(event_type="test_event", data={"test": "data"})

        assert event_id == ""

    def test_publish_event_success(self):
        """Test successful event publishing."""
        mock_client = Mock()
        mock_client.xadd.return_value = b"1706356800000-0"

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        event_id = streamer.publish_event(
            event_type="agent_heartbeat",
            data={"agent_id": "test-agent", "status": "running"},
            source="attune",
        )

        assert event_id == "1706356800000-0"
        mock_client.xadd.assert_called_once()

        # Check XADD arguments
        call_args = mock_client.xadd.call_args
        assert call_args[0][0] == "stream:agent_heartbeat"
        assert call_args[1]["maxlen"] == 10000
        assert call_args[1]["approximate"] is True

    def test_publish_event_failure(self):
        """Test publish_event handles Redis errors gracefully."""
        mock_client = Mock()
        mock_client.xadd.side_effect = Exception("Redis error")

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        event_id = streamer.publish_event(event_type="test_event", data={"test": "data"})

        assert event_id == ""

    def test_get_recent_events_without_memory(self):
        """Test get_recent_events returns empty list when no memory backend."""
        streamer = EventStreamer()

        events = streamer.get_recent_events(event_type="test_event")

        assert events == []

    def test_get_recent_events_success(self):
        """Test successful retrieval of recent events."""
        mock_client = Mock()
        mock_client.xrevrange.return_value = [
            (
                b"1706356800000-0",
                {
                    b"event_type": b"agent_heartbeat",
                    b"timestamp": b"2026-01-27T12:00:00",
                    b"data": b'{"agent_id": "agent-1"}',
                    b"source": b"attune",
                },
            ),
            (
                b"1706356800001-0",
                {
                    b"event_type": b"agent_heartbeat",
                    b"timestamp": b"2026-01-27T12:00:01",
                    b"data": b'{"agent_id": "agent-2"}',
                    b"source": b"attune",
                },
            ),
        ]

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        events = streamer.get_recent_events(event_type="agent_heartbeat", count=2)

        assert len(events) == 2
        assert events[0].event_id == "1706356800000-0"
        assert events[0].data["agent_id"] == "agent-1"
        assert events[1].event_id == "1706356800001-0"
        assert events[1].data["agent_id"] == "agent-2"

    def test_get_recent_events_failure(self):
        """Test get_recent_events handles Redis errors gracefully."""
        mock_client = Mock()
        mock_client.xrevrange.side_effect = Exception("Redis error")

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        events = streamer.get_recent_events(event_type="test_event")

        assert events == []

    def test_get_stream_info_success(self):
        """Test get_stream_info returns stream metadata."""
        mock_client = Mock()
        mock_client.xinfo_stream.return_value = {
            b"length": 100,
            b"first-entry": [b"1706356800000-0", {b"data": b"..."}],
        }

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        info = streamer.get_stream_info(event_type="agent_heartbeat")

        assert info["length"] == 100
        assert "first-entry" in info

    def test_get_stream_info_failure(self):
        """Test get_stream_info handles errors gracefully."""
        mock_client = Mock()
        mock_client.xinfo_stream.side_effect = Exception("Stream does not exist")

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        info = streamer.get_stream_info(event_type="nonexistent")

        assert info == {}

    def test_delete_stream_success(self):
        """Test successful stream deletion."""
        mock_client = Mock()
        mock_client.delete.return_value = 1

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        result = streamer.delete_stream(event_type="test_event")

        assert result is True
        mock_client.delete.assert_called_once_with("stream:test_event")

    def test_delete_stream_not_found(self):
        """Test delete_stream returns False when stream doesn't exist."""
        mock_client = Mock()
        mock_client.delete.return_value = 0

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        result = streamer.delete_stream(event_type="nonexistent")

        assert result is False

    def test_trim_stream_success(self):
        """Test successful stream trimming."""
        mock_client = Mock()
        mock_client.xtrim.return_value = 50

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        trimmed = streamer.trim_stream(event_type="agent_heartbeat", max_length=1000)

        assert trimmed == 50
        mock_client.xtrim.assert_called_once_with(
            "stream:agent_heartbeat",
            maxlen=1000,
            approximate=True,
        )

    def test_trim_stream_failure(self):
        """Test trim_stream handles errors gracefully."""
        mock_client = Mock()
        mock_client.xtrim.side_effect = Exception("Trim error")

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        trimmed = streamer.trim_stream(event_type="test_event", max_length=1000)

        assert trimmed == 0


class TestEventStreamerIntegration:
    """Integration tests for EventStreamer."""

    def test_consume_events_without_memory(self):
        """Test consume_events returns empty iterator when no memory backend."""
        streamer = EventStreamer()

        events = list(streamer.consume_events(event_types=["test_event"]))

        assert events == []

    def test_publish_and_retrieve_event_flow(self):
        """Test complete flow of publishing and retrieving events."""
        mock_client = Mock()

        # Mock xadd (publish)
        mock_client.xadd.return_value = b"1706356800000-0"

        # Mock xrevrange (retrieve)
        mock_client.xrevrange.return_value = [
            (
                b"1706356800000-0",
                {
                    b"event_type": b"agent_heartbeat",
                    b"timestamp": b"2026-01-27T12:00:00",
                    b"data": b'{"agent_id": "test-agent", "status": "running"}',
                    b"source": b"attune",
                },
            ),
        ]

        mock_memory = Mock()
        mock_memory._client = mock_client

        streamer = EventStreamer(memory=mock_memory)

        # Publish event
        event_id = streamer.publish_event(
            event_type="agent_heartbeat",
            data={"agent_id": "test-agent", "status": "running"},
        )

        assert event_id == "1706356800000-0"

        # Retrieve recent events
        events = streamer.get_recent_events(event_type="agent_heartbeat", count=10)

        assert len(events) == 1
        assert events[0].event_id == "1706356800000-0"
        assert events[0].data["agent_id"] == "test-agent"
        assert events[0].data["status"] == "running"


class TestStreamRegistry:
    """The registry set replaces keyspace scans for subscribe-to-all (#2241)."""

    @staticmethod
    def _streamer_with_client():
        mock_client = Mock()
        mock_memory = Mock()
        mock_memory._client = mock_client
        return EventStreamer(memory=mock_memory), mock_client

    def test_publish_registers_stream_key(self):
        """publish_event SADDs the stream key into the registry set."""
        streamer, client = self._streamer_with_client()
        client.xadd.return_value = b"1-0"

        streamer.publish_event(event_type="agent_heartbeat", data={"a": 1})

        client.sadd.assert_called_once_with("stream_registry", "stream:agent_heartbeat")

    def test_active_stream_keys_reads_registry_not_scan(self):
        """A populated registry answers without any keyspace scan."""
        streamer, client = self._streamer_with_client()
        client.smembers.return_value = {b"stream:b", "stream:a"}

        keys = streamer._active_stream_keys()

        assert keys == ["stream:a", "stream:b"]
        client.scan_iter.assert_not_called()

    def test_active_stream_keys_falls_back_to_scan_when_registry_empty(self):
        """Streams published by pre-registry code are still discovered.

        The positive assertion below proves the scan result is actually
        consumed (no broad-except swallows it), but the transport gate is
        satisfied explicitly: mget is served in terms of get.
        """
        from tests.unit.telemetry.conftest import serve_mget_from_get

        streamer, client = self._streamer_with_client()
        serve_mget_from_get(client)
        client.smembers.return_value = set()
        client.scan_iter.return_value = iter([b"stream:legacy"])

        keys = streamer._active_stream_keys()

        assert keys == ["stream:legacy"]
        client.scan_iter.assert_called_once_with(match="stream:*", count=100)

    def test_delete_stream_unregisters_key(self):
        """delete_stream SREMs the key so the registry does not go stale."""
        streamer, client = self._streamer_with_client()
        client.delete.return_value = 1

        assert streamer.delete_stream(event_type="old_event") is True
        client.srem.assert_called_once_with("stream_registry", "stream:old_event")

    def test_publish_succeeds_even_if_registration_fails(self):
        """A registry SADD failure never fails the already-committed XADD."""
        streamer, client = self._streamer_with_client()
        client.xadd.return_value = b"1-0"
        client.sadd.side_effect = RuntimeError("registry down")

        event_id = streamer.publish_event(event_type="agent_heartbeat", data={"a": 1})

        assert event_id == "1-0"
