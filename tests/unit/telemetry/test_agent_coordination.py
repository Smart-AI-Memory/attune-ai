"""Unit tests for agent coordination signals.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from attune.memory.types import AccessTier, AgentCredentials
from attune.telemetry.agent_coordination import CoordinationSignal, CoordinationSignals
from tests.unit.telemetry.conftest import serve_mget_from_get


class TestCoordinationSignal:
    """Test CoordinationSignal dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        signal = CoordinationSignal(
            signal_id="sig123",
            signal_type="task_complete",
            source_agent="agent-a",
            target_agent="agent-b",
            payload={"result": "success"},
            timestamp=datetime(2026, 1, 27, 12, 0, 0),
            ttl_seconds=60,
        )

        result = signal.to_dict()

        assert result["signal_id"] == "sig123"
        assert result["signal_type"] == "task_complete"
        assert result["source_agent"] == "agent-a"
        assert result["target_agent"] == "agent-b"
        assert result["payload"] == {"result": "success"}
        assert result["timestamp"] == "2026-01-27T12:00:00"
        assert result["ttl_seconds"] == 60

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "signal_id": "sig123",
            "signal_type": "task_complete",
            "source_agent": "agent-a",
            "target_agent": "agent-b",
            "payload": {"result": "success"},
            "timestamp": "2026-01-27T12:00:00",
            "ttl_seconds": 60,
        }

        signal = CoordinationSignal.from_dict(data)

        assert signal.signal_id == "sig123"
        assert signal.signal_type == "task_complete"
        assert signal.source_agent == "agent-a"
        assert signal.target_agent == "agent-b"
        assert signal.payload == {"result": "success"}
        assert isinstance(signal.timestamp, datetime)
        assert signal.ttl_seconds == 60

    def test_from_dict_broadcast(self):
        """Test from_dict with broadcast signal (no target)."""
        data = {
            "signal_id": "sig123",
            "signal_type": "abort",
            "source_agent": "orchestrator",
            "target_agent": None,  # Broadcast
            "payload": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        signal = CoordinationSignal.from_dict(data)

        assert signal.target_agent is None


class TestCoordinationSignalsNoMemory:
    """Test CoordinationSignals without Redis."""

    def test_init_no_memory(self):
        """Test initialization without memory backend."""
        # Patch UsageTracker at the source (where it's imported from)
        with patch("attune.telemetry.UsageTracker") as mock_tracker:
            mock_tracker.get_instance.side_effect = ImportError()

            coordinator = CoordinationSignals()

            assert coordinator.memory is None

    def test_signal_no_memory(self):
        """Test signal without memory backend (no-op)."""
        coordinator = CoordinationSignals(memory=None, agent_id="test")

        # Should not raise error, returns empty string
        signal_id = coordinator.signal(
            signal_type="test",
            source_agent="test",
            target_agent="target",
            payload={},
        )

        assert signal_id == ""

    def test_wait_for_signal_no_memory(self):
        """Test wait_for_signal without memory (returns None)."""
        coordinator = CoordinationSignals(memory=None, agent_id="test")

        result = coordinator.wait_for_signal(signal_type="test", timeout=0.1)

        assert result is None


class TestCoordinationSignalsWithMemory:
    """Test CoordinationSignals with mocked memory."""

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
        return CoordinationSignals(memory=mock_memory, agent_id="test-agent")

    def test_signal_targeted(self, coordinator, mock_memory):
        """Test sending targeted signal."""
        signal_id = coordinator.signal(
            signal_type="task_complete",
            source_agent="agent-a",
            target_agent="agent-b",
            payload={"result": "success"},
            ttl_seconds=120,
        )

        assert signal_id.startswith("signal_")

        # Verify Redis setex was called
        assert mock_memory._client.setex.called
        call_args = mock_memory._client.setex.call_args
        key, ttl, data = call_args[0]

        assert "signal:agent-b:task_complete:" in key
        assert ttl == 120

    def test_signal_uses_default_source(self, coordinator, mock_memory):
        """Test signal uses coordinator's agent_id as default source."""
        coordinator.signal(
            signal_type="ready",
            target_agent="orchestrator",
            payload={},
        )

        # Verify source was set to coordinator's agent_id
        call_args = mock_memory._client.setex.call_args
        import json

        data = json.loads(call_args[0][2])
        assert data["source_agent"] == "test-agent"

    def test_broadcast(self, coordinator, mock_memory):
        """Test broadcasting signal."""
        signal_id = coordinator.broadcast(
            signal_type="abort",
            source_agent="orchestrator",
            payload={"reason": "cancelled"},
        )

        assert signal_id.startswith("signal_")

        # Verify broadcast key format (target = *)
        call_args = mock_memory._client.setex.call_args
        key = call_args[0][0]

        assert "signal:*:abort:" in key

    def test_check_signal(self, coordinator, mock_memory):
        """Test checking for signal."""
        import json

        # Mock Redis keys and get
        mock_memory._client.scan_iter.return_value = [b"signal:test-agent:task_complete:sig123"]

        signal_data = {
            "signal_id": "sig123",
            "signal_type": "task_complete",
            "source_agent": "producer",
            "target_agent": "test-agent",
            "payload": {"data": "value"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }

        mock_memory._client.get.return_value = json.dumps(signal_data).encode()

        # Check for signal
        signal = coordinator.check_signal(signal_type="task_complete", consume=False)

        assert signal is not None
        assert signal.signal_id == "sig123"
        assert signal.source_agent == "producer"
        assert signal.payload == {"data": "value"}

        # Verify delete not called (consume=False)
        assert not mock_memory._client.delete.called

    def test_check_signal_with_consume(self, coordinator, mock_memory):
        """Test checking and consuming signal."""
        import json

        mock_memory._client.scan_iter.return_value = [b"signal:test-agent:ready:sig456"]

        signal_data = {
            "signal_id": "sig456",
            "signal_type": "ready",
            "source_agent": "worker",
            "target_agent": "test-agent",
            "payload": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }

        mock_memory._client.get.return_value = json.dumps(signal_data).encode()
        mock_memory._client.delete.return_value = 1

        # Check and consume
        signal = coordinator.check_signal(signal_type="ready", consume=True)

        assert signal is not None

        # Verify delete was called
        assert mock_memory._client.delete.called

    def test_check_signal_with_source_filter(self, coordinator, mock_memory):
        """Test checking signal with source filter."""
        import json

        mock_memory._client.scan_iter.return_value = [b"signal:test-agent:checkpoint:sig789"]

        signal_data = {
            "signal_id": "sig789",
            "signal_type": "checkpoint",
            "source_agent": "other-agent",
            "target_agent": "test-agent",
            "payload": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }

        mock_memory._client.get.return_value = json.dumps(signal_data).encode()

        # Check with source filter (should not match)
        signal = coordinator.check_signal(signal_type="checkpoint", source_agent="expected-agent")

        assert signal is None

        # Check with correct source
        signal = coordinator.check_signal(signal_type="checkpoint", source_agent="other-agent")

        assert signal is not None

    def test_check_signal_broadcast(self, coordinator, mock_memory):
        """Test checking broadcast signal."""
        import json

        # Mock both targeted and broadcast keys
        mock_memory._client.scan_iter.return_value = [b"signal:*:abort:sig_broadcast"]

        signal_data = {
            "signal_id": "sig_broadcast",
            "signal_type": "abort",
            "source_agent": "orchestrator",
            "target_agent": None,  # Broadcast
            "payload": {"reason": "test"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl_seconds": 60,
        }

        mock_memory._client.get.return_value = json.dumps(signal_data).encode()

        # Check for broadcast
        signal = coordinator.check_signal(signal_type="abort")

        assert signal is not None
        assert signal.target_agent is None

    def test_get_pending_signals(self, coordinator, mock_memory):
        """Test getting all pending signals."""
        import json

        mock_memory._client.scan_iter.side_effect = [
            [b"signal:test-agent:task1:sig1", b"signal:test-agent:task2:sig2"],
            [b"signal:*:broadcast:sig3"],
        ]

        signals_data = [
            {
                "signal_id": "sig1",
                "signal_type": "task1",
                "source_agent": "a",
                "target_agent": "test-agent",
                "payload": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ttl_seconds": 60,
            },
            {
                "signal_id": "sig2",
                "signal_type": "task2",
                "source_agent": "b",
                "target_agent": "test-agent",
                "payload": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ttl_seconds": 60,
            },
            {
                "signal_id": "sig3",
                "signal_type": "broadcast",
                "source_agent": "orchestrator",
                "target_agent": None,
                "payload": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "ttl_seconds": 60,
            },
        ]

        mock_memory._client.get.side_effect = [json.dumps(s).encode() for s in signals_data]

        # Get all pending
        signals = coordinator.get_pending_signals()

        assert len(signals) == 3

    def test_get_pending_signals_filtered(self, coordinator, mock_memory):
        """Test getting pending signals filtered by type."""
        import json

        mock_memory._client.scan_iter.side_effect = [
            [b"signal:test-agent:checkpoint:sig1", b"signal:test-agent:ready:sig2"],
            [],
        ]

        signals_data = [
            {
                "signal_id": "sig1",
                "signal_type": "checkpoint",
                "source_agent": "a",
                "target_agent": "test-agent",
                "payload": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "signal_id": "sig2",
                "signal_type": "ready",
                "source_agent": "b",
                "target_agent": "test-agent",
                "payload": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]

        mock_memory._client.get.side_effect = [json.dumps(s).encode() for s in signals_data]

        # Get filtered signals
        signals = coordinator.get_pending_signals(signal_type="checkpoint")

        assert len(signals) == 1
        assert signals[0].signal_type == "checkpoint"

    def test_clear_signals(self, coordinator, mock_memory):
        """Test clearing signals."""
        import json

        mock_memory._client.scan_iter.side_effect = [[b"signal:test-agent:test:sig1"], []]

        signal_data = {
            "signal_id": "sig1",
            "signal_type": "test",
            "source_agent": "a",
            "target_agent": "test-agent",
            "payload": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        mock_memory._client.get.return_value = json.dumps(signal_data).encode()
        mock_memory._client.delete.return_value = 1

        # Clear signals
        count = coordinator.clear_signals()

        assert count == 1
        assert mock_memory._client.delete.called

    def test_wait_for_signal_timeout(self, coordinator, mock_memory):
        """Test wait_for_signal with timeout.

        The clock is faked so the timeout logic is exercised deterministically:
        ``time.sleep`` advances a virtual clock instead of blocking, which
        removes the wall-clock dependence that flaked on slow Windows runners
        (CI run 33967508474 measured 1.08s against a ``< 1.0`` bound).
        """
        mock_memory._client.scan_iter.return_value = []

        clock = {"now": 100.0}
        sleeps: list[float] = []

        def fake_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            clock["now"] += seconds

        with patch("attune.telemetry.agent_coordination.time") as fake_time:
            fake_time.time.side_effect = lambda: clock["now"]
            fake_time.sleep.side_effect = fake_sleep
            # 0.125 is binary-exact, so four sleeps sum to exactly the timeout
            # (0.1 accumulates to 0.49999..., which would cost a spurious poll).
            result = coordinator.wait_for_signal(
                signal_type="test", timeout=0.5, poll_interval=0.125
            )

        duration = clock["now"] - 100.0
        assert result is None
        # Waited the full timeout in poll_interval steps ...
        assert duration >= 0.5
        assert sleeps == [0.125] * 4
        # ... and returned as soon as the timeout was reached, not a poll later.
        assert duration < 0.5 + 0.125

    def test_wait_for_signal_receives_signal(self, coordinator, mock_memory):
        """Test wait_for_signal receives signal."""
        import json

        # First check: no signal
        # Second check: signal arrives
        mock_memory._client.scan_iter.side_effect = [[], [b"signal:test-agent:ready:sig1"]]

        signal_data = {
            "signal_id": "sig1",
            "signal_type": "ready",
            "source_agent": "producer",
            "target_agent": "test-agent",
            "payload": {"data": "value"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        mock_memory._client.get.return_value = json.dumps(signal_data).encode()
        mock_memory._client.delete.return_value = 1

        # Wait for signal
        signal = coordinator.wait_for_signal(signal_type="ready", timeout=2.0, poll_interval=0.1)

        assert signal is not None
        assert signal.signal_id == "sig1"

    def test_signal_error_handling(self, coordinator, mock_memory):
        """Test error handling when signal fails."""
        mock_memory._client.setex.side_effect = Exception("Redis error")

        # Should not raise, just log error
        coordinator.signal(signal_type="test", payload={})

        # Should return empty signal_id on error
        # (The current implementation doesn't return empty on error, but logs it)

    def test_check_signal_no_agent_id(self):
        """Test check_signal without agent_id (returns None)."""
        coordinator = CoordinationSignals(memory=Mock(), agent_id=None)

        result = coordinator.check_signal(signal_type="test")

        assert result is None


class TestCoordinationSignalsWithStash:
    """Test CoordinationSignals fallback when no Redis client available."""

    def test_signal_without_client_logs_warning(self, caplog):
        """Test signal logs warning when no Redis client is available."""
        # Memory mock with no _client attribute
        memory = Mock(spec=[])
        coordinator = CoordinationSignals(memory=memory, agent_id="test")

        with caplog.at_level(logging.WARNING):
            signal_id = coordinator.signal(signal_type="test", payload={})

        # Signal ID is still generated
        assert signal_id.startswith("signal_")

        # Warning is logged about no Redis backend
        assert any("no Redis backend available" in record.message for record in caplog.records)


class TestCoordinationSignalsPermissions:
    """Test permission enforcement for coordination signals (v5.0)."""

    @pytest.fixture
    def mock_memory(self):
        """Mock memory with _client for Redis operations."""
        memory = Mock()
        memory._client = Mock()
        return memory

    def test_signal_without_credentials_logs_warning(self, mock_memory, caplog):
        """Test that sending signal without credentials logs security warning."""
        import logging

        caplog.set_level(logging.WARNING)

        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")

        # Send signal without credentials (backward compatibility mode)
        signal_id = coordinator.signal(
            signal_type="test",
            payload={"data": "test"},
            credentials=None,
        )

        # Should succeed but log warning
        assert signal_id != ""
        assert any("without credentials" in record.message.lower() for record in caplog.records)

    def test_signal_with_contributor_succeeds(self, mock_memory):
        """Test that CONTRIBUTOR tier can send signals."""
        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")
        credentials = AgentCredentials(agent_id="test-agent", tier=AccessTier.CONTRIBUTOR)

        # Should succeed
        signal_id = coordinator.signal(
            signal_type="test",
            payload={"data": "test"},
            credentials=credentials,
        )

        assert signal_id != ""
        assert mock_memory._client.setex.called
        # Credentials are used for permission check, not passed to storage layer

    def test_signal_with_validator_succeeds(self, mock_memory):
        """Test that VALIDATOR tier can send signals."""
        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")
        credentials = AgentCredentials(agent_id="test-agent", tier=AccessTier.VALIDATOR)

        # Should succeed (VALIDATOR > CONTRIBUTOR)
        signal_id = coordinator.signal(
            signal_type="test",
            payload={"data": "test"},
            credentials=credentials,
        )

        assert signal_id != ""
        assert mock_memory._client.setex.called

    def test_signal_with_steward_succeeds(self, mock_memory):
        """Test that STEWARD tier can send signals."""
        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")
        credentials = AgentCredentials(agent_id="test-agent", tier=AccessTier.STEWARD)

        # Should succeed (STEWARD > CONTRIBUTOR)
        signal_id = coordinator.signal(
            signal_type="test",
            payload={"data": "test"},
            credentials=credentials,
        )

        assert signal_id != ""
        assert mock_memory._client.setex.called

    def test_signal_with_observer_fails(self, mock_memory):
        """Test that OBSERVER tier cannot send signals."""
        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")
        credentials = AgentCredentials(agent_id="test-agent", tier=AccessTier.OBSERVER)

        # Should raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            coordinator.signal(
                signal_type="test",
                payload={"data": "test"},
                credentials=credentials,
            )

        assert "CONTRIBUTOR" in str(exc_info.value)
        assert "OBSERVER" in str(exc_info.value)
        assert not mock_memory.stash.called

    def test_broadcast_with_observer_fails(self, mock_memory):
        """Test that broadcast also enforces permissions."""
        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")
        credentials = AgentCredentials(agent_id="test-agent", tier=AccessTier.OBSERVER)

        # Should raise PermissionError
        with pytest.raises(PermissionError) as exc_info:
            coordinator.broadcast(
                signal_type="test",
                payload={"data": "test"},
                credentials=credentials,
            )

        assert "CONTRIBUTOR" in str(exc_info.value)
        assert not mock_memory.stash.called

    def test_broadcast_with_contributor_succeeds(self, mock_memory):
        """Test that broadcast works with valid credentials."""
        coordinator = CoordinationSignals(memory=mock_memory, agent_id="test-agent")
        credentials = AgentCredentials(agent_id="test-agent", tier=AccessTier.CONTRIBUTOR)

        # Should succeed
        signal_id = coordinator.broadcast(
            signal_type="test",
            payload={"data": "test"},
            credentials=credentials,
        )

        assert signal_id != ""
        assert mock_memory._client.setex.called

        # Verify it's a broadcast (target_agent=None)
        call_args = mock_memory._client.setex.call_args
        key = call_args[0][0]  # First positional arg is the key
        assert "empathy:signal:*:" in key  # * is the broadcast target
