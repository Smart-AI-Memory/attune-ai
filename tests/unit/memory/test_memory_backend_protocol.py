"""Tests for MemoryBackend protocol compliance.

Verifies that FileSessionMemory, RedisShortTermMemory,
and AMSMemoryBackend satisfy the MemoryBackend protocol.
"""

import time
from typing import Any
from unittest.mock import patch

import pytest

from attune.memory.backend import MemoryBackend, SearchableMemoryBackend
from attune.memory.file_session import FileSessionConfig, FileSessionMemory

# =========================================================================
# Protocol compliance
# =========================================================================


class TestFileSessionMemoryProtocol:
    """Verify FileSessionMemory satisfies MemoryBackend."""

    def test_isinstance_check(self, tmp_path):
        """FileSessionMemory must pass runtime protocol check."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        assert isinstance(mem, MemoryBackend)

    def test_stash_returns_bool(self, tmp_path):
        """stash() must return True on success."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        result = mem.stash("k1", {"v": 1})
        assert result is True

    def test_retrieve_returns_value_or_none(self, tmp_path):
        """retrieve() must return stored value or None."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        assert mem.retrieve("missing") is None

        mem.stash("k1", "hello")
        assert mem.retrieve("k1") == "hello"

    def test_delete_returns_bool(self, tmp_path):
        """delete() must return True/False."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        assert mem.delete("missing") is False

        mem.stash("k1", 42)
        assert mem.delete("k1") is True
        assert mem.retrieve("k1") is None

    def test_keys_returns_list(self, tmp_path):
        """keys() must return list of strings."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        mem.stash("prefix:a", 1)
        mem.stash("prefix:b", 2)
        mem.stash("other", 3)

        result = mem.keys("prefix:*")
        assert isinstance(result, list)
        assert set(result) == {"prefix:a", "prefix:b"}

    def test_is_connected_returns_bool(self, tmp_path):
        """is_connected() must return True for file backend."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        assert mem.is_connected() is True

    def test_get_stats_returns_dict(self, tmp_path):
        """get_stats() must return a dict."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        stats = mem.get_stats()
        assert isinstance(stats, dict)
        assert "mode" in stats

    def test_close_succeeds(self, tmp_path):
        """close() must not raise."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        mem.stash("k", "v")
        mem.close()  # Should not raise

    def test_supports_realtime_returns_false(self, tmp_path):
        """File backend does not support realtime."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        assert mem.supports_realtime() is False

    def test_supports_distributed_returns_false(self, tmp_path):
        """File backend does not support distributed ops."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        assert mem.supports_distributed() is False

    def test_ttl_expiration(self, tmp_path):
        """stash() with ttl should expire entries."""
        config = FileSessionConfig(base_dir=str(tmp_path / ".attune"))
        mem = FileSessionMemory(user_id="proto-test", config=config)

        mem.stash("ephemeral", "gone-soon", ttl=1)
        assert mem.retrieve("ephemeral") == "gone-soon"

        time.sleep(1.1)
        assert mem.retrieve("ephemeral") is None


class TestAMSMemoryBackendProtocol:
    """Verify AMSMemoryBackend satisfies MemoryBackend.

    Uses mocked AMS client so no server is needed.
    """

    @pytest.fixture
    def backend(self):
        """Create AMSMemoryBackend with mocked client."""
        from unittest.mock import AsyncMock

        # Import here to handle optional dependency
        try:
            import agent_memory_client  # noqa: F401

            from attune_redis.config import RedisPluginConfig
            from attune_redis.memory import AMSMemoryBackend
            from attune_redis.tests.conftest import (
                FakeHealthCheckResponse,
                FakeMemoryRecordResults,
                FakeSessionListResponse,
                FakeWorkingMemoryResponse,
            )
        except ImportError:
            pytest.skip("attune-redis plugin or agent-memory-client not available")

        config = RedisPluginConfig(
            ams_base_url="http://localhost:9999",
            ams_namespace="test",
            default_session_id="proto-test",
        )

        _data: dict[str, Any] = {}

        mock_client = AsyncMock()

        async def _get_wm(**kw):
            return FakeWorkingMemoryResponse(data=dict(_data))

        async def _get_or_create_wm(**kw):
            # AMS 0.14.0 get_or_create returns (created, WorkingMemory); the
            # backend unpacks `_, response`. retrieve/delete/keys read via this.
            return (False, FakeWorkingMemoryResponse(data=dict(_data)))

        async def _set_wm(session_id, data, namespace=None, preserve_existing=True):
            if preserve_existing:
                _data.update(data)
            else:
                _data.clear()
                _data.update(data)
            return FakeWorkingMemoryResponse(data=dict(_data))

        async def _update_wm(session_id, data_updates, namespace=None, merge_strategy="merge"):
            if merge_strategy == "replace":
                _data.clear()
                _data.update(data_updates)
            else:
                _data.update(data_updates)
            return FakeWorkingMemoryResponse(data=dict(_data))

        mock_client.get_working_memory.side_effect = _get_wm
        mock_client.get_or_create_working_memory.side_effect = _get_or_create_wm
        mock_client.set_working_memory_data.side_effect = _set_wm
        mock_client.update_working_memory_data.side_effect = _update_wm
        mock_client.health_check.return_value = FakeHealthCheckResponse()
        mock_client.list_sessions.return_value = FakeSessionListResponse()
        mock_client.close.return_value = None
        mock_client.search_long_term_memory.return_value = FakeMemoryRecordResults()
        mock_client.promote_working_memories_to_long_term.return_value = None

        with patch("agent_memory_client.MemoryAPIClient", return_value=mock_client):
            b = AMSMemoryBackend(config=config)
            b._client = mock_client
            return b

    def test_isinstance_check(self, backend):
        """AMSMemoryBackend passes MemoryBackend protocol check."""
        assert isinstance(backend, MemoryBackend)

    def test_searchable_isinstance_check(self, backend):
        """AMSMemoryBackend passes SearchableMemoryBackend check."""
        assert isinstance(backend, SearchableMemoryBackend)

    def test_stash_returns_bool(self, backend):
        """stash() returns True on success."""
        assert backend.stash("k1", {"v": 1}) is True

    def test_retrieve_returns_value_or_none(self, backend):
        """retrieve() returns stored value or None."""
        assert backend.retrieve("missing") is None
        backend.stash("k1", "hello")
        assert backend.retrieve("k1") == "hello"

    def test_delete_returns_bool(self, backend):
        """delete() returns True/False."""
        assert backend.delete("missing") is False
        backend.stash("k1", 42)
        assert backend.delete("k1") is True

    def test_keys_returns_list(self, backend):
        """keys() returns list of strings."""
        backend.stash("prefix:a", 1)
        backend.stash("prefix:b", 2)
        result = backend.keys("prefix:*")
        assert isinstance(result, list)
        assert set(result) == {"prefix:a", "prefix:b"}

    def test_is_connected_returns_bool(self, backend):
        """is_connected() returns True when healthy."""
        assert backend.is_connected() is True

    def test_get_stats_returns_dict(self, backend):
        """get_stats() returns a dict."""
        stats = backend.get_stats()
        assert isinstance(stats, dict)
        assert stats["mode"] == "ams"

    def test_close_succeeds(self, backend):
        """close() must not raise."""
        backend.close()

    def test_supports_distributed(self, backend):
        """AMS backend supports distributed ops."""
        assert backend.supports_distributed() is True


# =========================================================================
# Custom backend compliance
# =========================================================================


class MinimalBackend:
    """Minimal backend to verify protocol is not too strict."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def stash(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        agent_id: str | None = None,
    ) -> bool:
        self._data[key] = value
        return True

    def retrieve(self, key: str, agent_id: str | None = None) -> Any | None:
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def keys(self, pattern: str = "*") -> list[str]:
        return list(self._data.keys())

    def is_connected(self) -> bool:
        return True

    def get_stats(self) -> dict:
        return {"keys": len(self._data)}

    def close(self) -> None:
        self._data.clear()

    def supports_realtime(self) -> bool:
        return False

    def supports_distributed(self) -> bool:
        return False


class TestMinimalBackendProtocol:
    """A bare-minimum implementation must also pass."""

    def test_isinstance_check(self):
        """MinimalBackend satisfies MemoryBackend protocol."""
        backend = MinimalBackend()
        assert isinstance(backend, MemoryBackend)

    def test_round_trip(self):
        """Basic stash/retrieve works."""
        backend = MinimalBackend()
        backend.stash("k", "v")
        assert backend.retrieve("k") == "v"
