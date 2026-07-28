"""Tests for Redis MCP tool definitions and handlers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune_redis.mcp_tools import (
    SESSION_MEMORY_TOOL_DEFINITIONS,
    SESSION_MEMORY_TOOL_HANDLERS,
    TOOL_DEFINITIONS,
    TOOL_HANDLERS,
    handle_redis_health_check,
    handle_redis_memory_promote,
    handle_redis_memory_retrieve,
    handle_redis_memory_search,
    handle_redis_memory_store,
    handle_session_memory_capture,
    handle_session_memory_forget,
    handle_session_memory_recall,
    handle_session_memory_recent,
    handle_session_memory_status,
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


class TestLegacySchemaFreeze:
    """D6: the 6 redis_memory_* schemas are FROZEN public surfaces.

    session_memory_* tools are additive; any change to the shapes below
    requires versioning and a changelog entry, not an in-place edit.
    """

    FROZEN = {
        "redis_memory_store": (["key", "value"], {"key", "value", "session_id"}),
        "redis_memory_retrieve": (["key"], {"key", "session_id"}),
        "redis_memory_search": (["query"], {"query", "limit"}),
        "redis_memory_forget": (["ids"], {"ids"}),
        "redis_memory_promote": ([], {"session_id"}),
        "redis_health_check": ([], set()),
    }

    def test_legacy_tools_unchanged(self):
        assert set(TOOL_DEFINITIONS) == set(self.FROZEN)
        for name, (required, properties) in self.FROZEN.items():
            schema = TOOL_DEFINITIONS[name]["input_schema"]
            assert schema["required"] == required, f"{name} required drifted"
            assert set(schema["properties"]) == properties, f"{name} properties drifted"

    def test_no_session_tools_in_legacy_dict(self):
        """Additive tools live in their own dict; TOOL_DEFINITIONS stays 6."""
        assert not any(n.startswith("session_memory") for n in TOOL_DEFINITIONS)


class TestSessionMemoryToolDefinitions:
    """The 5 additive session_memory_* tools (cross-provider T2)."""

    def test_five_tools_defined(self):
        assert len(SESSION_MEMORY_TOOL_DEFINITIONS) == 5

    @pytest.mark.parametrize("tool_name", sorted(SESSION_MEMORY_TOOL_DEFINITIONS))
    def test_tool_has_required_fields(self, tool_name):
        tool = SESSION_MEMORY_TOOL_DEFINITIONS[tool_name]
        assert tool["name"] == tool_name
        assert len(tool["description"]) > 10
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema

    def test_capture_requires_content_and_bounds_type(self):
        schema = SESSION_MEMORY_TOOL_DEFINITIONS["session_memory_capture"]["input_schema"]
        assert schema["required"] == ["content"]
        assert set(schema["properties"]["type"]["enum"]) == {
            "decision",
            "pattern",
            "bug",
            "reference",
            "note",
        }

    def test_recall_requires_query(self):
        schema = SESSION_MEMORY_TOOL_DEFINITIONS["session_memory_recall"]["input_schema"]
        assert schema["required"] == ["query"]

    def test_forget_requires_ids(self):
        schema = SESSION_MEMORY_TOOL_DEFINITIONS["session_memory_forget"]["input_schema"]
        assert schema["required"] == ["ids"]
        assert schema["properties"]["ids"]["type"] == "array"

    def test_handlers_match_definitions(self):
        assert set(SESSION_MEMORY_TOOL_HANDLERS) == set(SESSION_MEMORY_TOOL_DEFINITIONS)

    def test_handlers_are_coroutines(self):
        import asyncio

        for name, handler in SESSION_MEMORY_TOOL_HANDLERS.items():
            assert asyncio.iscoroutinefunction(handler), f"{name} is not async"


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
# Session-memory handler unit tests (session_stash patched at its module)
# =========================================================================


class TestHandleSessionCapture:
    """session_memory_capture delegates to the sanitizing stash contract."""

    @pytest.mark.asyncio()
    async def test_capture_success_returns_id(self, mock_server):
        with patch("attune.memory.session_stash.stash_entry", return_value=True) as stash:
            result = await handle_session_memory_capture(
                mock_server,
                {"content": "a finding", "type": "bug", "cwd": "/proj"},
            )
        assert result["ok"] is True
        assert len(result["id"]) == 36  # uuid4 — usable for later forget
        assert result["source"] == "session-stash"
        entry = stash.call_args.args[0]
        assert entry.type == "bug"
        assert entry.cwd == "/proj"

    @pytest.mark.asyncio()
    async def test_capture_defaults_cwd_to_workspace_root(self, mock_server):
        mock_server._workspace_root = "/workspace"
        with patch("attune.memory.session_stash.stash_entry", return_value=True) as stash:
            await handle_session_memory_capture(mock_server, {"content": "x"})
        entry = stash.call_args.args[0]
        assert entry.cwd == "/workspace"
        assert entry.type == "note"
        assert entry.session_id == "mcp"

    @pytest.mark.asyncio()
    async def test_false_write_maps_to_ok_false_with_stable_reason(self, mock_server):
        """CR-5: a Python False result is NEVER reported as success; the
        caller-scoped status reason is surfaced as a stable code."""
        with (
            patch("attune.memory.session_stash.stash_entry", return_value=False),
            patch(
                "attune.memory.session_stash.backend_status",
                return_value={"ok": False, "reason": "file_write_denied"},
            ),
        ):
            result = await handle_session_memory_capture(mock_server, {"content": "x"})
        assert result["ok"] is False
        assert result["reason"] == "file_write_denied"

    @pytest.mark.asyncio()
    async def test_false_write_without_status_reason_is_write_failed(self, mock_server):
        with (
            patch("attune.memory.session_stash.stash_entry", return_value=False),
            patch(
                "attune.memory.session_stash.backend_status",
                return_value={"ok": True, "reason": None},
            ),
        ):
            result = await handle_session_memory_capture(mock_server, {"content": "x"})
        assert result["ok"] is False
        assert result["reason"] == "write_failed"

    @pytest.mark.asyncio()
    async def test_invalid_type_rejected_without_write(self, mock_server):
        with patch("attune.memory.session_stash.stash_entry") as stash:
            result = await handle_session_memory_capture(
                mock_server, {"content": "x", "type": "nonsense"}
            )
        assert result["ok"] is False
        assert result["reason"] == "invalid_entry"
        stash.assert_not_called()

    @pytest.mark.asyncio()
    async def test_empty_content_rejected(self, mock_server):
        result = await handle_session_memory_capture(mock_server, {"content": "   "})
        assert result["ok"] is False
        assert result["reason"] == "invalid_entry"


class TestHandleSessionRecall:
    """session_memory_recall / recent delegate with bounded top_k."""

    @pytest.mark.asyncio()
    async def test_recall_returns_results(self, mock_server):
        hits = [{"id": "m1", "text": "found"}]
        with patch("attune.memory.session_stash.recall_entries", return_value=hits) as recall:
            result = await handle_session_memory_recall(
                mock_server, {"query": "parser", "cwd": "/proj"}
            )
        assert result["ok"] is True
        assert result["count"] == 1
        recall.assert_called_once_with("parser", top_k=5, cwd="/proj")

    @pytest.mark.asyncio()
    async def test_recall_clamps_top_k(self, mock_server):
        with patch("attune.memory.session_stash.recall_entries", return_value=[]) as recall:
            await handle_session_memory_recall(mock_server, {"query": "q", "top_k": 999})
        assert recall.call_args.kwargs["top_k"] == 20

    @pytest.mark.asyncio()
    async def test_recent_returns_results(self, mock_server):
        with patch("attune.memory.session_stash.recent_entries", return_value=[]) as recent:
            result = await handle_session_memory_recent(mock_server, {"top_k": 3})
        assert result["ok"] is True
        recent.assert_called_once_with(top_k=3, cwd=None)


class TestHandleSessionForget:
    """session_memory_forget delegates to precise deletion."""

    @pytest.mark.asyncio()
    async def test_forget_deletes_by_id(self, mock_server):
        with patch("attune.memory.session_stash.forget_entries", return_value=2) as forget:
            result = await handle_session_memory_forget(
                mock_server, {"ids": ["a", "b"], "cwd": "/proj"}
            )
        assert result["ok"] is True
        assert result["deleted"] == 2
        forget.assert_called_once_with(["a", "b"], source="mcp_forget", cwd="/proj")

    @pytest.mark.asyncio()
    async def test_forget_zero_deleted_reports_not_found(self, mock_server):
        with (
            patch("attune.memory.session_stash.forget_entries", return_value=0),
            patch(
                "attune.memory.session_stash.backend_status",
                return_value={"ok": True, "reason": None},
            ),
        ):
            result = await handle_session_memory_forget(mock_server, {"ids": ["gone"]})
        assert result["ok"] is False
        assert result["reason"] == "not_found"

    @pytest.mark.asyncio()
    async def test_forget_rejects_non_string_ids(self, mock_server):
        result = await handle_session_memory_forget(mock_server, {"ids": [1, 2]})
        assert result["ok"] is False
        assert result["reason"] == "invalid_entry"


class TestHandleSessionStatus:
    """session_memory_status layers the MCP transport over backend_status."""

    @pytest.mark.asyncio()
    async def test_status_reports_mcp_transport_layer(self, mock_server):
        underlying = {
            "backend": "FileStashBackend",
            "fallback": True,
            "unreachable_upgrade": None,
            "ok": True,
            "transport": "file",
            "reachability": "reachable",
            "reason": None,
        }
        with patch("attune.memory.session_stash.backend_status", return_value=underlying):
            result = await handle_session_memory_status(mock_server, {})
        assert result["transport"] == "mcp"
        assert result["backend_transport"] == "file"
        assert result["ok"] is True
        assert result["backend"] == "FileStashBackend"

    @pytest.mark.asyncio()
    async def test_status_surfaces_denial_reason(self, mock_server):
        underlying = {
            "backend": "FileStashBackend",
            "fallback": True,
            "unreachable_upgrade": "redis",
            "ok": False,
            "transport": "file",
            "reachability": "unreachable_local",
            "reason": "file_write_denied",
        }
        with patch("attune.memory.session_stash.backend_status", return_value=underlying):
            result = await handle_session_memory_status(mock_server, {})
        assert result["ok"] is False
        assert result["reason"] == "file_write_denied"
        assert result["reachability"] == "unreachable_local"


class TestSessionMemoryVoiceSummaries:
    """Each verb voices its own action-appropriate summary.

    Regression guard for the receipt-4 canary bug (2026-07-27): every
    session_memory_* verb answered with the generic recall greeting
    "Here's what I found." because the shared voice layer stamped
    GREETING_SUCCESS over responses that carried no summary of their own.
    """

    GENERIC_GREETING = "Here's what I found."

    @pytest.mark.asyncio()
    async def test_capture_voices_stashing(self, mock_server):
        with patch("attune.memory.session_stash.stash_entry", return_value=True):
            result = await handle_session_memory_capture(mock_server, {"content": "a finding"})
        assert result["voice_summary"] == "Stashed that finding for future recall."

    @pytest.mark.asyncio()
    async def test_capture_failure_voices_the_reason(self, mock_server):
        with (
            patch("attune.memory.session_stash.stash_entry", return_value=False),
            patch(
                "attune.memory.session_stash.backend_status",
                return_value={"ok": False, "reason": "file_write_denied"},
            ),
        ):
            result = await handle_session_memory_capture(mock_server, {"content": "x"})
        assert result["voice_summary"] == "Couldn't stash that finding (file_write_denied)."

    @pytest.mark.asyncio()
    async def test_recall_voices_hit_count(self, mock_server):
        hits = [{"id": "m1", "text": "found"}]
        with patch("attune.memory.session_stash.recall_entries", return_value=hits):
            result = await handle_session_memory_recall(mock_server, {"query": "parser"})
        assert result["voice_summary"] == "Found 1 stashed finding."

    @pytest.mark.asyncio()
    async def test_recall_empty_voices_no_match(self, mock_server):
        with patch("attune.memory.session_stash.recall_entries", return_value=[]):
            result = await handle_session_memory_recall(mock_server, {"query": "nope"})
        assert result["voice_summary"] == "No stashed findings matched that query."

    @pytest.mark.asyncio()
    async def test_recent_voices_singular_and_empty(self, mock_server):
        one = [{"id": "m1"}]
        with patch("attune.memory.session_stash.recent_entries", return_value=one):
            result = await handle_session_memory_recent(mock_server, {})
        assert result["voice_summary"] == "Here is the most recent stashed finding."

        with patch("attune.memory.session_stash.recent_entries", return_value=[]):
            result = await handle_session_memory_recent(mock_server, {})
        assert result["voice_summary"] == "Nothing stashed yet for this project."

    @pytest.mark.asyncio()
    async def test_forget_voices_deletion_counts(self, mock_server):
        with patch("attune.memory.session_stash.forget_entries", return_value=2):
            result = await handle_session_memory_forget(mock_server, {"ids": ["a", "b"]})
        assert result["voice_summary"] == "Deleted 2 of 2 stashed records."

    @pytest.mark.asyncio()
    async def test_forget_not_found_voices_failure(self, mock_server):
        with (
            patch("attune.memory.session_stash.forget_entries", return_value=0),
            patch(
                "attune.memory.session_stash.backend_status",
                return_value={"ok": True, "reason": None},
            ),
        ):
            result = await handle_session_memory_forget(mock_server, {"ids": ["gone"]})
        assert result["voice_summary"] == "Couldn't delete those records (not_found)."

    @pytest.mark.asyncio()
    async def test_status_voices_backend_readiness(self, mock_server):
        underlying = {
            "backend": "FileStashBackend",
            "ok": True,
            "transport": "file",
            "reason": None,
        }
        with patch("attune.memory.session_stash.backend_status", return_value=underlying):
            result = await handle_session_memory_status(mock_server, {})
        assert result["voice_summary"] == "Session memory is ready (FileStashBackend backend)."

        underlying = {"backend": None, "ok": False, "transport": "none", "reason": "no_backend"}
        with patch("attune.memory.session_stash.backend_status", return_value=underlying):
            result = await handle_session_memory_status(mock_server, {})
        assert result["voice_summary"] == "Session memory is unavailable (no_backend)."

    @pytest.mark.asyncio()
    async def test_no_verb_uses_the_generic_recall_greeting(self, mock_server):
        """The canary assertion: no session_memory verb ever says
        "Here's what I found." — that phrasing only fits recall, and
        recall now phrases its own count."""
        with patch("attune.memory.session_stash.stash_entry", return_value=True):
            capture = await handle_session_memory_capture(mock_server, {"content": "x"})
        with patch("attune.memory.session_stash.recall_entries", return_value=[]):
            recall = await handle_session_memory_recall(mock_server, {"query": "q"})
        with patch("attune.memory.session_stash.recent_entries", return_value=[]):
            recent = await handle_session_memory_recent(mock_server, {})
        with patch("attune.memory.session_stash.forget_entries", return_value=1):
            forget = await handle_session_memory_forget(mock_server, {"ids": ["a"]})
        with patch(
            "attune.memory.session_stash.backend_status",
            return_value={"ok": True, "backend": "FileStashBackend"},
        ):
            status = await handle_session_memory_status(mock_server, {})
        for result in (capture, recall, recent, forget, status):
            assert result["voice_summary"] != self.GENERIC_GREETING


# =========================================================================
# Registration integration
# =========================================================================


class TestRegisterTools:
    """Test register_tools() wiring."""

    def test_registers_tool_definitions(self):
        """register_tools adds the 6 redis + 5 session tools (attune core
        is importable in the test environment)."""
        server = MagicMock()
        server.tools = {}
        server._plugin_handlers = {}

        register_tools(server)

        assert len(server.tools) == 11
        assert "redis_memory_store" in server.tools
        assert "redis_health_check" in server.tools
        assert "session_memory_capture" in server.tools

    def test_registers_handlers(self):
        """register_tools adds handlers to dispatch table."""
        server = MagicMock()
        server.tools = {}
        server._plugin_handlers = {}

        register_tools(server)

        assert len(server._plugin_handlers) == 11
        assert "redis_memory_store" in server._plugin_handlers
        assert "session_memory_status" in server._plugin_handlers

    def test_session_tools_skipped_without_attune_core(self):
        """Conditional registration: a partial environment gets only the
        6 redis tools, never session tools that can only fail."""
        server = MagicMock()
        server.tools = {}
        server._plugin_handlers = {}

        with patch("attune_redis.mcp_tools._session_memory_available", return_value=False):
            register_tools(server)

        assert len(server.tools) == 6
        assert "session_memory_capture" not in server.tools
        assert "session_memory_capture" not in server._plugin_handlers

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
