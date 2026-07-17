"""Tests for Redis MCP tool definitions and handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune_redis.mcp_tools import (
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    handle_redis_health_check,
    handle_redis_memory_promote,
    handle_redis_memory_retrieve,
    handle_redis_memory_search,
    handle_redis_memory_store,
    register_tools,
)

# =========================================================================
# Tool schema validation
# =========================================================================


class TestToolDefinitions:
    """Verify all 6 tools have valid JSON schemas."""

    def test_six_tools_defined(self):
        """Exactly 6 tools must be defined."""
        assert len(TOOL_DEFINITIONS) == 6

    @pytest.mark.parametrize(
        "tool_name",
        [
            "redis_memory_store",
            "redis_memory_retrieve",
            "redis_memory_search",
            "redis_memory_forget",
            "redis_memory_promote",
            "redis_health_check",
        ],
    )
    def test_tool_has_required_fields(self, tool_name):
        """Each tool must have name, description, input_schema."""
        tool = TOOL_DEFINITIONS[tool_name]
        assert tool["name"] == tool_name
        assert "description" in tool
        assert len(tool["description"]) > 10
        assert "input_schema" in tool

    @pytest.mark.parametrize(
        "tool_name",
        [
            "redis_memory_store",
            "redis_memory_retrieve",
            "redis_memory_search",
            "redis_memory_forget",
            "redis_memory_promote",
            "redis_health_check",
        ],
    )
    def test_schema_is_valid_json_schema(self, tool_name):
        """Each input_schema must be a valid JSON Schema object."""
        schema = TOOL_DEFINITIONS[tool_name]["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_store_requires_key_and_value(self):
        """redis_memory_store must require key and value."""
        schema = TOOL_DEFINITIONS["redis_memory_store"]["input_schema"]
        assert "key" in schema["required"]
        assert "value" in schema["required"]

    def test_retrieve_requires_key(self):
        """redis_memory_retrieve must require key."""
        schema = TOOL_DEFINITIONS["redis_memory_retrieve"]["input_schema"]
        assert "key" in schema["required"]

    def test_search_requires_query(self):
        """redis_memory_search must require query."""
        schema = TOOL_DEFINITIONS["redis_memory_search"]["input_schema"]
        assert "query" in schema["required"]

    def test_forget_requires_ids(self):
        """redis_memory_forget must require ids (array of strings)."""
        schema = TOOL_DEFINITIONS["redis_memory_forget"]["input_schema"]
        assert schema["required"] == ["ids"]
        assert schema["properties"]["ids"]["type"] == "array"


class TestToolHandlers:
    """Verify handler dispatch table matches definitions."""

    def test_six_handlers(self):
        """Exactly 6 handlers must be registered."""
        assert len(TOOL_HANDLERS) == 6

    def test_handlers_match_definitions(self):
        """Every defined tool must have a handler."""
        for tool_name in TOOL_DEFINITIONS:
            assert tool_name in TOOL_HANDLERS, f"Missing handler for {tool_name}"

    def test_handlers_are_coroutines(self):
        """All handlers must be async functions."""
        import asyncio

        for name, handler in TOOL_HANDLERS.items():
            assert asyncio.iscoroutinefunction(handler), f"{name} is not async"


# =========================================================================
# Handler unit tests (mocked AMSMemoryBackend)
# =========================================================================


@pytest.fixture()
def mock_server():
    """Create a mock MCP server with mocked Redis backend."""
    server = MagicMock()
    server._plugin_handlers = {}

    backend = MagicMock()
    backend.stash.return_value = True
    backend.retrieve.return_value = "test-value"
    backend.search.return_value = [{"id": "m1", "text": "result1", "topics": [], "entities": []}]
    backend.promote.return_value = True
    backend.is_connected.return_value = True
    backend.get_stats.return_value = {"mode": "ams", "connected": True}

    server._redis_backend = backend
    return server


class TestHandleStore:
    """Test redis_memory_store handler."""

    @pytest.mark.asyncio()
    async def test_store_success(self, mock_server):
        """Store returns success with key."""
        result = await handle_redis_memory_store(mock_server, {"key": "k1", "value": {"data": 1}})
        assert result["success"] is True
        assert result["key"] == "k1"
        assert result["source"] == "redis-ams"
        mock_server._redis_backend.stash.assert_called_once_with("k1", {"data": 1}, agent_id=None)

    @pytest.mark.asyncio()
    async def test_store_with_session_id(self, mock_server):
        """Store passes session_id as agent_id."""
        await handle_redis_memory_store(
            mock_server, {"key": "k1", "value": "v", "session_id": "s1"}
        )
        mock_server._redis_backend.stash.assert_called_once_with("k1", "v", agent_id="s1")

    @pytest.mark.asyncio()
    async def test_store_import_error(self):
        """Store returns error when redis libs are not importable."""
        server = MagicMock(spec=[])
        del server._redis_backend
        with patch(
            "attune_redis.mcp_tools._get_backend",
            side_effect=ImportError("no module"),
        ):
            result = await handle_redis_memory_store(server, {"key": "k", "value": "v"})
        assert result["success"] is False
        # New contract (#1420): the deps are core, so the error names a
        # broken install and a remediation that can actually work.
        assert "not importable" in result["error"]
        assert "attune-ai[" not in result["error"]


class TestHandleRetrieve:
    """Test redis_memory_retrieve handler."""

    @pytest.mark.asyncio()
    async def test_retrieve_found(self, mock_server):
        """Retrieve returns value when found."""
        result = await handle_redis_memory_retrieve(mock_server, {"key": "k1"})
        assert result["success"] is True
        assert result["value"] == "test-value"
        assert result["found"] is True

    @pytest.mark.asyncio()
    async def test_retrieve_missing(self, mock_server):
        """Retrieve returns found=False when key missing."""
        mock_server._redis_backend.retrieve.return_value = None
        result = await handle_redis_memory_retrieve(mock_server, {"key": "missing"})
        assert result["success"] is True
        assert result["found"] is False
        assert result["value"] is None


class TestHandleSearch:
    """Test redis_memory_search handler."""

    @pytest.mark.asyncio()
    async def test_search_returns_results(self, mock_server):
        """Search returns matching memories."""
        result = await handle_redis_memory_search(mock_server, {"query": "test query"})
        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["results"]) == 1

    @pytest.mark.asyncio()
    async def test_search_with_limit(self, mock_server):
        """Search passes limit to backend."""
        await handle_redis_memory_search(mock_server, {"query": "test", "limit": 5})
        mock_server._redis_backend.search.assert_called_once_with("test", limit=5)


class TestHandlePromote:
    """Test redis_memory_promote handler."""

    @pytest.mark.asyncio()
    async def test_promote_success(self, mock_server):
        """Promote returns success."""
        result = await handle_redis_memory_promote(mock_server, {})
        assert result["success"] is True

    @pytest.mark.asyncio()
    async def test_promote_with_session(self, mock_server):
        """Promote passes session_id."""
        await handle_redis_memory_promote(mock_server, {"session_id": "s1"})
        mock_server._redis_backend.promote.assert_called_once_with(session_id="s1")


class TestHandleHealthCheck:
    """Test redis_health_check handler."""

    @pytest.mark.asyncio()
    async def test_health_check_success(self, mock_server):
        """Health check returns connected status."""
        result = await handle_redis_health_check(mock_server, {})
        assert result["success"] is True
        assert result["connected"] is True
        assert result["stats"]["mode"] == "ams"


# =========================================================================
# Registration integration
# =========================================================================


class TestRegisterTools:
    """Test register_tools() wiring."""

    def test_registers_tool_definitions(self):
        """register_tools adds all 5 tools to server."""
        server = MagicMock()
        server.tools = {}
        server._plugin_handlers = {}

        register_tools(server)

        assert len(server.tools) == 6
        assert "redis_memory_store" in server.tools
        assert "redis_health_check" in server.tools

    def test_registers_handlers(self):
        """register_tools adds handlers to dispatch table."""
        server = MagicMock()
        server.tools = {}
        server._plugin_handlers = {}

        register_tools(server)

        assert len(server._plugin_handlers) == 6
        assert "redis_memory_store" in server._plugin_handlers

    def test_creates_plugin_handlers_if_missing(self):
        """register_tools creates _plugin_handlers if not present."""
        server = MagicMock(spec=[])
        server.tools = {}

        register_tools(server)

        assert hasattr(server, "_plugin_handlers")


class TestRedisPluginMCPRegistration:
    """Test RedisPlugin.register_mcp_tools() integration."""

    def test_plugin_registers_tools(self):
        """RedisPlugin.register_mcp_tools adds tools to server."""
        from attune_redis.plugin import RedisPlugin

        server = MagicMock()
        server.tools = {}
        server._plugin_handlers = {}

        plugin = RedisPlugin()
        plugin.register_mcp_tools(server)

        assert "redis_memory_store" in server.tools
        assert "redis_health_check" in server._plugin_handlers
