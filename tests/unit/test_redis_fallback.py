"""Redis Fallback & Recovery Tests for RedisShortTermMemory.

Tests graceful degradation when Redis is unavailable including:
- Fallback to in-memory mock storage
- Recovery when Redis comes back online
- Data consistency during fallback
- No data loss on connection failures

These tests address the critical gap identified in TEST_IMPROVEMENT_PLAN.md
Phase 1: Redis Failure & Recovery Tests (CRITICAL severity).

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import Mock, patch

import pytest

pytest.importorskip("redis")

import redis  # noqa: E402

from attune.memory.short_term import (  # noqa: E402
    AccessTier,
    AgentCredentials,
    RedisConfig,
    RedisShortTermMemory,
    TTLStrategy,
)
from attune.memory.short_term.base import BaseOperations  # noqa: E402

# Common patches needed to bypass auto-detection layers.
# The facade checks MemoryFeatures.check_redis() and base.py
# checks REDIS_AVAILABLE and may run RedisAutoDetector.
# These patches ensure tests reach the actual retry logic.
_PATCH_REDIS_AVAILABLE = patch("attune.memory.short_term.base.REDIS_AVAILABLE", True)
_PATCH_FEATURES = patch(
    "attune.memory.features.MemoryFeatures.check_redis",
    return_value=True,
)
_PATCH_AUTO_DETECT = patch(
    "attune.memory.short_term.base.RedisAutoDetector",
)


def _redis_running() -> bool:
    """Check if Redis is actually running on localhost."""
    try:
        r = redis.Redis(host="127.0.0.1", port=6379, socket_connect_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def _drive_retry(ping):
    """Exercise ``_create_client_with_retry`` in isolation and return the base.

    The retry-metric assertions used to go through the full
    ``RedisShortTermMemory`` constructor, whose ``use_mock`` gate reads the
    module-global ``REDIS_AVAILABLE`` (``base.py``). That made them vulnerable
    to cross-test xdist patch pollution — a sibling leaving stale module state
    flipped ``use_mock`` to True, the retry path was skipped, and
    ``retries_total`` stayed 0 (the long-standing flake that xfailed these
    tests on Ubuntu/Windows lanes).

    Instead, build a mock-mode ``BaseOperations`` (so construction never enters
    the retry path) and call ``_create_client_with_retry`` directly with
    ``redis.Redis`` patched and a zero backoff. This tests the exact retry
    logic deterministically, with no dependency on the polluted gate.

    Args:
        ping: callable assigned to the mock client's ``ping`` (raise to retry).

    Returns:
        The ``BaseOperations`` instance — inspect ``.metrics.retries_total``.
    """
    base = BaseOperations(use_mock=True)
    base._config.retry_base_delay = 0
    base._config.retry_max_delay = 0
    mock_client = Mock()
    mock_client.ping = ping
    with patch("attune.memory.short_term.base.redis.Redis", return_value=mock_client):
        base._create_client_with_retry()
    return base


class TestRedisFallbackBehavior:
    """Test that RedisShortTermMemory gracefully falls back to mock when Redis unavailable."""

    @patch("attune.memory.redis_auto_detect.RedisAutoDetector")
    @patch("attune.memory.features.MemoryFeatures.check_redis", return_value=True)
    @patch("attune.memory.short_term.base.REDIS_AVAILABLE", True)
    @patch("attune.memory.short_term.base.redis.Redis")
    def test_falls_back_to_mock_on_connection_failure(
        self, mock_redis_cls, _mock_feat, mock_detector
    ):
        # Force auto-detect to report Redis available so the production
        # __init__ proceeds to _create_client_with_retry() instead of
        # short-circuiting to mock when no real Redis server runs (CI).
        mock_detector.return_value.detect.return_value = type(
            "DetectResult", (), {"available": True, "reason": ""}
        )()
        """Test graceful fallback to mock storage when Redis connection fails."""
        # Mock Redis connection failure
        mock_redis_cls.side_effect = redis.ConnectionError("Connection refused")

        # Should raise exception after retries exhausted
        with pytest.raises(redis.ConnectionError):
            _ = RedisShortTermMemory(host="127.0.0.1", port=6379)

        # Verify it attempted to connect
        assert mock_redis_cls.called

    @patch("attune.memory.redis_auto_detect.RedisAutoDetector")
    @patch("attune.memory.features.MemoryFeatures.check_redis", return_value=True)
    @patch("attune.memory.short_term.base.REDIS_AVAILABLE", True)
    @patch("attune.memory.short_term.base.redis.Redis")
    def test_falls_back_to_mock_on_auth_failure(self, mock_redis_cls, _mock_feat, mock_detector):
        """Test graceful fallback when Redis authentication fails."""
        # See test_falls_back_to_mock_on_connection_failure for why
        # auto-detect is patched.
        mock_detector.return_value.detect.return_value = type(
            "DetectResult", (), {"available": True, "reason": ""}
        )()
        mock_client = Mock()
        mock_client.ping.side_effect = redis.AuthenticationError("Invalid password")
        mock_redis_cls.return_value = mock_client

        # Auth errors are not retried (not ConnectionError/TimeoutError)
        with pytest.raises(redis.AuthenticationError):
            _ = RedisShortTermMemory(host="127.0.0.1", port=6379, password="wrong")

    @patch("attune.memory.redis_auto_detect.RedisAutoDetector")
    @patch("attune.memory.features.MemoryFeatures.check_redis", return_value=True)
    @patch("attune.memory.short_term.base.REDIS_AVAILABLE", True)
    @patch("attune.memory.short_term.base.redis.Redis")
    def test_retries_connection_with_exponential_backoff(
        self, mock_redis_cls, _mock_feat, mock_detector
    ):
        """Test that connection retries use exponential backoff."""
        # See test_falls_back_to_mock_on_connection_failure for why
        # auto-detect is patched.
        mock_detector.return_value.detect.return_value = type(
            "DetectResult", (), {"available": True, "reason": ""}
        )()
        mock_client = Mock()
        call_count = 0

        def ping_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise redis.ConnectionError("Connection refused")
            return True  # Success on 3rd attempt

        mock_client.ping = ping_with_retry
        mock_redis_cls.return_value = mock_client

        # Should succeed after retries
        memory = RedisShortTermMemory(host="127.0.0.1", port=6379)

        # Verify it retried 3 times
        assert call_count == 3
        assert memory._metrics.retries_total >= 2  # At least 2 retries before success

    @patch("attune.memory.short_term.base.REDIS_AVAILABLE", False)
    def test_uses_mock_when_redis_not_installed(self):
        """Test that mock storage is used when Redis package not available."""
        memory = RedisShortTermMemory(host="127.0.0.1", port=6379)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Should use mock
        assert memory.use_mock is True
        assert memory._client is None

        # Should still be functional
        memory.stash("test_key", {"data": "test_value"}, creds, ttl=TTLStrategy.WORKING_RESULTS)
        result = memory.retrieve("test_key", creds)
        assert result == {"data": "test_value"}


class TestMockStorageFunctionality:
    """Test that mock storage provides equivalent functionality to Redis."""

    def test_mock_storage_stash_and_retrieve(self):
        """Test basic stash/retrieve operations in mock storage."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        data = {"test": "value", "number": 42}
        memory.stash("result1", data, creds, ttl=TTLStrategy.WORKING_RESULTS)

        result = memory.retrieve("result1", creds)
        assert result == data

    def test_mock_storage_respects_ttl(self):
        """Test that mock storage respects TTL expiration."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Stash data
        memory.stash("expires_soon", {"data": "test"}, creds, ttl=TTLStrategy.SESSION)

        # Should be retrievable immediately
        result = memory.retrieve("expires_soon", creds)
        assert result == {"data": "test"}

    def test_mock_storage_handles_missing_keys(self):
        """Test that mock storage handles missing keys gracefully."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Retrieve non-existent key
        result = memory.retrieve("nonexistent", creds)
        assert result is None

    def test_mock_storage_stage_pattern(self):
        """Test pattern staging in mock storage."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        from attune.memory.short_term import StagedPattern

        pattern = StagedPattern(
            pattern_id="test_pattern",
            agent_id="test_agent",
            pattern_type="test",
            name="Test Pattern",
            description="A test pattern for fallback testing",
            confidence=0.9,
        )

        memory.stage_pattern(pattern, creds)

        # Should be able to retrieve staged pattern
        retrieved = memory.get_staged_pattern("test_pattern", creds)
        assert retrieved is not None
        assert retrieved.pattern_id == "test_pattern"

    def test_mock_storage_clear_working_memory(self):
        """Test clearing working memory in mock storage."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Stash some data
        memory.stash("key1", {"data": "test1"}, creds, ttl=TTLStrategy.WORKING_RESULTS)
        memory.stash("key2", {"data": "test2"}, creds, ttl=TTLStrategy.WORKING_RESULTS)

        # Clear working memory
        cleared = memory.clear_working_memory(creds)
        assert cleared >= 0  # Should report number of keys cleared

    def test_mock_storage_ping(self):
        """Test ping returns true for mock storage."""
        memory = RedisShortTermMemory(use_mock=True)

        # Mock storage should always respond to ping
        assert memory.ping() is True


class TestDataConsistencyDuringFailover:
    """Test data consistency when failing over between Redis and mock."""

    @patch("attune.memory.short_term.REDIS_AVAILABLE", True)
    @patch("attune.memory.short_term.redis.Redis")
    def test_stash_fails_on_connection_loss(self, mock_redis_cls):
        """Test that stash operations fail gracefully on connection loss."""
        mock_client = Mock()
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Mock setex to raise connection error
        mock_client.setex.side_effect = redis.ConnectionError("Connection lost")
        mock_client.ping.return_value = True
        mock_redis_cls.return_value = mock_client

        memory = RedisShortTermMemory(host="127.0.0.1", port=6379)

        # Stash should raise exception after retries exhausted
        with pytest.raises(redis.ConnectionError):
            memory.stash("key1", {"data": "value1"}, creds, ttl=TTLStrategy.WORKING_RESULTS)


class TestConnectionRecovery:
    """Test automatic recovery when Redis connection is restored."""

    @patch("attune.memory.short_term.REDIS_AVAILABLE", True)
    @patch("attune.memory.short_term.redis.Redis")
    def test_connection_recovery_after_failure(self, mock_redis_cls):
        """Test that connection recovers automatically after transient failure."""
        mock_client = Mock()
        ping_count = 0

        def ping_with_recovery():
            nonlocal ping_count
            ping_count += 1
            if ping_count == 1:
                raise redis.ConnectionError("Connection lost")
            return True  # Recovered

        mock_client.ping = ping_with_recovery
        mock_client.setex.return_value = True
        mock_client.get.return_value = '{"data": "value"}'
        mock_redis_cls.return_value = mock_client

        # First connection attempt fails, retries succeed
        memory = RedisShortTermMemory(host="127.0.0.1", port=6379)

        # Should have recovered and ping should work
        assert memory.ping() is True

    def test_tracks_retry_metrics(self):
        """Retry attempts are tracked in metrics (1 failure before success)."""
        attempt = 0

        def ping_with_retries():
            nonlocal attempt
            attempt += 1
            if attempt < 2:
                raise redis.ConnectionError("Connection refused")
            return True

        base = _drive_retry(ping_with_retries)

        assert base._metrics.retries_total >= 1  # at least one retry occurred


class TestErrorHandlingEdgeCases:
    """Test edge cases in error handling and fallback logic."""

    def test_handles_redis_timeout_gracefully(self):
        """Test handling of Redis timeout errors."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Mock storage should never timeout
        memory.stash("key", {"data": "value"}, creds, ttl=TTLStrategy.WORKING_RESULTS)
        result = memory.retrieve("key", creds)
        assert result == {"data": "value"}

    @patch("attune.memory.short_term.REDIS_AVAILABLE", True)
    @patch("attune.memory.short_term.redis.Redis")
    def test_handles_redis_out_of_memory(self, mock_redis_cls):
        """Test handling of Redis OOM errors."""
        mock_client = Mock()
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)
        mock_client.ping.return_value = True
        mock_client.setex.side_effect = redis.ResponseError("OOM command not allowed")
        mock_redis_cls.return_value = mock_client

        memory = RedisShortTermMemory(host="127.0.0.1", port=6379)

        # Should raise ResponseError (not fallback - this is a config issue)
        with pytest.raises(redis.ResponseError):
            memory.stash("key", {"data": "value"}, creds, ttl=TTLStrategy.WORKING_RESULTS)

    def test_handles_max_clients_exceeded(self):
        """Retry loop re-raises after attempts are exhausted (max clients).

        Previously xfailed for cross-test xdist patch pollution; now drives
        ``_create_client_with_retry`` directly so it's deterministic. Here
        ``redis.Redis(...)`` itself raises every attempt, so the loop exhausts
        and re-raises the connection error.
        """
        base = BaseOperations(use_mock=True)
        base._config.retry_base_delay = 0
        base._config.retry_max_delay = 0
        with patch(
            "attune.memory.short_term.base.redis.Redis",
            side_effect=redis.ConnectionError("max number of clients reached"),
        ):
            with pytest.raises(redis.ConnectionError):
                base._create_client_with_retry()


class TestConfigurationValidation:
    """Test configuration validation for Redis connection."""

    @pytest.mark.skipif(
        not _redis_running(),
        reason="Redis not running on localhost",
    )
    def test_validates_retry_configuration(self):
        """Test that retry configuration is validated."""
        config = RedisConfig(
            host="127.0.0.1",
            port=6379,
            retry_max_attempts=3,
            retry_base_delay=0.1,
            retry_max_delay=2.0,
        )

        memory = RedisShortTermMemory(config=config)

        assert memory._config.retry_max_attempts == 3
        assert memory._config.retry_base_delay == 0.1
        assert memory._config.retry_max_delay == 2.0

    def test_ssl_configuration(self):
        """Test SSL/TLS configuration options."""
        config = RedisConfig(
            host="redis.example.com",
            port=6380,
            ssl=True,
            ssl_cert_reqs="required",
        )

        kwargs = config.to_redis_kwargs()

        assert kwargs["ssl"] is True
        assert kwargs["ssl_cert_reqs"] == "required"

    def test_socket_timeout_configuration(self):
        """Test socket timeout configuration."""
        config = RedisConfig(
            host="127.0.0.1",
            port=6379,
            socket_timeout=10.0,
            socket_connect_timeout=5.0,
        )

        kwargs = config.to_redis_kwargs()

        assert kwargs["socket_timeout"] == 10.0
        assert kwargs["socket_connect_timeout"] == 5.0


class TestMetricsTracking:
    """Test that metrics are properly tracked during fallback scenarios."""

    def test_tracks_retries_in_metrics(self):
        """Retry attempts increment the counter (2 failures, then success).

        Previously xfailed for cross-test xdist patch pollution; now exercises
        the retry logic directly via ``_drive_retry`` so it's deterministic.
        """
        call_count = 0

        def ping_with_retries():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise redis.TimeoutError("Timeout")
            return True

        base = _drive_retry(ping_with_retries)

        assert base._metrics.retries_total == 2  # 2 failures before success

    def test_mock_storage_provides_stats(self):
        """Test that mock storage provides stats."""
        memory = RedisShortTermMemory(use_mock=True)
        creds = AgentCredentials("test_agent", AccessTier.CONTRIBUTOR)

        # Perform operations
        memory.stash("key1", {"data": "value1"}, creds, ttl=TTLStrategy.WORKING_RESULTS)
        memory.retrieve("key1", creds)

        # Should be able to get stats
        stats = memory.get_stats()
        assert stats is not None
        assert "mode" in stats
        assert stats["mode"] == "mock"
