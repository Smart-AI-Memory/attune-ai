"""Branch-coverage tests for agent heartbeat tracking.

Net-new file for the test-quality program (#1569): covers the
UsageTracker memory fallback, the lazy EventStreamer paths, the
stream-publish path in _publish_heartbeat, and the guard/error
branches in get_active_agents / is_agent_alive / get_agent_status /
_retrieve_heartbeat. Complements test_agent_tracking.py.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from attune.telemetry.agent_tracking import AgentHeartbeat, HeartbeatCoordinator


@pytest.fixture
def mock_memory():
    """Memory backend double exposing only _client."""
    memory = Mock(spec=["_client"])
    memory._client = Mock()
    return memory


@pytest.fixture
def coordinator(mock_memory):
    coordinator = HeartbeatCoordinator(memory=mock_memory)
    coordinator.agent_id = "agent-1"
    return coordinator


class TestFromDictLastBeatFallback:
    def test_numeric_last_beat_falls_back_to_now(self):
        heartbeat = AgentHeartbeat.from_dict(
            {
                "agent_id": "agent-1",
                "status": "running",
                "progress": 0.5,
                "current_task": "work",
                "last_beat": 12345,
            }
        )
        assert isinstance(heartbeat.last_beat, datetime)
        assert heartbeat.last_beat.tzinfo is timezone.utc
        assert (datetime.now(timezone.utc) - heartbeat.last_beat).total_seconds() < 60


class TestInitMemoryFallback:
    def test_adopts_usage_tracker_memory(self):
        tracker = Mock(spec=["_memory"])
        with patch("attune.telemetry.UsageTracker") as tracker_cls:
            tracker_cls.get_instance.return_value = tracker
            coordinator = HeartbeatCoordinator()
        assert coordinator.memory is tracker._memory


class TestEventStreamerLifecycle:
    def test_lazy_init_caches_instance(self, mock_memory):
        coordinator = HeartbeatCoordinator(memory=mock_memory, enable_streaming=True)
        streamer = Mock()
        with patch(
            "attune.telemetry.event_streaming.EventStreamer", return_value=streamer
        ) as streamer_cls:
            assert coordinator._get_event_streamer() is streamer
            assert coordinator._get_event_streamer() is streamer
        streamer_cls.assert_called_once_with(memory=mock_memory)

    def test_init_failure_disables_streaming(self, mock_memory):
        coordinator = HeartbeatCoordinator(memory=mock_memory, enable_streaming=True)
        with patch(
            "attune.telemetry.event_streaming.EventStreamer",
            side_effect=RuntimeError("no stream"),
        ):
            assert coordinator._get_event_streamer() is None
        assert coordinator._enable_streaming is False
        assert coordinator._get_event_streamer() is None


class TestPublishHeartbeatBranches:
    def test_guard_without_agent_id_is_noop(self, mock_memory):
        coordinator = HeartbeatCoordinator(memory=mock_memory)
        coordinator._publish_heartbeat(
            status="running", progress=0.1, current_task="x", metadata={}
        )
        mock_memory._client.setex.assert_not_called()

    def test_falsy_client_logs_warning(self, caplog):
        memory = Mock(spec=["_client"])
        memory._client = None
        coordinator = HeartbeatCoordinator(memory=memory)
        coordinator.agent_id = "agent-1"
        with caplog.at_level(logging.WARNING):
            coordinator._publish_heartbeat(
                status="running", progress=0.1, current_task="x", metadata={}
            )
        assert "Cannot publish heartbeat" in caplog.text

    def test_publishes_heartbeat_event_to_stream(self, mock_memory):
        coordinator = HeartbeatCoordinator(memory=mock_memory, enable_streaming=True)
        streamer = Mock()
        with patch("attune.telemetry.event_streaming.EventStreamer", return_value=streamer):
            coordinator.start_heartbeat(agent_id="agent-1", display_name="Agent One")
        kwargs = streamer.publish_event.call_args.kwargs
        assert kwargs["event_type"] == "agent_heartbeat"
        assert kwargs["source"] == "attune"
        assert kwargs["data"]["agent_id"] == "agent-1"
        assert kwargs["data"]["status"] == "starting"
        assert kwargs["data"]["display_name"] == "Agent One"

    def test_stream_publish_failure_still_stores_heartbeat(self, mock_memory):
        coordinator = HeartbeatCoordinator(memory=mock_memory, enable_streaming=True)
        streamer = Mock()
        streamer.publish_event.side_effect = RuntimeError("stream down")
        with patch("attune.telemetry.event_streaming.EventStreamer", return_value=streamer):
            coordinator.start_heartbeat(agent_id="agent-1")
        mock_memory._client.setex.assert_called_once()


class TestGetActiveAgentsBranches:
    def test_no_memory_returns_empty(self):
        coordinator = HeartbeatCoordinator(memory=None)
        assert coordinator.get_active_agents() == []

    def test_falsy_client_returns_empty(self, caplog):
        memory = Mock(spec=["_client"])
        memory._client = None
        coordinator = HeartbeatCoordinator(memory=memory)
        with caplog.at_level(logging.WARNING):
            assert coordinator.get_active_agents() == []
        assert "no Redis access" in caplog.text

    def test_scan_error_returns_empty(self, coordinator, mock_memory):
        mock_memory._client.scan_iter.side_effect = RuntimeError("redis down")
        assert coordinator.get_active_agents() == []


class TestAgentQueriesWithoutMemory:
    def test_is_agent_alive_no_memory_returns_false(self):
        coordinator = HeartbeatCoordinator(memory=None)
        assert coordinator.is_agent_alive("agent-1") is False

    def test_get_agent_status_no_memory_returns_none(self):
        coordinator = HeartbeatCoordinator(memory=None)
        assert coordinator.get_agent_status("agent-1") is None

    def test_get_agent_status_missing_heartbeat_returns_none(self, coordinator, mock_memory):
        mock_memory._client.get.return_value = None
        assert coordinator.get_agent_status("agent-1") is None


class TestRetrieveHeartbeatBranches:
    def test_no_memory_returns_none(self, coordinator):
        coordinator.memory = None
        assert coordinator._retrieve_heartbeat("key") is None

    def test_invalid_json_returns_none(self, coordinator, mock_memory):
        mock_memory._client.get.return_value = b"not json"
        assert coordinator._retrieve_heartbeat("key") is None
