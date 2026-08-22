"""Branch-coverage tests for agent coordination signals.

Net-new file for the test-quality program (#1569): covers the
UsageTracker memory fallback, the lazy EventStreamer paths, the
stream-publish path in signal(), and the guard/error branches in
check_signal / get_pending_signals / clear_signals and the private
retrieve/delete helpers. Complements test_agent_coordination.py.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from attune.telemetry.agent_coordination import CoordinationSignal, CoordinationSignals
from tests.unit.telemetry.conftest import serve_mget_from_get


@pytest.fixture
def mock_memory():
    """Memory backend double exposing only _client."""
    memory = Mock(spec=["_client"])
    memory._client = serve_mget_from_get(Mock())
    return memory


@pytest.fixture
def coordinator(mock_memory):
    return CoordinationSignals(memory=mock_memory, agent_id="test-agent")


class TestFromDictTimestampFallback:
    def test_numeric_timestamp_falls_back_to_now(self):
        signal = CoordinationSignal.from_dict(
            {
                "signal_id": "signal_1",
                "signal_type": "ready",
                "source_agent": "a",
                "timestamp": 12345,
            }
        )
        assert isinstance(signal.timestamp, datetime)
        assert signal.timestamp.tzinfo is timezone.utc
        assert (datetime.now(timezone.utc) - signal.timestamp).total_seconds() < 60


class TestInitMemoryFallback:
    def test_adopts_usage_tracker_memory(self):
        tracker = Mock(spec=["_memory"])
        with patch("attune.telemetry.UsageTracker") as tracker_cls:
            tracker_cls.get_instance.return_value = tracker
            coordinator = CoordinationSignals()
        assert coordinator.memory is tracker._memory


class TestEventStreamerLifecycle:
    def test_disabled_returns_none(self, mock_memory):
        coordinator = CoordinationSignals(memory=mock_memory, enable_streaming=False)
        assert coordinator._get_event_streamer() is None

    def test_lazy_init_caches_instance(self, mock_memory):
        coordinator = CoordinationSignals(memory=mock_memory, enable_streaming=True)
        streamer = Mock()
        with patch(
            "attune.telemetry.event_streaming.EventStreamer", return_value=streamer
        ) as streamer_cls:
            assert coordinator._get_event_streamer() is streamer
            assert coordinator._get_event_streamer() is streamer
        streamer_cls.assert_called_once_with(memory=mock_memory)

    def test_init_failure_disables_streaming(self, mock_memory):
        coordinator = CoordinationSignals(memory=mock_memory, enable_streaming=True)
        with patch(
            "attune.telemetry.event_streaming.EventStreamer",
            side_effect=RuntimeError("no stream"),
        ):
            assert coordinator._get_event_streamer() is None
        assert coordinator._enable_streaming is False
        # Subsequent calls stay disabled without retrying the import.
        assert coordinator._get_event_streamer() is None


class TestSignalStreamPublish:
    def test_signal_publishes_coordination_event(self, mock_memory):
        coordinator = CoordinationSignals(
            memory=mock_memory, agent_id="test-agent", enable_streaming=True
        )
        streamer = Mock()
        with patch("attune.telemetry.event_streaming.EventStreamer", return_value=streamer):
            signal_id = coordinator.signal(signal_type="task_complete")
        assert signal_id.startswith("signal_")
        kwargs = streamer.publish_event.call_args.kwargs
        assert kwargs["event_type"] == "coordination_signal"
        assert kwargs["source"] == "attune"
        assert kwargs["data"]["signal_id"] == signal_id
        assert kwargs["data"]["signal_type"] == "task_complete"

    def test_publish_failure_still_returns_signal_id(self, mock_memory):
        coordinator = CoordinationSignals(
            memory=mock_memory, agent_id="test-agent", enable_streaming=True
        )
        streamer = Mock()
        streamer.publish_event.side_effect = RuntimeError("stream down")
        with patch("attune.telemetry.event_streaming.EventStreamer", return_value=streamer):
            signal_id = coordinator.signal(signal_type="task_complete")
        assert signal_id.startswith("signal_")
        # The signal itself was still stored.
        mock_memory._client.setex.assert_called_once()


class TestCheckSignalBranches:
    def test_memory_without_client_returns_none(self):
        coordinator = CoordinationSignals(memory=Mock(spec=[]), agent_id="test-agent")
        assert coordinator.check_signal(signal_type="ready") is None

    def test_unretrievable_signal_is_skipped(self, coordinator, mock_memory):
        mock_memory._client.scan_iter.return_value = ["empathy:signal:test-agent:ready:signal_1"]
        mock_memory._client.get.return_value = None
        assert coordinator.check_signal(signal_type="ready") is None

    def test_scan_error_returns_none(self, coordinator, mock_memory):
        mock_memory._client.scan_iter.side_effect = RuntimeError("redis down")
        assert coordinator.check_signal(signal_type="ready") is None


class TestGetPendingSignalsBranches:
    def test_no_agent_id_returns_empty(self, mock_memory):
        coordinator = CoordinationSignals(memory=mock_memory, agent_id=None)
        assert coordinator.get_pending_signals() == []

    def test_memory_without_client_returns_empty(self):
        coordinator = CoordinationSignals(memory=Mock(spec=[]), agent_id="test-agent")
        assert coordinator.get_pending_signals() == []

    def test_unretrievable_signal_is_skipped(self, coordinator, mock_memory):
        mock_memory._client.scan_iter.return_value = [b"empathy:signal:test-agent:ready:signal_1"]
        mock_memory._client.get.return_value = None
        assert coordinator.get_pending_signals() == []

    def test_scan_error_returns_empty(self, coordinator, mock_memory):
        mock_memory._client.scan_iter.side_effect = RuntimeError("redis down")
        assert coordinator.get_pending_signals() == []


class TestClearSignalsGuard:
    def test_no_agent_id_returns_zero(self, mock_memory):
        coordinator = CoordinationSignals(memory=mock_memory, agent_id=None)
        assert coordinator.clear_signals() == 0


class TestDeleteSignalBranches:
    def test_no_memory_returns_false(self, coordinator):
        coordinator.memory = None
        assert coordinator._delete_signal("key") is False

    def test_memory_without_client_returns_false(self):
        coordinator = CoordinationSignals(memory=Mock(spec=[]), agent_id="test-agent")
        assert coordinator._delete_signal("key") is False
