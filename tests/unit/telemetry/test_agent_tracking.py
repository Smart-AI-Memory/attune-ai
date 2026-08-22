"""Unit tests for agent heartbeat tracking.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from attune.telemetry.agent_tracking import AgentHeartbeat, HeartbeatCoordinator
from tests.unit.telemetry.conftest import serve_mget_from_get


class TestAgentHeartbeat:
    """Test AgentHeartbeat dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        heartbeat = AgentHeartbeat(
            agent_id="test-agent",
            status="running",
            progress=0.5,
            current_task="Testing",
            last_beat=datetime(2026, 1, 27, 12, 0, 0),
            metadata={"key": "value"},
        )

        result = heartbeat.to_dict()

        assert result["agent_id"] == "test-agent"
        assert result["status"] == "running"
        assert result["progress"] == 0.5
        assert result["current_task"] == "Testing"
        assert result["last_beat"] == "2026-01-27T12:00:00"
        assert result["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "agent_id": "test-agent",
            "status": "running",
            "progress": 0.5,
            "current_task": "Testing",
            "last_beat": "2026-01-27T12:00:00",
            "metadata": {"key": "value"},
        }

        heartbeat = AgentHeartbeat.from_dict(data)

        assert heartbeat.agent_id == "test-agent"
        assert heartbeat.status == "running"
        assert heartbeat.progress == 0.5
        assert heartbeat.current_task == "Testing"
        assert isinstance(heartbeat.last_beat, datetime)
        assert heartbeat.metadata == {"key": "value"}

    def test_from_dict_with_datetime(self):
        """Test from_dict with datetime object."""
        now = datetime.now(timezone.utc)
        data = {
            "agent_id": "test",
            "status": "running",
            "progress": 0.0,
            "current_task": "test",
            "last_beat": now,
        }

        heartbeat = AgentHeartbeat.from_dict(data)
        assert heartbeat.last_beat == now


class TestHeartbeatCoordinatorNoMemory:
    """Test HeartbeatCoordinator without Redis."""

    def test_init_no_memory(self):
        """Test initialization without memory backend."""
        # Patch UsageTracker at the source (where it's imported from)
        with patch("attune.telemetry.UsageTracker") as mock_tracker:
            mock_tracker.get_instance.side_effect = ImportError()

            coordinator = HeartbeatCoordinator()

            assert coordinator.memory is None
            assert coordinator.agent_id is None

    def test_start_heartbeat_no_memory(self):
        """Test start_heartbeat without memory backend (no-op)."""
        coordinator = HeartbeatCoordinator(memory=None)

        # Should not raise error, but also doesn't set agent_id (early return)
        coordinator.start_heartbeat("test-agent", metadata={"test": "data"})

        # agent_id remains None because early return when no memory
        assert coordinator.agent_id is None

    def test_beat_no_memory(self):
        """Test beat without memory backend (no-op)."""
        coordinator = HeartbeatCoordinator(memory=None)

        # Should not raise error
        coordinator.beat(status="running", progress=0.5, current_task="test")

    def test_stop_heartbeat_no_memory(self):
        """Test stop_heartbeat without memory backend (no-op)."""
        coordinator = HeartbeatCoordinator(memory=None)
        coordinator.agent_id = "test"

        # Should not raise error, but also doesn't clear agent_id (early return)
        coordinator.stop_heartbeat(final_status="completed")

        # agent_id remains "test" because early return when no memory
        assert coordinator.agent_id == "test"


class TestHeartbeatCoordinatorWithMemory:
    """Test HeartbeatCoordinator with mocked memory."""

    @pytest.fixture
    def mock_memory(self):
        """Create mock memory backend."""
        # Use spec to prevent Mock from having stash attribute
        # This makes hasattr(memory, "stash") return False
        memory = Mock(spec=["_client"])
        memory._client = serve_mget_from_get(Mock())
        return memory

    @pytest.fixture
    def coordinator(self, mock_memory):
        """Create coordinator with mock memory."""
        return HeartbeatCoordinator(memory=mock_memory)

    def test_start_heartbeat(self, coordinator, mock_memory):
        """Test starting heartbeat."""
        coordinator.start_heartbeat("test-agent", metadata={"workflow": "test"})

        assert coordinator.agent_id == "test-agent"

        # Verify stash was called
        assert mock_memory._client.setex.called

    def test_beat_updates_heartbeat(self, coordinator, mock_memory):
        """Test beat updates heartbeat."""
        coordinator.agent_id = "test-agent"

        coordinator.beat(status="running", progress=0.75, current_task="Processing")

        # Verify Redis setex was called
        assert mock_memory._client.setex.called
        call_args = mock_memory._client.setex.call_args
        key, ttl, data = call_args[0]

        assert key == "empathy:heartbeat:test-agent"
        assert ttl == coordinator.HEARTBEAT_TTL

    def test_stop_heartbeat(self, coordinator, mock_memory):
        """Test stopping heartbeat."""
        coordinator.agent_id = "test-agent"

        coordinator.stop_heartbeat(final_status="completed")

        # Verify final heartbeat was sent
        assert mock_memory._client.setex.called

        # Verify agent_id cleared
        assert coordinator.agent_id is None

    def test_get_active_agents(self, coordinator, mock_memory):
        """Test getting active agents."""
        # Mock Redis keys response
        mock_memory._client.scan_iter.return_value = [b"heartbeat:agent-1", b"heartbeat:agent-2"]

        # Mock Redis get responses
        import json

        heartbeat1 = {
            "agent_id": "agent-1",
            "status": "running",
            "progress": 0.5,
            "current_task": "task1",
            "last_beat": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }
        heartbeat2 = {
            "agent_id": "agent-2",
            "status": "starting",
            "progress": 0.0,
            "current_task": "init",
            "last_beat": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }

        mock_memory._client.get.side_effect = [
            json.dumps(heartbeat1).encode(),
            json.dumps(heartbeat2).encode(),
        ]

        # Get active agents
        active = coordinator.get_active_agents()

        assert len(active) == 2
        assert active[0].agent_id == "agent-1"
        assert active[1].agent_id == "agent-2"

    def test_is_agent_alive(self, coordinator, mock_memory):
        """Test checking if agent is alive."""
        import json

        heartbeat = {
            "agent_id": "test-agent",
            "status": "running",
            "progress": 0.5,
            "current_task": "test",
            "last_beat": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }

        mock_memory._client.get.return_value = json.dumps(heartbeat).encode()

        assert coordinator.is_agent_alive("test-agent") is True

        # Test non-existent agent
        mock_memory._client.get.return_value = None
        assert coordinator.is_agent_alive("missing-agent") is False

    def test_get_agent_status(self, coordinator, mock_memory):
        """Test getting agent status."""
        import json

        heartbeat = {
            "agent_id": "test-agent",
            "status": "running",
            "progress": 0.75,
            "current_task": "processing",
            "last_beat": datetime.now(timezone.utc).isoformat(),
            "metadata": {"key": "value"},
        }

        mock_memory._client.get.return_value = json.dumps(heartbeat).encode()

        status = coordinator.get_agent_status("test-agent")

        assert status is not None
        assert status.agent_id == "test-agent"
        assert status.progress == 0.75
        assert status.current_task == "processing"

    def test_get_stale_agents(self, coordinator, mock_memory):
        """Test detecting stale agents."""
        # Create one fresh and one stale heartbeat
        now = datetime.now(timezone.utc)
        fresh_time = now - timedelta(seconds=10)
        stale_time = now - timedelta(seconds=120)

        mock_memory._client.scan_iter.return_value = [
            b"heartbeat:agent-fresh",
            b"heartbeat:agent-stale",
        ]

        import json

        heartbeat_fresh = {
            "agent_id": "agent-fresh",
            "status": "running",
            "progress": 0.5,
            "current_task": "working",
            "last_beat": fresh_time.isoformat(),
            "metadata": {},
        }

        heartbeat_stale = {
            "agent_id": "agent-stale",
            "status": "running",  # Still running but stale
            "progress": 0.3,
            "current_task": "stuck",
            "last_beat": stale_time.isoformat(),
            "metadata": {},
        }

        mock_memory._client.get.side_effect = [
            json.dumps(heartbeat_fresh).encode(),
            json.dumps(heartbeat_stale).encode(),
        ]

        # Get stale agents (threshold 60s)
        stale = coordinator.get_stale_agents(threshold_seconds=60.0)

        assert len(stale) == 1
        assert stale[0].agent_id == "agent-stale"

    def test_beat_no_agent_id(self, coordinator):
        """Test beat without agent_id set (no-op)."""
        coordinator.agent_id = None

        # Should not raise error
        coordinator.beat(status="running", progress=0.5, current_task="test")

    def test_stop_heartbeat_no_agent_id(self, coordinator):
        """Test stop_heartbeat without agent_id (no-op)."""
        coordinator.agent_id = None

        # Should not raise error
        coordinator.stop_heartbeat()


class TestHeartbeatCoordinatorIntegration:
    """Integration tests requiring actual Redis or comprehensive mocking."""

    @pytest.fixture
    def mock_memory_with_stash(self):
        """Mock memory with stash method (UnifiedMemory style)."""
        memory = Mock()
        memory.stash = Mock()
        memory.retrieve = Mock()
        return memory

    def test_client_method_support(self, mock_memory_with_stash):
        """Test coordinator works with _client method."""
        # Add _client to the mock
        mock_memory_with_stash._client = Mock()
        coordinator = HeartbeatCoordinator(memory=mock_memory_with_stash)

        coordinator.start_heartbeat("test-agent", metadata={})

        # Verify setex was called
        assert mock_memory_with_stash._client.setex.called
        call_args = mock_memory_with_stash._client.setex.call_args
        key, ttl, data = call_args[0]

        assert key == "empathy:heartbeat:test-agent"
        assert ttl == coordinator.HEARTBEAT_TTL

    def test_error_handling_in_publish(self, mock_memory_with_stash):
        """Test error handling when publish fails."""
        mock_memory_with_stash._client = Mock()
        mock_memory_with_stash._client.setex.side_effect = Exception("Redis error")

        coordinator = HeartbeatCoordinator(memory=mock_memory_with_stash)

        # Should not raise, just log warning
        coordinator.start_heartbeat("test-agent", metadata={})

    def test_retrieve_heartbeat_with_client_method(self, mock_memory_with_stash):
        """Test _retrieve_heartbeat with _client.get method."""
        import json

        heartbeat_data = {
            "agent_id": "test",
            "status": "running",
            "progress": 0.5,
            "current_task": "test",
            "last_beat": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
        }

        mock_memory_with_stash._client = Mock()
        mock_memory_with_stash._client.get.return_value = json.dumps(heartbeat_data).encode()

        coordinator = HeartbeatCoordinator(memory=mock_memory_with_stash)
        result = coordinator._retrieve_heartbeat("heartbeat:test")

        assert result == heartbeat_data
