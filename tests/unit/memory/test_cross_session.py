"""Tests for cross-session agent communication.

Tests the CrossSessionCoordinator, BackgroundService, and session discovery
functionality for multi-session agent coordination.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from attune.memory.cross_session import (
    STALE_THRESHOLD_SECONDS,
    CrossSessionCoordinator,
    SessionInfo,
    SessionType,
    generate_agent_id,
)
from attune.memory.short_term import AccessTier, RedisShortTermMemory


class TestGenerateAgentId:
    """Tests for generate_agent_id function."""

    def test_generates_unique_ids(self):
        """Each call should produce a unique ID."""
        ids = [generate_agent_id(SessionType.CLAUDE) for _ in range(10)]
        assert len(set(ids)) == 10  # All unique

    def test_includes_session_type(self):
        """ID should include the session type prefix."""
        claude_id = generate_agent_id(SessionType.CLAUDE)
        service_id = generate_agent_id(SessionType.SERVICE)
        worker_id = generate_agent_id(SessionType.WORKER)

        assert claude_id.startswith("claude_")
        assert service_id.startswith("service_")
        assert worker_id.startswith("worker_")

    def test_includes_timestamp(self):
        """ID should include a timestamp component."""
        agent_id = generate_agent_id(SessionType.CLAUDE)
        parts = agent_id.split("_")
        assert len(parts) == 3
        # Second part should be a timestamp (14 digits: YYYYMMDDHHmmss)
        assert len(parts[1]) == 14
        assert parts[1].isdigit()


class TestSessionInfo:
    """Tests for SessionInfo dataclass."""

    def test_to_dict_and_from_dict(self):
        """Should round-trip through dict conversion."""
        original = SessionInfo(
            agent_id="claude_20260120_abc123",
            session_type=SessionType.CLAUDE,
            access_tier=AccessTier.CONTRIBUTOR,
            capabilities=["stash", "retrieve"],
            started_at=datetime(2026, 1, 20, 10, 0, 0),
            last_heartbeat=datetime(2026, 1, 20, 10, 5, 0),
            metadata={"key": "value"},
        )

        as_dict = original.to_dict()
        restored = SessionInfo.from_dict(as_dict)

        assert restored.agent_id == original.agent_id
        assert restored.session_type == original.session_type
        assert restored.access_tier == original.access_tier
        assert restored.capabilities == original.capabilities
        assert restored.started_at == original.started_at
        assert restored.last_heartbeat == original.last_heartbeat
        assert restored.metadata == original.metadata

    def test_is_stale_fresh_session(self):
        """Recent heartbeat should not be stale."""
        session = SessionInfo(
            agent_id="test",
            session_type=SessionType.CLAUDE,
            access_tier=AccessTier.CONTRIBUTOR,
            capabilities=[],
            started_at=datetime.now(),
            last_heartbeat=datetime.now(),
        )
        assert not session.is_stale

    def test_is_stale_old_heartbeat(self):
        """Old heartbeat should be stale."""
        old_time = datetime.now() - timedelta(seconds=STALE_THRESHOLD_SECONDS + 10)
        session = SessionInfo(
            agent_id="test",
            session_type=SessionType.CLAUDE,
            access_tier=AccessTier.CONTRIBUTOR,
            capabilities=[],
            started_at=old_time,
            last_heartbeat=old_time,
        )
        assert session.is_stale


class TestCrossSessionCoordinatorMockMode:
    """Tests that verify mock mode raises appropriate errors."""

    def test_degrades_on_mock_mode(self):
        """Should degrade gracefully when Redis is not available or memory is in mock mode."""
        memory = RedisShortTermMemory(use_mock=True)

        # Phase 2.5: CrossSessionCoordinator no longer raises on mock mode,
        # it enters degraded mode instead with a warning.
        # auto_announce=False: ``_degraded`` is set before the announce
        # block, so the assertion still holds, and we avoid leaking a
        # heartbeat daemon thread (see docs/specs/ci-runner-hang/).
        coordinator = CrossSessionCoordinator(memory=memory, auto_announce=False)
        assert coordinator._degraded is True
