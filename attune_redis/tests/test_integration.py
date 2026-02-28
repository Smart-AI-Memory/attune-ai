"""Integration tests for AMSMemoryBackend.

These tests require a running Redis Agent Memory Server.
They skip automatically when AMS is unavailable.

Run with:
    pytest attune_redis/tests/test_integration.py -v -m integration

Start AMS locally:
    docker run -d -p 8000:8000 redis/agent-memory-server
"""

from __future__ import annotations

import os
import uuid

import pytest

from attune_redis.config import RedisPluginConfig

# All tests in this module require a live AMS instance
pytestmark = [pytest.mark.integration]


def _ams_available() -> bool:
    """Check if AMS is reachable."""
    try:
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
        )
        backend = AMSMemoryBackend(config=config)
        connected = backend.is_connected()
        backend.close()
        return connected
    except Exception:  # noqa: BLE001
        # INTENTIONAL: Any failure means AMS is unavailable
        return False


# Skip entire module if AMS is not running
pytestmark.append(
    pytest.mark.skipif(
        not _ams_available(),
        reason="AMS not available (set AMS_BASE_URL or run locally)",
    )
)


@pytest.fixture()
def backend():
    """Create AMSMemoryBackend connected to live AMS."""
    from attune_redis.memory import AMSMemoryBackend

    session_id = f"integration-test-{uuid.uuid4().hex[:8]}"
    config = RedisPluginConfig(
        ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
        ams_namespace="attune-test",
        default_session_id=session_id,
    )
    b = AMSMemoryBackend(config=config)
    yield b
    b.close()


class TestStashRetrieveRoundTrip:
    """Test real stash/retrieve against AMS."""

    def test_stash_returns_true(self, backend):
        """stash() succeeds against live AMS."""
        assert backend.stash("test-key", {"hello": "world"}) is True

    def test_retrieve_after_stash(self, backend):
        """retrieve() returns what was stashed."""
        backend.stash("round-trip", "test-value")
        result = backend.retrieve("round-trip")
        assert result == "test-value"

    def test_retrieve_missing_returns_none(self, backend):
        """retrieve() returns None for missing keys."""
        result = backend.retrieve("nonexistent-key")
        assert result is None

    def test_stash_complex_data(self, backend):
        """stash() handles nested dicts and lists."""
        data = {
            "scores": [1, 2, 3],
            "nested": {"a": True, "b": None},
        }
        backend.stash("complex", data)
        result = backend.retrieve("complex")
        assert result == data


class TestDelete:
    """Test real delete against AMS."""

    def test_delete_existing(self, backend):
        """delete() returns True for existing key."""
        backend.stash("to-delete", "value")
        assert backend.delete("to-delete") is True

    def test_delete_missing(self, backend):
        """delete() returns False for missing key."""
        assert backend.delete("never-existed") is False

    def test_delete_removes_key(self, backend):
        """deleted key is no longer retrievable."""
        backend.stash("temp", "data")
        backend.delete("temp")
        assert backend.retrieve("temp") is None


class TestKeys:
    """Test real keys listing against AMS."""

    def test_keys_returns_stashed_keys(self, backend):
        """keys() includes recently stashed keys."""
        backend.stash("k1", 1)
        backend.stash("k2", 2)
        result = backend.keys()
        assert "k1" in result
        assert "k2" in result

    def test_keys_with_pattern(self, backend):
        """keys() filters by glob pattern."""
        backend.stash("prefix:a", 1)
        backend.stash("prefix:b", 2)
        backend.stash("other", 3)
        result = backend.keys("prefix:*")
        assert "prefix:a" in result
        assert "prefix:b" in result
        assert "other" not in result


class TestConnectionLifecycle:
    """Test connection health and lifecycle."""

    def test_is_connected(self, backend):
        """is_connected() returns True when AMS is up."""
        assert backend.is_connected() is True

    def test_get_stats(self, backend):
        """get_stats() returns dict with connection info."""
        stats = backend.get_stats()
        assert isinstance(stats, dict)
        assert stats["mode"] == "ams"
        assert stats["connected"] is True

    def test_close_and_reconnect(self):
        """close() doesn't prevent creating a new backend."""
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url=os.environ.get("AMS_BASE_URL", "http://localhost:8000"),
            ams_namespace="attune-test",
            default_session_id=f"lifecycle-{uuid.uuid4().hex[:8]}",
        )
        b1 = AMSMemoryBackend(config=config)
        b1.stash("before-close", "value")
        b1.close()

        b2 = AMSMemoryBackend(config=config)
        assert b2.is_connected() is True
        b2.close()


class TestErrorHandling:
    """Test graceful degradation with bad config."""

    def test_bad_url_stash_returns_false(self):
        """stash() returns False when AMS is unreachable."""
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url="http://localhost:19999",
            default_session_id="error-test",
        )
        b = AMSMemoryBackend(config=config)
        assert b.stash("key", "val") is False
        b.close()

    def test_bad_url_is_connected_returns_false(self):
        """is_connected() returns False for bad URL."""
        from attune_redis.memory import AMSMemoryBackend

        config = RedisPluginConfig(
            ams_base_url="http://localhost:19999",
            default_session_id="error-test",
        )
        b = AMSMemoryBackend(config=config)
        assert b.is_connected() is False
        b.close()
