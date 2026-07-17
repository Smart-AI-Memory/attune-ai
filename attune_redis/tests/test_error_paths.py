"""Tests covering error paths and edge cases.

Targets uncovered branches in memory.py, mcp_tools.py,
and plugin.py to bring coverage above 80%.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune_redis.mcp_tools import (
    handle_redis_health_check,
    handle_redis_memory_promote,
    handle_redis_memory_retrieve,
    handle_redis_memory_search,
    handle_redis_memory_store,
)
from attune_redis.memory import AMSMemoryBackend, _run_sync

# =================================================================
# _run_sync() — ThreadPoolExecutor branch (memory.py lines 46-49)
# =================================================================


class TestRunSync:
    """Test the async-to-sync helper."""

    def test_run_sync_no_loop(self):
        """_run_sync works when no event loop is running."""

        async def coro():
            return 42

        assert _run_sync(coro()) == 42

    def test_run_sync_inside_running_loop(self):
        """_run_sync falls back to ThreadPoolExecutor inside a loop."""

        async def coro():
            return "from-thread"

        async def outer():
            # We're inside a running loop here
            return _run_sync(coro())

        result = asyncio.run(outer())
        assert result == "from-thread"


# =================================================================
# AMSMemoryBackend error paths (memory.py exception branches)
# =================================================================


@pytest.fixture()
def failing_backend(redis_config):
    """Create backend with a client that raises on every call."""
    with patch("agent_memory_client.MemoryAPIClient") as mock_cls:
        client = AsyncMock()
        error = ConnectionError("AMS unreachable")
        client.set_working_memory_data.side_effect = error
        client.get_working_memory.side_effect = error
        client.get_or_create_working_memory.side_effect = error
        client.update_working_memory_data.side_effect = error
        client.health_check.side_effect = error
        client.list_sessions.side_effect = error
        client.close.side_effect = error
        client.search_long_term_memory.side_effect = error
        client.promote_working_memories_to_long_term.side_effect = error
        mock_cls.return_value = client

        b = AMSMemoryBackend(config=redis_config)
        b._client = client
        return b


class TestMemoryErrorPaths:
    """AMSMemoryBackend gracefully degrades on AMS errors."""

    def test_stash_error_returns_false(self, failing_backend):
        """stash() returns False on AMS error."""
        assert failing_backend.stash("k", "v") is False

    def test_retrieve_error_returns_none(self, failing_backend):
        """retrieve() returns None on AMS error."""
        assert failing_backend.retrieve("k") is None

    def test_delete_error_returns_false(self, failing_backend):
        """delete() returns False on AMS error."""
        assert failing_backend.delete("k") is False

    def test_keys_error_returns_empty(self, failing_backend):
        """keys() returns empty list on AMS error."""
        assert failing_backend.keys() == []

    def test_get_stats_error_returns_partial(self, failing_backend):
        """get_stats() returns dict with connected=False on error."""
        stats = failing_backend.get_stats()
        assert stats["connected"] is False
        assert stats["mode"] == "ams"

    def test_close_error_does_not_raise(self, failing_backend):
        """close() catches errors during cleanup."""
        failing_backend.close()  # Should not raise
        assert failing_backend._closed is True

    def test_search_error_returns_empty(self, failing_backend):
        """search() returns empty list on AMS error."""
        assert failing_backend.search("query") == []

    def test_promote_error_returns_false(self, failing_backend):
        """promote() returns False on AMS error."""
        assert failing_backend.promote() is False


class TestRetrieveNoneData:
    """Cover retrieve() when response.data is None."""

    def test_retrieve_returns_none_when_data_is_none(self, redis_config):
        """retrieve() returns None when AMS returns empty data."""
        from attune_redis.tests.conftest import FakeWorkingMemoryResponse

        with patch("agent_memory_client.MemoryAPIClient") as mock_cls:
            client = AsyncMock()

            async def _get_or_create_wm(**kwargs):
                # retrieve() reads via get_or_create_working_memory, which
                # returns (created, WorkingMemory); exercise the data=None branch.
                return (False, FakeWorkingMemoryResponse(data=None))

            client.get_or_create_working_memory.side_effect = _get_or_create_wm
            mock_cls.return_value = client

            b = AMSMemoryBackend(config=redis_config)
            b._client = client
            assert b.retrieve("any-key") is None


# =================================================================
# MCP tool handler error paths (mcp_tools.py exception branches)
# =================================================================


class TestMCPHandlerExceptionPaths:
    """Cover the except Exception branches in each handler."""

    @pytest.fixture()
    def error_server(self):
        """Server with backend that raises RuntimeError."""
        server = MagicMock()
        backend = MagicMock()
        backend.stash.side_effect = RuntimeError("boom")
        backend.retrieve.side_effect = RuntimeError("boom")
        backend.search.side_effect = RuntimeError("boom")
        backend.promote.side_effect = RuntimeError("boom")
        backend.is_connected.side_effect = RuntimeError("boom")
        server._redis_backend = backend
        return server

    @pytest.mark.asyncio()
    async def test_store_exception_returns_error(self, error_server):
        """Store handler catches RuntimeError."""
        result = await handle_redis_memory_store(error_server, {"key": "k", "value": "v"})
        assert result["success"] is False
        assert "boom" in result["error"]

    @pytest.mark.asyncio()
    async def test_retrieve_exception_returns_error(self, error_server):
        """Retrieve handler catches RuntimeError."""
        result = await handle_redis_memory_retrieve(error_server, {"key": "k"})
        assert result["success"] is False
        assert "boom" in result["error"]

    @pytest.mark.asyncio()
    async def test_search_exception_returns_error(self, error_server):
        """Search handler catches RuntimeError."""
        result = await handle_redis_memory_search(error_server, {"query": "test"})
        assert result["success"] is False
        assert "boom" in result["error"]

    @pytest.mark.asyncio()
    async def test_promote_exception_returns_error(self, error_server):
        """Promote handler catches RuntimeError."""
        result = await handle_redis_memory_promote(error_server, {})
        assert result["success"] is False
        assert "boom" in result["error"]

    @pytest.mark.asyncio()
    async def test_health_check_exception_returns_error(self, error_server):
        """Health check handler catches RuntimeError."""
        result = await handle_redis_health_check(error_server, {})
        assert result["success"] is False
        assert "boom" in result["error"]


class TestMCPHandlerImportErrorPaths:
    """Cover the except ImportError branches in each handler."""

    @pytest.fixture()
    def import_error_server(self):
        """Server where _get_backend raises ImportError."""
        server = MagicMock(spec=[])
        return server

    @pytest.mark.asyncio()
    async def test_retrieve_import_error(self, import_error_server):
        """Retrieve returns install hint on ImportError."""
        with patch(
            "attune_redis.mcp_tools._get_backend",
            side_effect=ImportError("no module"),
        ):
            result = await handle_redis_memory_retrieve(import_error_server, {"key": "k"})
        assert result["success"] is False
        # New contract (#1420): the deps are core, so the error names a
        # broken install and a remediation that can actually work.
        assert "not importable" in result["error"]
        assert "attune-ai[" not in result["error"]

    @pytest.mark.asyncio()
    async def test_search_import_error(self, import_error_server):
        """Search returns install hint on ImportError."""
        with patch(
            "attune_redis.mcp_tools._get_backend",
            side_effect=ImportError("no module"),
        ):
            result = await handle_redis_memory_search(import_error_server, {"query": "test"})
        assert result["success"] is False
        # New contract (#1420): the deps are core, so the error names a
        # broken install and a remediation that can actually work.
        assert "not importable" in result["error"]
        assert "attune-ai[" not in result["error"]

    @pytest.mark.asyncio()
    async def test_promote_import_error(self, import_error_server):
        """Promote returns install hint on ImportError."""
        with patch(
            "attune_redis.mcp_tools._get_backend",
            side_effect=ImportError("no module"),
        ):
            result = await handle_redis_memory_promote(import_error_server, {})
        assert result["success"] is False
        # New contract (#1420): the deps are core, so the error names a
        # broken install and a remediation that can actually work.
        assert "not importable" in result["error"]
        assert "attune-ai[" not in result["error"]

    @pytest.mark.asyncio()
    async def test_health_check_import_error(self, import_error_server):
        """Health check returns install hint on ImportError."""
        with patch(
            "attune_redis.mcp_tools._get_backend",
            side_effect=ImportError("no module"),
        ):
            result = await handle_redis_health_check(import_error_server, {})
        assert result["success"] is False
        # New contract (#1420): the deps are core, so the error names a
        # broken install and a remediation that can actually work.
        assert "not importable" in result["error"]
        assert "attune-ai[" not in result["error"]


# =================================================================
# plugin.py error paths (lines 77-81, 89-90)
# =================================================================


class TestPluginErrorPaths:
    """Cover RedisPlugin error branches."""

    def test_register_mcp_tools_import_error(self):
        """register_mcp_tools catches ImportError gracefully."""
        from attune_redis.plugin import RedisPlugin

        plugin = RedisPlugin()
        server = MagicMock()

        with patch(
            "attune_redis.mcp_tools.register_tools",
            side_effect=ImportError("mcp not available"),
        ):
            # Should not raise — catches ImportError
            plugin.register_mcp_tools(server)

    def test_register_mcp_tools_generic_error(self):
        """register_mcp_tools catches unexpected errors."""
        from attune_redis.plugin import RedisPlugin

        plugin = RedisPlugin()
        server = MagicMock()

        with patch(
            "attune_redis.mcp_tools.register_tools",
            side_effect=RuntimeError("unexpected"),
        ):
            # Should not raise — catches Exception
            plugin.register_mcp_tools(server)

    def test_on_activate_missing_dependency(self):
        """on_activate warns when agent-memory-client missing."""
        from attune_redis.plugin import RedisPlugin

        plugin = RedisPlugin()

        with patch.dict("sys.modules", {"agent_memory_client": None}):
            # Should not raise — logs warning
            plugin.on_activate()
