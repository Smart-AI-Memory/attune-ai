"""Tests for cross-session BackgroundService and convenience functions.

Covers:
- BackgroundService.__init__ raises ValueError in mock mode
- is_running default False
- get_status() when not running
- check_redis_cross_session_support with mock mode returns False
- get_or_start_service with mock mode returns None
"""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from attune.memory.cross_session.service import (
    BackgroundService,
    check_redis_cross_session_support,
    get_or_start_service,
)
from attune.memory.short_term import RedisShortTermMemory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_memory() -> RedisShortTermMemory:
    """Return RedisShortTermMemory that looks like a real Redis connection.

    Starts in mock mode (no real Redis), then patches _base.use_mock to
    False and injects a MagicMock client so that BackgroundService and
    check_redis_cross_session_support treat it as a live connection.
    """
    memory = RedisShortTermMemory(use_mock=True)
    mock_client = MagicMock()
    mock_client.set.return_value = True
    mock_client.get.return_value = None
    mock_client.hgetall.return_value = {}
    mock_client.hget.return_value = None
    memory._base._client = mock_client
    # Flip use_mock to False so service/support checks see a live connection
    memory._base.use_mock = False
    return memory


# ---------------------------------------------------------------------------
# BackgroundService.__init__
# ---------------------------------------------------------------------------


class TestBackgroundServiceInit:
    """BackgroundService constructor behaviour."""

    def test_raises_value_error_on_mock_mode(self):
        """Constructing BackgroundService with mock memory raises ValueError."""
        memory = RedisShortTermMemory(use_mock=True)
        with pytest.raises(ValueError, match="requires Redis"):
            BackgroundService(memory=memory)

    def test_is_running_defaults_to_false(self):
        """is_running is False immediately after construction."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        assert service.is_running is False

    def test_service_thread_initially_none(self):
        """The service thread attribute is None before start()."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        assert service._service_thread is None

    def test_coordinator_initially_none(self):
        """The internal coordinator is None before start()."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        assert service._coordinator is None


# ---------------------------------------------------------------------------
# get_status when not running
# ---------------------------------------------------------------------------


class TestBackgroundServiceStatus:
    """get_status() output when service has not been started."""

    def test_get_status_running_false(self):
        """Status dict reports running=False when service is idle."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        status = service.get_status()
        assert status["running"] is False

    def test_get_status_agent_id_none(self):
        """Status dict reports agent_id=None when coordinator not created."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        status = service.get_status()
        assert status["agent_id"] is None

    def test_get_status_active_sessions_zero(self):
        """Status dict reports active_sessions=0 when idle."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        status = service.get_status()
        assert status["active_sessions"] == 0

    def test_get_status_no_sessions_key(self):
        """Status dict has no 'sessions' key when coordinator is absent."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        status = service.get_status()
        assert "sessions" not in status


# ---------------------------------------------------------------------------
# stop() safety
# ---------------------------------------------------------------------------


class TestBackgroundServiceStop:
    """stop() behaviour when service has not been started."""

    def test_stop_when_not_running_is_safe(self):
        """stop() does not raise when the service was never started."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        service.stop()  # Must not raise

    def test_stop_does_not_set_running(self):
        """is_running stays False after stop() on a never-started service."""
        memory = _mock_memory()
        service = BackgroundService(memory=memory)
        service.stop()
        assert service.is_running is False


# ---------------------------------------------------------------------------
# start() with mock client — thread must not actually run
# ---------------------------------------------------------------------------


class TestBackgroundServiceStart:
    """start() with mocked thread creation so daemon threads never run."""

    def test_start_fails_when_lock_not_acquired(self):
        """start() returns False when the service lock is already held."""
        memory = _mock_memory()
        memory._base._client.set.return_value = None  # lock held
        service = BackgroundService(memory=memory)
        result = service.start()
        assert result is False
        assert service.is_running is False

    def test_start_succeeds_when_lock_acquired(self):
        """start() returns True and sets is_running when lock is free."""
        memory = _mock_memory()
        memory._base._client.set.return_value = True

        with patch.object(threading.Thread, "start"), patch.object(threading.Thread, "join"):
            service = BackgroundService(memory=memory)
            result = service.start()
            assert result is True
            assert service.is_running is True
            service.stop()

    def test_start_returns_false_when_already_running(self):
        """Calling start() twice returns False on the second call."""
        memory = _mock_memory()
        memory._base._client.set.return_value = True

        with patch.object(threading.Thread, "start"), patch.object(threading.Thread, "join"):
            service = BackgroundService(memory=memory)
            service.start()
            second_result = service.start()
            assert second_result is False
            service.stop()


# ---------------------------------------------------------------------------
# check_redis_cross_session_support
# ---------------------------------------------------------------------------


class TestCheckRedisCrossSessionSupport:
    """Convenience function for checking cross-session availability."""

    def test_returns_false_for_mock_memory(self):
        """Returns False when memory is in mock mode (client is None)."""
        memory = RedisShortTermMemory(use_mock=True)
        assert check_redis_cross_session_support(memory) is False

    def test_returns_true_when_client_is_present(self):
        """Returns True when memory has a live (or mocked) client."""
        memory = _mock_memory()
        assert check_redis_cross_session_support(memory) is True

    def test_mock_mode_flag_takes_precedence(self):
        """use_mock=True makes the function return False even with a client."""
        memory = RedisShortTermMemory(use_mock=True)
        # Inject a mock client but leave use_mock=True so the check fails
        memory._base._client = MagicMock()
        # use_mock is still True → function returns False
        assert check_redis_cross_session_support(memory) is False


# ---------------------------------------------------------------------------
# get_or_start_service
# ---------------------------------------------------------------------------


class TestGetOrStartService:
    """get_or_start_service convenience function."""

    def test_returns_none_for_mock_memory(self):
        """Returns None immediately when Redis support is unavailable."""
        memory = RedisShortTermMemory(use_mock=True)
        result = get_or_start_service(memory)
        assert result is None

    def test_returns_none_when_lock_held(self):
        """Returns None when service lock is already held by another process."""
        memory = _mock_memory()
        memory._base._client.set.return_value = None  # lock held

        result = get_or_start_service(memory)
        assert result is None

    def test_returns_service_when_started(self):
        """Returns a BackgroundService when the lock is successfully acquired."""
        memory = _mock_memory()
        memory._base._client.set.return_value = True

        with patch.object(threading.Thread, "start"), patch.object(threading.Thread, "join"):
            result = get_or_start_service(memory)
            assert isinstance(result, BackgroundService)
            assert result.is_running is True
            result.stop()
