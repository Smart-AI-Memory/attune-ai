"""Tests for Redis pub/sub signal bus."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from attune_redis.signals import RedisSignalBus


@pytest.fixture()
def mock_redis():
    """Create a mocked redis connection."""
    with patch("redis.from_url") as mock_from_url:
        client = MagicMock()
        mock_from_url.return_value = client
        yield client


class TestRedisSignalBusInit:
    """Test signal bus initialization."""

    def test_creates_redis_connection(self, mock_redis):
        """Bus creates a Redis connection from URL."""
        bus = RedisSignalBus("redis://localhost:6379")
        assert bus._closed is False

    def test_raises_import_error_without_redis(self):
        """Bus raises ImportError when redis not installed."""
        with patch.dict("sys.modules", {"redis": None}):
            with pytest.raises(ImportError):
                RedisSignalBus("redis://localhost:6379")


class TestSend:
    """Test message publishing."""

    def test_send_publishes_json(self, mock_redis):
        """Send serializes message as JSON and publishes."""
        bus = RedisSignalBus("redis://localhost:6379")
        bus.send("channel:test", {"type": "update", "data": 42})

        mock_redis.publish.assert_called_once_with(
            "channel:test",
            json.dumps({"type": "update", "data": 42}),
        )

    def test_send_returns_subscriber_count(self, mock_redis):
        """Send returns number of subscribers that received."""
        mock_redis.publish.return_value = 3
        bus = RedisSignalBus("redis://localhost:6379")

        result = bus.send("ch", {"msg": "hi"})
        assert result == 3


class TestIsConnected:
    """Test health check."""

    def test_connected_when_ping_succeeds(self, mock_redis):
        """is_connected returns True when Redis responds."""
        mock_redis.ping.return_value = True
        bus = RedisSignalBus("redis://localhost:6379")

        assert bus.is_connected() is True

    def test_disconnected_when_ping_fails(self, mock_redis):
        """is_connected returns False when Redis is down."""
        mock_redis.ping.side_effect = ConnectionError("refused")
        bus = RedisSignalBus("redis://localhost:6379")

        assert bus.is_connected() is False


class TestClose:
    """Test connection cleanup."""

    def test_close_calls_redis_close(self, mock_redis):
        """Close delegates to redis client."""
        bus = RedisSignalBus("redis://localhost:6379")
        bus.close()

        mock_redis.close.assert_called_once()
        assert bus._closed is True

    def test_close_is_idempotent(self, mock_redis):
        """Second close is a no-op."""
        bus = RedisSignalBus("redis://localhost:6379")
        bus.close()
        bus.close()

        mock_redis.close.assert_called_once()

    def test_close_handles_error_gracefully(self, mock_redis):
        """Close catches Redis errors during cleanup."""
        mock_redis.close.side_effect = RuntimeError("conn lost")
        bus = RedisSignalBus("redis://localhost:6379")

        bus.close()  # Should not raise
        assert bus._closed is True
