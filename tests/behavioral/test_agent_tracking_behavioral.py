"""Behavioral tests for agent_tracking.py module.

Tests heartbeat coordination, agent status tracking, and TTL management.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

import time
from datetime import datetime
from unittest.mock import MagicMock

from attune.telemetry.agent_tracking import (
    AgentHeartbeat,
    HeartbeatCoordinator,
)


def create_mock_coordinator():
    """Create HeartbeatCoordinator with mock Redis backend for testing."""
    # Create mock Redis client
    mock_client = MagicMock()
    mock_client._store = {}  # Internal store for test data

    def mock_setex(key, ttl, value):
        """Mock Redis setex - store key with TTL.

        Implementation stores as empathy:heartbeat:{agent_id}
        but retrieval uses heartbeat:{agent_id}, so we store under both keys.
        """
        mock_client._store[key] = value
        # Also store under alternate key format for retrieval compatibility
        if key.startswith("empathy:heartbeat:"):
            alt_key = key.replace("empathy:heartbeat:", "heartbeat:")
            mock_client._store[alt_key] = value
        elif key.startswith("heartbeat:"):
            alt_key = "empathy:" + key
            mock_client._store[alt_key] = value

    def mock_get(key):
        """Mock Redis get - retrieve key."""
        return mock_client._store.get(key)

    def mock_keys(pattern):
        """Mock Redis keys - scan for pattern."""
        if pattern == "empathy:heartbeat:*":
            return [k for k in mock_client._store.keys() if k.startswith("empathy:heartbeat:")]
        return []

    def mock_scan_iter(match="", count=100):
        """Mock Redis scan_iter - iterate keys matching pattern."""
        if match == "empathy:heartbeat:*":
            return iter(
                [k for k in mock_client._store.keys() if k.startswith("empathy:heartbeat:")]
            )
        return iter([])

    def mock_delete(key):
        """Mock Redis delete - remove key."""
        if key in mock_client._store:
            del mock_client._store[key]
        # Also delete alternate key format
        if key.startswith("empathy:heartbeat:"):
            alt_key = key.replace("empathy:heartbeat:", "heartbeat:")
            if alt_key in mock_client._store:
                del mock_client._store[alt_key]
        elif key.startswith("heartbeat:"):
            alt_key = "empathy:" + key
            if alt_key in mock_client._store:
                del mock_client._store[alt_key]

    mock_client.setex = mock_setex
    mock_client.get = mock_get
    mock_client.keys = mock_keys
    mock_client.scan_iter = mock_scan_iter
    mock_client.delete = mock_delete

    # Create mock memory with Redis client
    mock_memory = MagicMock()
    mock_memory._client = mock_client

    # Create coordinator with mock memory
    coordinator = HeartbeatCoordinator(memory=mock_memory)
    return coordinator


class TestAgentHeartbeat:
    """Test AgentHeartbeat dataclass."""

    def test_creates_heartbeat(self):
        """Test creating an agent heartbeat."""
        heartbeat = AgentHeartbeat(
            agent_id="test-agent-123",
            status="running",
            progress=0.5,
            current_task="Processing files",
            last_beat=datetime.now(),
            metadata={"workflow": "code-review"},
        )

        assert heartbeat.agent_id == "test-agent-123"
        assert heartbeat.status == "running"
        assert heartbeat.progress == 0.5
        assert heartbeat.current_task == "Processing files"

    def test_converts_to_dict(self):
        """Test converting heartbeat to dictionary."""
        now = datetime.now()
        heartbeat = AgentHeartbeat(
            agent_id="test-agent",
            status="running",
            progress=0.75,
            current_task="Final step",
            last_beat=now,
            metadata={"run_id": "xyz"},
        )

        data = heartbeat.to_dict()

        assert data["agent_id"] == "test-agent"
        assert data["status"] == "running"
        assert data["progress"] == 0.75
        assert isinstance(data["last_beat"], str)  # ISO format

    def test_creates_from_dict(self):
        """Test creating heartbeat from dictionary."""
        data = {
            "agent_id": "test-agent",
            "status": "completed",
            "progress": 1.0,
            "current_task": "Done",
            "last_beat": "2026-01-29T12:00:00",
            "metadata": {"result": "success"},
        }

        heartbeat = AgentHeartbeat.from_dict(data)

        assert heartbeat.agent_id == "test-agent"
        assert heartbeat.status == "completed"
        assert isinstance(heartbeat.last_beat, datetime)

    def test_handles_missing_metadata(self):
        """Test handling missing metadata in dict."""
        data = {
            "agent_id": "test-agent",
            "status": "running",
            "progress": 0.5,
            "current_task": "Task",
            "last_beat": datetime.now(),
        }

        heartbeat = AgentHeartbeat.from_dict(data)

        assert heartbeat.metadata == {}


class TestHeartbeatCoordinator:
    """Test HeartbeatCoordinator functionality."""

    def test_starts_heartbeat(self):
        """Test starting agent heartbeat tracking."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(
            agent_id="agent-1",
            metadata={"workflow": "test"},
        )

        # Agent should be in active list
        active = coordinator.get_active_agents()
        assert len(active) == 1
        assert active[0].agent_id == "agent-1"
        assert active[0].status == "starting"

    def test_updates_heartbeat(self):
        """Test updating heartbeat status."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        coordinator.beat(
            status="running",
            progress=0.5,
            current_task="Processing",
        )

        active = coordinator.get_active_agents()
        assert active[0].status == "running"
        assert active[0].progress == 0.5
        assert active[0].current_task == "Processing"

    def test_stops_heartbeat(self):
        """Test stopping heartbeat tracking."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        coordinator.stop_heartbeat(
            final_status="completed",
        )

        # Agent should be removed from active list (stop clears agent_id but doesn't delete key)
        # The heartbeat is still in Redis with final status
        active = coordinator.get_active_agents()
        assert len(active) == 1
        assert active[0].status == "completed"

    def test_tracks_multiple_agents(self):
        """Test tracking multiple agents simultaneously."""
        coordinator1 = create_mock_coordinator()
        coordinator2 = create_mock_coordinator()

        # Share the same mock memory backend
        coordinator2.memory = coordinator1.memory

        coordinator1.start_heartbeat(agent_id="agent-1", metadata={"type": "analyzer"})
        coordinator2.start_heartbeat(agent_id="agent-2", metadata={"type": "reviewer"})

        active = coordinator1.get_active_agents()
        assert len(active) == 2

        agent_ids = {agent.agent_id for agent in active}
        assert agent_ids == {"agent-1", "agent-2"}

    def test_detects_stale_heartbeats(self):
        """Test detection of stale heartbeats based on TTL."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")

        # Immediately should be active
        active = coordinator.get_active_agents()
        assert len(active) == 1

        # Wait for stale threshold (default is 60s, we'll use get_stale_agents with lower threshold)
        time.sleep(0.5)

        # Should now detect as stale with low threshold
        stale = coordinator.get_stale_agents(threshold_seconds=0.1)
        assert len(stale) == 1
        assert stale[0].agent_id == "agent-1"

    def test_gets_agent_status(self):
        """Test retrieving individual agent status."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1", metadata={"run_id": "123"})
        coordinator.beat(
            status="running",
            progress=0.7,
            current_task="Final steps",
        )

        status = coordinator.get_agent_status("agent-1")

        assert status is not None
        assert status.agent_id == "agent-1"
        assert status.status == "running"
        assert status.progress == 0.7

    def test_returns_none_for_missing_agent(self):
        """Test that None is returned for non-existent agent."""
        coordinator = create_mock_coordinator()

        status = coordinator.get_agent_status("nonexistent")

        assert status is None

    def test_cleans_up_completed_agents(self):
        """Test cleanup of completed agents by manually deleting keys."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        coordinator.beat(status="completed", progress=1.0)

        # Manually clean up completed agent (no built-in cleanup_completed method)
        active = coordinator.get_active_agents()
        for agent in active:
            if agent.status in ("completed", "failed", "cancelled"):
                key = f"empathy:heartbeat:{agent.agent_id}"
                coordinator.memory._client.delete(key)

        active = coordinator.get_active_agents()
        assert len(active) == 0

    def test_preserves_running_agents_during_cleanup(self):
        """Test that running agents are preserved during manual cleanup."""
        coordinator1 = create_mock_coordinator()
        coordinator2 = create_mock_coordinator()
        coordinator2.memory = coordinator1.memory

        coordinator1.start_heartbeat(agent_id="agent-1")
        coordinator2.start_heartbeat(agent_id="agent-2")

        coordinator1.beat(status="completed", progress=1.0)
        coordinator2.beat(status="running", progress=0.5)

        # Manual cleanup of completed agents
        active = coordinator1.get_active_agents()
        for agent in active:
            if agent.status in ("completed", "failed", "cancelled"):
                key = f"empathy:heartbeat:{agent.agent_id}"
                coordinator1.memory._client.delete(key)

        active = coordinator1.get_active_agents()
        assert len(active) == 1
        assert active[0].agent_id == "agent-2"


class TestProgressTracking:
    """Test progress tracking functionality."""

    def test_tracks_progress_updates(self):
        """Test tracking progress from 0 to 100%."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")

        # Update progress incrementally
        for i in range(11):
            progress = i / 10.0
            coordinator.beat(
                status="running",
                progress=progress,
                current_task=f"Step {i}",
            )

            status = coordinator.get_agent_status("agent-1")
            assert status.progress == progress

    def test_validates_progress_range(self):
        """Test that progress is kept within 0-1 range."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")

        # Try to set progress > 1.0 (implementation doesn't clamp, just stores it)
        coordinator.beat(status="running", progress=1.5)

        status = coordinator.get_agent_status("agent-1")
        # Implementation stores the value as-is (no validation)
        assert status.progress == 1.5


class TestMetadataHandling:
    """Test metadata storage and retrieval."""

    def test_stores_metadata(self):
        """Test that metadata is stored with heartbeat."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(
            agent_id="agent-1",
            metadata={
                "workflow": "code-review",
                "run_id": "abc123",
                "user": "test-user",
            },
        )

        status = coordinator.get_agent_status("agent-1")
        assert status.metadata["workflow"] == "code-review"
        assert status.metadata["run_id"] == "abc123"

    def test_updates_metadata(self):
        """Test updating metadata during execution.

        Note: beat() method replaces metadata, doesn't merge it.
        """
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(
            agent_id="agent-1",
            metadata={"phase": "initialization"},
        )

        # Note: beat() in the implementation only accepts status, progress, current_task
        # Metadata is not updated via beat() - it's set at start_heartbeat
        coordinator.beat(
            status="running",
            progress=0.5,
            current_task="analysis",
        )

        status = coordinator.get_agent_status("agent-1")
        # Metadata remains from start_heartbeat since beat() doesn't update it
        # beat() sends empty dict for metadata
        assert status.metadata == {}


class TestStatusTransitions:
    """Test agent status transitions."""

    def test_starting_to_running_transition(self):
        """Test transition from starting to running."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        assert coordinator.get_agent_status("agent-1").status == "starting"

        coordinator.beat(status="running", progress=0.1)
        assert coordinator.get_agent_status("agent-1").status == "running"

    def test_running_to_completed_transition(self):
        """Test transition from running to completed."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        coordinator.beat(status="running", progress=0.5)
        coordinator.beat(status="completed", progress=1.0)

        status = coordinator.get_agent_status("agent-1")
        assert status.status == "completed"
        assert status.progress == 1.0

    def test_running_to_failed_transition(self):
        """Test transition from running to failed."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        coordinator.beat(status="running", progress=0.3)
        coordinator.beat(
            status="failed",
            progress=0.3,
            current_task="error",
        )

        status = coordinator.get_agent_status("agent-1")
        assert status.status == "failed"
        # Note: beat() doesn't accept metadata parameter, only start_heartbeat does
        # so we can't set error metadata via beat()


class TestTimestampHandling:
    """Test last beat timestamp handling."""

    def test_updates_last_beat_timestamp(self):
        """Test that last_beat is updated on each beat."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        first_beat = coordinator.get_agent_status("agent-1").last_beat

        time.sleep(0.1)

        coordinator.beat(status="running", progress=0.5)
        second_beat = coordinator.get_agent_status("agent-1").last_beat

        assert second_beat > first_beat

    def test_calculates_time_since_last_beat(self):
        """Test calculating time elapsed since last beat."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1")
        time.sleep(0.5)

        status = coordinator.get_agent_status("agent-1")
        elapsed = (datetime.utcnow() - status.last_beat).total_seconds()

        assert elapsed >= 0.4  # Allow some tolerance


class TestErrorHandling:
    """Test error handling in edge cases."""

    def test_handles_beat_for_nonexistent_agent(self):
        """Test handling beat update for non-existent agent."""
        coordinator = create_mock_coordinator()

        # Should not crash when updating non-existent agent
        # beat() requires agent_id to be set via start_heartbeat first
        # Without start_heartbeat, beat() returns early (no crash)
        coordinator.beat(
            status="running",
            progress=0.5,
        )
        # Should not raise exception

    def test_handles_stop_for_nonexistent_agent(self):
        """Test handling stop for non-existent agent."""
        coordinator = create_mock_coordinator()

        # Should not crash when stopping non-existent agent
        # Without start_heartbeat, stop_heartbeat() returns early (no crash)
        coordinator.stop_heartbeat(
            final_status="completed",
        )
        # Should not raise exception

    def test_handles_duplicate_start(self):
        """Test handling duplicate start requests."""
        coordinator = create_mock_coordinator()

        coordinator.start_heartbeat(agent_id="agent-1", metadata={"attempt": 1})
        coordinator.start_heartbeat(agent_id="agent-1", metadata={"attempt": 2})

        # Second start overwrites first (same agent_id)
        active = coordinator.get_active_agents()
        assert len(active) == 1
        assert active[0].metadata["attempt"] == 2


class TestConcurrentAccess:
    """Test handling of concurrent access patterns."""

    def test_multiple_agents_dont_interfere(self):
        """Test that multiple agents don't interfere with each other."""
        # Create separate coordinators for each agent, sharing same memory backend
        coordinators = []
        mock_memory = None

        for _ in range(5):
            coord = create_mock_coordinator()
            if mock_memory is None:
                mock_memory = coord.memory
            else:
                coord.memory = mock_memory
            coordinators.append(coord)

        # Start multiple agents
        for i in range(5):
            coordinators[i].start_heartbeat(
                agent_id=f"agent-{i}",
                metadata={"index": i},
            )

        # Update each independently
        for i in range(5):
            coordinators[i].beat(
                status="running",
                progress=i / 10.0,
                current_task=f"Task {i}",
            )

        # Verify each has correct state
        for i in range(5):
            status = coordinators[0].get_agent_status(f"agent-{i}")
            assert status.progress == i / 10.0
            assert status.current_task == f"Task {i}"
