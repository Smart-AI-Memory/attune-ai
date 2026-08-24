"""Unit tests for attune.telemetry.event_streaming module.

Tests cover:
- StreamEvent dataclass (to_dict, from_redis_entry)
- EventStreamer initialization (with and without memory)
- EventStreamer.publish_event graceful degradation
- EventStreamer.publish_event with mock Redis client
- EventStreamer.consume_events graceful degradation and with mock Redis
- EventStreamer.get_recent_events graceful degradation and with mock Redis
- EventStreamer.get_stream_info graceful degradation and with mock Redis
- EventStreamer.delete_stream graceful degradation and with mock Redis
- EventStreamer.trim_stream graceful degradation and with mock Redis

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from attune.telemetry.event_streaming import EventStreamer, StreamEvent

# ---------------------------------------------------------------------------
# StreamEvent dataclass tests
# ---------------------------------------------------------------------------


class TestStreamEvent:
    """Tests for the StreamEvent dataclass."""

    def test_to_dict_with_datetime_timestamp(self) -> None:
        """Test to_dict converts datetime timestamp to ISO format."""
        ts = datetime(2026, 1, 15, 10, 30, 0)
        event = StreamEvent(
            event_id="1706356800000-0",
            event_type="agent_heartbeat",
            timestamp=ts,
            data={"agent_id": "worker-1", "status": "running"},
            source="attune",
        )
        result = event.to_dict()

        assert result["event_id"] == "1706356800000-0"
        assert result["event_type"] == "agent_heartbeat"
        assert result["timestamp"] == ts.isoformat()
        assert result["data"] == {"agent_id": "worker-1", "status": "running"}
        assert result["source"] == "attune"

    def test_to_dict_with_string_timestamp(self) -> None:
        """Test to_dict passes through non-datetime timestamp as-is."""
        event = StreamEvent(
            event_id="123-0",
            event_type="workflow_progress",
            timestamp="2026-01-15T10:30:00",  # type: ignore[arg-type]
            data={"step": 3},
            source="test",
        )
        result = event.to_dict()

        assert result["timestamp"] == "2026-01-15T10:30:00"

    def test_to_dict_default_source(self) -> None:
        """Test that default source is 'attune'."""
        event = StreamEvent(
            event_id="1-0",
            event_type="test",
            timestamp=datetime.now(timezone.utc),
            data={},
        )
        assert event.source == "attune"
        assert event.to_dict()["source"] == "attune"

    def test_from_redis_entry_with_bytes(self) -> None:
        """Test from_redis_entry decodes bytes keys and values."""
        entry_data = {
            b"event_type": b"coordination_signal",
            b"timestamp": b"2026-01-15T10:30:00",
            b"data": b'{"msg": "hello"}',
            b"source": b"test-source",
        }
        event = StreamEvent.from_redis_entry("100-0", entry_data)

        assert event.event_id == "100-0"
        assert event.event_type == "coordination_signal"
        assert event.timestamp == datetime(2026, 1, 15, 10, 30, 0)
        assert event.data == {"msg": "hello"}
        assert event.source == "test-source"

    def test_from_redis_entry_with_strings(self) -> None:
        """Test from_redis_entry handles string keys and values."""
        entry_data = {
            "event_type": "agent_error",
            "timestamp": "2026-02-01T12:00:00",
            "data": '{"error": "timeout"}',
            "source": "attune",
        }
        event = StreamEvent.from_redis_entry("200-0", entry_data)

        assert event.event_type == "agent_error"
        assert event.data == {"error": "timeout"}

    def test_from_redis_entry_invalid_timestamp_falls_back(self) -> None:
        """Test from_redis_entry uses utcnow for invalid timestamps."""
        entry_data = {
            b"event_type": b"test",
            b"timestamp": b"not-a-date",
            b"data": b"{}",
        }
        before = datetime.now(timezone.utc)
        event = StreamEvent.from_redis_entry("300-0", entry_data)
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_from_redis_entry_missing_timestamp_falls_back(self) -> None:
        """Test from_redis_entry uses utcnow when timestamp key is missing."""
        entry_data = {
            b"event_type": b"test",
            b"data": b"{}",
        }
        before = datetime.now(timezone.utc)
        event = StreamEvent.from_redis_entry("400-0", entry_data)
        after = datetime.now(timezone.utc)

        assert before <= event.timestamp <= after

    def test_from_redis_entry_invalid_json_data(self) -> None:
        """Test from_redis_entry returns empty dict for invalid JSON data."""
        entry_data = {
            b"event_type": b"test",
            b"timestamp": b"2026-01-15T10:30:00",
            b"data": b"not-valid-json{{{",
        }
        event = StreamEvent.from_redis_entry("500-0", entry_data)

        assert event.data == {}

    def test_from_redis_entry_missing_data_field(self) -> None:
        """Test from_redis_entry defaults to empty dict when data key is absent."""
        entry_data = {
            b"event_type": b"test",
            b"timestamp": b"2026-01-15T10:30:00",
        }
        event = StreamEvent.from_redis_entry("600-0", entry_data)

        assert event.data == {}

    def test_from_redis_entry_missing_event_type(self) -> None:
        """Test from_redis_entry defaults event_type to 'unknown'."""
        entry_data = {
            b"timestamp": b"2026-01-15T10:30:00",
            b"data": b"{}",
        }
        event = StreamEvent.from_redis_entry("700-0", entry_data)

        assert event.event_type == "unknown"

    def test_from_redis_entry_missing_source(self) -> None:
        """Test from_redis_entry defaults source to 'attune'."""
        entry_data = {
            b"event_type": b"test",
            b"timestamp": b"2026-01-15T10:30:00",
            b"data": b"{}",
        }
        event = StreamEvent.from_redis_entry("800-0", entry_data)

        assert event.source == "attune"


# ---------------------------------------------------------------------------
# EventStreamer tests
# ---------------------------------------------------------------------------


class TestEventStreamerInit:
    """Tests for EventStreamer.__init__."""

    def test_init_with_memory_provided(self) -> None:
        """Test initialization when memory is explicitly provided."""
        mock_memory = MagicMock()
        streamer = EventStreamer(memory=mock_memory)

        assert streamer.memory is mock_memory

    def test_init_with_memory_none_graceful_degradation(self) -> None:
        """Test initialization with memory=None degrades gracefully."""
        # Patch the local import inside __init__ so it raises ImportError
        with patch.dict(
            "sys.modules",
            {
                "attune.telemetry": MagicMock(
                    UsageTracker=MagicMock(
                        get_instance=MagicMock(side_effect=ImportError("no tracker")),
                    ),
                ),
            },
        ):
            streamer = EventStreamer(memory=None)
            assert streamer.memory is None

    def test_init_fallback_to_usage_tracker_memory(self) -> None:
        """Test __init__ attempts to get memory from UsageTracker when memory=None."""
        mock_memory = MagicMock()
        mock_tracker = MagicMock()
        mock_tracker._memory = mock_memory

        mock_usage_tracker_cls = MagicMock()
        mock_usage_tracker_cls.get_instance.return_value = mock_tracker

        mock_telemetry_module = MagicMock()
        mock_telemetry_module.UsageTracker = mock_usage_tracker_cls

        with patch.dict("sys.modules", {"attune.telemetry": mock_telemetry_module}):
            streamer = EventStreamer(memory=None)
            assert streamer.memory is mock_memory

    def test_init_fallback_import_error(self) -> None:
        """Test __init__ handles ImportError when UsageTracker is not available."""
        # Make the import itself fail
        import sys

        saved = sys.modules.get("attune.telemetry")
        sys.modules["attune.telemetry"] = None  # type: ignore[assignment]
        try:
            streamer = EventStreamer(memory=None)
            assert streamer.memory is None
        finally:
            if saved is not None:
                sys.modules["attune.telemetry"] = saved
            else:
                del sys.modules["attune.telemetry"]

    def test_init_fallback_attribute_error(self) -> None:
        """Test __init__ handles AttributeError when tracker has no _memory."""
        mock_tracker = MagicMock(spec=[])  # No attributes at all

        mock_usage_tracker_cls = MagicMock()
        mock_usage_tracker_cls.get_instance.return_value = mock_tracker

        mock_telemetry_module = MagicMock()
        mock_telemetry_module.UsageTracker = mock_usage_tracker_cls

        with patch.dict("sys.modules", {"attune.telemetry": mock_telemetry_module}):
            streamer = EventStreamer(memory=None)
            # memory should remain None since tracker has no _memory attr
            assert streamer.memory is None


class TestEventStreamerGetStreamKey:
    """Tests for EventStreamer._get_stream_key."""

    def test_get_stream_key_format(self) -> None:
        """Test stream key follows expected prefix format."""
        streamer = EventStreamer(memory=MagicMock())

        assert streamer._get_stream_key("agent_heartbeat") == "stream:agent_heartbeat"
        assert streamer._get_stream_key("workflow_progress") == "stream:workflow_progress"
        assert streamer._get_stream_key("coordination_signal") == "stream:coordination_signal"


class TestEventStreamerPublishEvent:
    """Tests for EventStreamer.publish_event."""

    def test_publish_event_no_memory_returns_empty(self) -> None:
        """Test publish_event returns '' when no memory backend."""
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = None

        result = streamer.publish_event(
            event_type="agent_heartbeat",
            data={"agent_id": "w-1"},
        )
        assert result == ""

    def test_publish_event_memory_without_client_returns_empty(self) -> None:
        """Test publish_event returns '' when memory has no _client attribute."""
        mock_memory = MagicMock(spec=[])  # No _client attr
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.publish_event(
            event_type="agent_heartbeat",
            data={"status": "running"},
        )
        assert result == ""

    def test_publish_event_memory_client_is_none_returns_empty(self) -> None:
        """Test publish_event returns '' when memory._client is None."""
        mock_memory = MagicMock()
        mock_memory._client = None
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.publish_event(
            event_type="agent_heartbeat",
            data={"status": "running"},
        )
        assert result == ""

    def test_publish_event_success_with_string_id(self) -> None:
        """Test publish_event succeeds and returns event ID as string."""
        mock_client = MagicMock()
        mock_client.xadd.return_value = "1706356800000-0"

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.publish_event(
            event_type="agent_heartbeat",
            data={"agent_id": "w-1", "status": "running"},
            source="test",
        )

        assert result == "1706356800000-0"
        mock_client.xadd.assert_called_once()

        # Verify the call arguments
        call_args = mock_client.xadd.call_args
        assert call_args[0][0] == "stream:agent_heartbeat"
        entry = call_args[0][1]
        assert entry["event_type"] == "agent_heartbeat"
        assert entry["source"] == "test"
        assert json.loads(entry["data"]) == {"agent_id": "w-1", "status": "running"}
        assert call_args[1]["maxlen"] == 10000
        assert call_args[1]["approximate"] is True

    def test_publish_event_success_with_bytes_id(self) -> None:
        """Test publish_event decodes bytes event ID from Redis."""
        mock_client = MagicMock()
        mock_client.xadd.return_value = b"1706356800000-1"

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.publish_event(
            event_type="workflow_progress",
            data={"step": 2},
        )

        assert result == "1706356800000-1"

    def test_publish_event_redis_error_returns_empty(self) -> None:
        """Test publish_event returns '' when Redis raises an exception."""
        mock_client = MagicMock()
        mock_client.xadd.side_effect = ConnectionError("Redis unavailable")

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.publish_event(
            event_type="agent_error",
            data={"error": "test"},
        )

        assert result == ""

    def test_publish_event_default_source_is_attune(self) -> None:
        """Test publish_event uses 'attune' as default source."""
        mock_client = MagicMock()
        mock_client.xadd.return_value = "1-0"

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        streamer.publish_event(event_type="test", data={})

        call_args = mock_client.xadd.call_args
        entry = call_args[0][1]
        assert entry["source"] == "attune"


class TestEventStreamerConsumeEvents:
    """Tests for EventStreamer.consume_events."""

    def test_consume_events_no_memory_yields_nothing(self) -> None:
        """Test consume_events yields nothing when no memory backend."""
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = None

        events = list(streamer.consume_events(event_types=["test"]))
        assert events == []

    def test_consume_events_no_client_yields_nothing(self) -> None:
        """Test consume_events yields nothing when memory has no _client."""
        mock_memory = MagicMock(spec=[])
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        events = list(streamer.consume_events(event_types=["test"]))
        assert events == []

    def test_consume_events_client_is_none_yields_nothing(self) -> None:
        """Test consume_events yields nothing when memory._client is None."""
        mock_memory = MagicMock()
        mock_memory._client = None
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        events = list(streamer.consume_events(event_types=["test"]))
        assert events == []

    def test_consume_events_with_event_types_builds_correct_streams(self) -> None:
        """Test consume_events subscribes to correct stream keys."""
        mock_client = MagicMock()
        # Return one batch then raise to exit the while loop
        mock_client.xread.side_effect = KeyboardInterrupt()

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        list(streamer.consume_events(event_types=["agent_heartbeat", "agent_error"]))

        mock_client.xread.assert_called_once()
        call_args = mock_client.xread.call_args
        streams_arg = call_args[0][0]
        assert "stream:agent_heartbeat" in streams_arg
        assert "stream:agent_error" in streams_arg

    def test_consume_events_no_event_types_reads_registry(self) -> None:
        """consume_events with event_types=None subscribes to the streams
        named by the registry set — no keyspace scan (#2241)."""
        mock_client = MagicMock()
        mock_client.smembers.return_value = {b"stream:heartbeat", b"stream:error"}
        mock_client.xread.side_effect = KeyboardInterrupt()

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        list(streamer.consume_events(event_types=None))

        mock_client.smembers.assert_called_once_with("stream_registry")
        mock_client.scan_iter.assert_not_called()
        streams_arg = mock_client.xread.call_args[0][0]
        assert "stream:heartbeat" in streams_arg
        assert "stream:error" in streams_arg

    def test_consume_events_empty_streams_returns(self) -> None:
        """consume_events returns when registry and legacy scan are both empty."""
        mock_client = MagicMock()
        mock_client.smembers.return_value = set()  # Empty registry
        mock_client.scan_iter.return_value = []  # No pre-registry streams either

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        events = list(streamer.consume_events(event_types=None))
        assert events == []
        mock_client.xread.assert_not_called()

    def test_consume_events_yields_parsed_events(self) -> None:
        """Test consume_events yields StreamEvent instances from xread results."""
        mock_client = MagicMock()

        # First call returns data, second call raises KeyboardInterrupt to exit
        xread_result = [
            (
                b"stream:agent_heartbeat",
                [
                    (
                        b"1706356800000-0",
                        {
                            b"event_type": b"agent_heartbeat",
                            b"timestamp": b"2026-01-15T10:30:00",
                            b"data": b'{"agent_id": "w-1"}',
                            b"source": b"attune",
                        },
                    ),
                ],
            ),
        ]
        mock_client.xread.side_effect = [xread_result, KeyboardInterrupt()]

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        events = list(streamer.consume_events(event_types=["agent_heartbeat"], count=5))

        assert len(events) == 1
        assert events[0].event_id == "1706356800000-0"
        assert events[0].event_type == "agent_heartbeat"
        assert events[0].data == {"agent_id": "w-1"}

    def test_consume_events_uses_custom_block_ms(self) -> None:
        """Test consume_events respects custom block_ms parameter."""
        mock_client = MagicMock()
        mock_client.xread.side_effect = KeyboardInterrupt()

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        list(streamer.consume_events(event_types=["test"], block_ms=1000, count=1))

        call_args = mock_client.xread.call_args
        assert call_args[1]["block"] == 1000
        assert call_args[1]["count"] == 1

    def test_consume_events_uses_default_block_ms(self) -> None:
        """Test consume_events uses DEFAULT_BLOCK_MS when block_ms is None."""
        mock_client = MagicMock()
        mock_client.xread.side_effect = KeyboardInterrupt()

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        list(streamer.consume_events(event_types=["test"]))

        call_args = mock_client.xread.call_args
        assert call_args[1]["block"] == EventStreamer.DEFAULT_BLOCK_MS

    def test_consume_events_handles_generic_exception(self) -> None:
        """Test consume_events handles generic exceptions without crashing."""
        mock_client = MagicMock()
        mock_client.xread.side_effect = RuntimeError("connection lost")

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        # Should not raise
        events = list(streamer.consume_events(event_types=["test"]))
        assert events == []

    def test_consume_events_timeout_continues_loop(self) -> None:
        """Test consume_events continues when xread returns empty (timeout)."""
        mock_client = MagicMock()
        # First call returns None (timeout), second returns data, third exits
        xread_result = [
            (
                b"stream:test",
                [
                    (
                        b"1-0",
                        {
                            b"event_type": b"test",
                            b"timestamp": b"2026-01-15T10:30:00",
                            b"data": b"{}",
                            b"source": b"attune",
                        },
                    ),
                ],
            ),
        ]
        mock_client.xread.side_effect = [None, xread_result, KeyboardInterrupt()]

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        events = list(streamer.consume_events(event_types=["test"]))

        assert len(events) == 1
        assert mock_client.xread.call_count == 3


class TestEventStreamerGetRecentEvents:
    """Tests for EventStreamer.get_recent_events."""

    def test_get_recent_events_no_memory_returns_empty(self) -> None:
        """Test get_recent_events returns [] when no memory backend."""
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = None

        result = streamer.get_recent_events(event_type="agent_heartbeat")
        assert result == []

    def test_get_recent_events_no_client_returns_empty(self) -> None:
        """Test get_recent_events returns [] when memory has no _client."""
        mock_memory = MagicMock(spec=[])
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_recent_events(event_type="test")
        assert result == []

    def test_get_recent_events_client_is_none_returns_empty(self) -> None:
        """Test get_recent_events returns [] when _client is None."""
        mock_memory = MagicMock()
        mock_memory._client = None
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_recent_events(event_type="test")
        assert result == []

    def test_get_recent_events_returns_parsed_events(self) -> None:
        """Test get_recent_events returns list of StreamEvent from xrevrange."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = [
            (
                b"2-0",
                {
                    b"event_type": b"workflow_progress",
                    b"timestamp": b"2026-01-15T11:00:00",
                    b"data": b'{"step": 2}',
                    b"source": b"attune",
                },
            ),
            (
                b"1-0",
                {
                    b"event_type": b"workflow_progress",
                    b"timestamp": b"2026-01-15T10:30:00",
                    b"data": b'{"step": 1}',
                    b"source": b"attune",
                },
            ),
        ]

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_recent_events(event_type="workflow_progress", count=10)

        assert len(result) == 2
        assert result[0].event_id == "2-0"
        assert result[0].data == {"step": 2}
        assert result[1].event_id == "1-0"
        assert result[1].data == {"step": 1}

        mock_client.xrevrange.assert_called_once_with(
            "stream:workflow_progress",
            max="+",
            min="-",
            count=10,
        )

    def test_get_recent_events_with_custom_range(self) -> None:
        """Test get_recent_events passes start_id and end_id to xrevrange."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = []

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        streamer.get_recent_events(
            event_type="test",
            count=50,
            start_id="100-0",
            end_id="200-0",
        )

        mock_client.xrevrange.assert_called_once_with(
            "stream:test",
            max="200-0",
            min="100-0",
            count=50,
        )

    def test_get_recent_events_with_string_event_ids(self) -> None:
        """Test get_recent_events handles string event IDs (not bytes)."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = [
            (
                "3-0",  # String, not bytes
                {
                    b"event_type": b"test",
                    b"timestamp": b"2026-01-15T12:00:00",
                    b"data": b"{}",
                },
            ),
        ]

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_recent_events(event_type="test")

        assert len(result) == 1
        assert result[0].event_id == "3-0"

    def test_get_recent_events_redis_error_returns_empty(self) -> None:
        """Test get_recent_events returns [] on Redis exception."""
        mock_client = MagicMock()
        mock_client.xrevrange.side_effect = ConnectionError("Redis down")

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_recent_events(event_type="test")
        assert result == []


class TestEventStreamerGetStreamInfo:
    """Tests for EventStreamer.get_stream_info."""

    def test_get_stream_info_no_memory_returns_empty_dict(self) -> None:
        """Test get_stream_info returns {} when no memory backend."""
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = None

        result = streamer.get_stream_info(event_type="test")
        assert result == {}

    def test_get_stream_info_no_client_returns_empty_dict(self) -> None:
        """Test get_stream_info returns {} when memory has no _client."""
        mock_memory = MagicMock(spec=[])
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_stream_info(event_type="test")
        assert result == {}

    def test_get_stream_info_client_is_none_returns_empty_dict(self) -> None:
        """Test get_stream_info returns {} when _client is None."""
        mock_memory = MagicMock()
        mock_memory._client = None
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_stream_info(event_type="test")
        assert result == {}

    def test_get_stream_info_returns_decoded_info(self) -> None:
        """Test get_stream_info decodes bytes keys/values from xinfo_stream."""
        mock_client = MagicMock()
        mock_client.xinfo_stream.return_value = {
            b"length": 42,
            b"first-entry": b"1-0",
            b"last-entry": b"42-0",
            "groups": 0,  # Already a string key with int value
        }

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_stream_info(event_type="agent_heartbeat")

        assert result["length"] == 42
        assert result["first-entry"] == "1-0"
        assert result["last-entry"] == "42-0"
        assert result["groups"] == 0

        mock_client.xinfo_stream.assert_called_once_with("stream:agent_heartbeat")

    def test_get_stream_info_redis_error_returns_empty_dict(self) -> None:
        """Test get_stream_info returns {} on Redis exception."""
        mock_client = MagicMock()
        mock_client.xinfo_stream.side_effect = ConnectionError("Redis down")

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.get_stream_info(event_type="test")
        assert result == {}


class TestEventStreamerDeleteStream:
    """Tests for EventStreamer.delete_stream."""

    def test_delete_stream_no_memory_returns_false(self) -> None:
        """Test delete_stream returns False when no memory backend."""
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = None

        assert streamer.delete_stream(event_type="test") is False

    def test_delete_stream_no_client_returns_false(self) -> None:
        """Test delete_stream returns False when memory has no _client."""
        mock_memory = MagicMock(spec=[])
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.delete_stream(event_type="test") is False

    def test_delete_stream_client_is_none_returns_false(self) -> None:
        """Test delete_stream returns False when _client is None."""
        mock_memory = MagicMock()
        mock_memory._client = None
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.delete_stream(event_type="test") is False

    def test_delete_stream_success_returns_true(self) -> None:
        """Test delete_stream returns True when Redis delete returns >0."""
        mock_client = MagicMock()
        mock_client.delete.return_value = 1

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.delete_stream(event_type="agent_heartbeat") is True
        mock_client.delete.assert_called_once_with("stream:agent_heartbeat")

    def test_delete_stream_not_found_returns_false(self) -> None:
        """Test delete_stream returns False when stream doesn't exist."""
        mock_client = MagicMock()
        mock_client.delete.return_value = 0

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.delete_stream(event_type="nonexistent") is False

    def test_delete_stream_redis_error_returns_false(self) -> None:
        """Test delete_stream returns False on Redis exception."""
        mock_client = MagicMock()
        mock_client.delete.side_effect = ConnectionError("Redis down")

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.delete_stream(event_type="test") is False


class TestEventStreamerTrimStream:
    """Tests for EventStreamer.trim_stream."""

    def test_trim_stream_no_memory_returns_zero(self) -> None:
        """Test trim_stream returns 0 when no memory backend."""
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = None

        assert streamer.trim_stream(event_type="test") == 0

    def test_trim_stream_no_client_returns_zero(self) -> None:
        """Test trim_stream returns 0 when memory has no _client."""
        mock_memory = MagicMock(spec=[])
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.trim_stream(event_type="test") == 0

    def test_trim_stream_client_is_none_returns_zero(self) -> None:
        """Test trim_stream returns 0 when _client is None."""
        mock_memory = MagicMock()
        mock_memory._client = None
        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.trim_stream(event_type="test") == 0

    def test_trim_stream_success_returns_trimmed_count(self) -> None:
        """Test trim_stream returns number of trimmed events."""
        mock_client = MagicMock()
        mock_client.xtrim.return_value = 500

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        result = streamer.trim_stream(event_type="agent_heartbeat", max_length=1000)

        assert result == 500
        mock_client.xtrim.assert_called_once_with(
            "stream:agent_heartbeat",
            maxlen=1000,
            approximate=True,
        )

    def test_trim_stream_default_max_length(self) -> None:
        """Test trim_stream uses default max_length of 1000."""
        mock_client = MagicMock()
        mock_client.xtrim.return_value = 0

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        streamer.trim_stream(event_type="test")

        call_args = mock_client.xtrim.call_args
        assert call_args[1]["maxlen"] == 1000

    def test_trim_stream_redis_error_returns_zero(self) -> None:
        """Test trim_stream returns 0 on Redis exception."""
        mock_client = MagicMock()
        mock_client.xtrim.side_effect = ConnectionError("Redis down")

        mock_memory = MagicMock()
        mock_memory._client = mock_client

        streamer = EventStreamer.__new__(EventStreamer)
        streamer.memory = mock_memory

        assert streamer.trim_stream(event_type="test") == 0


class TestEventStreamerClassConstants:
    """Tests for EventStreamer class-level constants."""

    def test_stream_prefix(self) -> None:
        """Test STREAM_PREFIX constant value."""
        assert EventStreamer.STREAM_PREFIX == "stream:"

    def test_max_stream_length(self) -> None:
        """Test MAX_STREAM_LENGTH constant value."""
        assert EventStreamer.MAX_STREAM_LENGTH == 10000

    def test_default_block_ms(self) -> None:
        """Test DEFAULT_BLOCK_MS constant value."""
        assert EventStreamer.DEFAULT_BLOCK_MS == 5000
