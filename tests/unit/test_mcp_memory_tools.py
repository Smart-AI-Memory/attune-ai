"""Unit tests for MCP memory and context tools.

Tests the MCP tools on AttuneMCPServer:
- memory_store, memory_retrieve, memory_search, memory_forget
- context_get, context_set

Copyright 2025 Smart AI Memory, LLC
Licensed under Apache 2.0
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer


@pytest.fixture
def server():
    """Create an AttuneMCPServer instance for testing."""
    with patch("attune.mcp.version_check.check_for_updates", return_value=None):
        return AttuneMCPServer()


class TestToolRegistration:
    """Verify all core, workspace, and optional Redis tools are registered."""

    def test_tools_list_returns_at_least_core_count(self, server: AttuneMCPServer):
        """Core tools (48) are always registered; attune-redis adds 6 more."""
        tools = server.get_tool_list()
        tool_names = {t["name"] for t in tools}

        # The shared renderer adds three generic workspace tools to the
        # previous 48-tool core surface.
        workspace_tools = {
            "command_workspace_open",
            "command_workspace_collect_action",
            "command_workspace_publish",
        }
        assert len(tools) >= 51
        assert workspace_tools.issubset(tool_names)

        # When attune-redis plugin is installed, all 6 redis tools are present
        redis_tools = {
            "redis_health_check",
            "redis_memory_forget",
            "redis_memory_promote",
            "redis_memory_retrieve",
            "redis_memory_search",
            "redis_memory_store",
        }
        if redis_tools.issubset(tool_names):
            # attune-redis also registers 5 session_memory_* tools when the
            # core session stash is importable (conditional registration).
            expected = 64 if "session_memory_status" in tool_names else 59
            assert (
                len(tools) == expected
            ), f"Expected {expected} tools with redis plugin, got {len(tools)}"

    def test_memory_tools_registered(self, server: AttuneMCPServer):
        """Test that all memory tools are in the tool list."""
        tool_names = {t["name"] for t in server.get_tool_list()}
        expected_memory_tools = {
            "memory_store",
            "memory_retrieve",
            "memory_search",
            "memory_forget",
        }
        assert expected_memory_tools.issubset(tool_names)

    def test_context_tools_registered(self, server: AttuneMCPServer):
        """Test that context tools are in the tool list."""
        tool_names = {t["name"] for t in server.get_tool_list()}
        assert "context_get" in tool_names
        assert "context_set" in tool_names

    def test_memory_store_schema(self, server: AttuneMCPServer):
        """Test that memory_store has correct input schema."""
        tool = server.tools["memory_store"]
        schema = tool["input_schema"]
        assert "key" in schema["properties"]
        assert "value" in schema["properties"]
        assert "classification" in schema["properties"]
        assert schema["properties"]["classification"]["enum"] == ["PUBLIC", "INTERNAL", "SENSITIVE"]
        assert schema["required"] == ["key", "value"]


class TestContextTools:
    """Test context get/set operations."""

    @pytest.mark.asyncio
    async def test_context_get_set_roundtrip(self, server: AttuneMCPServer):
        """Test that context_set and context_get round-trip values."""
        await server.call_tool("context_set", {"key": "project", "value": "attune-ai"})
        result = await server.call_tool("context_get", {"key": "project"})
        assert result["success"] is True
        assert result["value"] == "attune-ai"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_context_get_missing_key(self, server: AttuneMCPServer):
        """Test that context_get returns found=False for missing keys."""
        result = await server.call_tool("context_get", {"key": "nonexistent"})
        assert result["success"] is True
        assert result["value"] is None
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_context_set_overwrites(self, server: AttuneMCPServer):
        """Test that context_set overwrites existing values."""
        await server.call_tool("context_set", {"key": "mode", "value": "development"})
        await server.call_tool("context_set", {"key": "mode", "value": "production"})
        result = await server.call_tool("context_get", {"key": "mode"})
        assert result["value"] == "production"

    @pytest.mark.asyncio
    async def test_context_multiple_keys(self, server: AttuneMCPServer):
        """Test storing and retrieving multiple context keys."""
        keys = {"a": "1", "b": "2", "c": "3"}
        for key, value in keys.items():
            await server.call_tool("context_set", {"key": key, "value": value})
        for key, expected in keys.items():
            result = await server.call_tool("context_get", {"key": key})
            assert result["value"] == expected


class TestMemoryToolsWithMock:
    """Test memory tools with mocked UnifiedMemory."""

    @pytest.mark.asyncio
    async def test_memory_store_basic(self, server: AttuneMCPServer):
        """Test basic memory_store operation."""
        mock_memory = MagicMock()
        mock_memory.persist_pattern.return_value = {"pattern_id": "test-123"}
        server._memory = mock_memory

        result = await server.call_tool(
            "memory_store",
            {
                "key": "test-key",
                "value": "test-value",
            },
        )
        assert result["success"] is True
        assert result["key"] == "test-key"
        assert result["classification"] == "PUBLIC"
        mock_memory.stash.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_store_with_classification(self, server: AttuneMCPServer):
        """Test memory_store with SENSITIVE classification."""
        mock_memory = MagicMock()
        mock_memory.persist_pattern.return_value = {"pattern_id": "sensitive-123"}
        server._memory = mock_memory

        result = await server.call_tool(
            "memory_store",
            {
                "key": "secret-key",
                "value": "sensitive-data",
                "classification": "SENSITIVE",
                "pattern_type": "credential",
            },
        )
        assert result["success"] is True
        assert result["classification"] == "SENSITIVE"
        assert "pattern_id" in result

    @pytest.mark.asyncio
    async def test_memory_retrieve_found(self, server: AttuneMCPServer):
        """Test memory_retrieve when key exists in short-term."""
        mock_memory = MagicMock()
        mock_memory.retrieve.return_value = {"value": "found-data", "classification": "PUBLIC"}
        server._memory = mock_memory

        result = await server.call_tool("memory_retrieve", {"key": "existing-key"})
        assert result["success"] is True
        assert result["data"] is not None
        assert result["source"] == "short_term"

    @pytest.mark.asyncio
    async def test_memory_retrieve_missing_key(self, server: AttuneMCPServer):
        """Test memory_retrieve when key does not exist."""
        mock_memory = MagicMock()
        mock_memory.retrieve.return_value = None
        mock_memory.recall_pattern.return_value = None
        server._memory = mock_memory

        result = await server.call_tool("memory_retrieve", {"key": "missing-key"})
        assert result["success"] is True
        assert result["data"] is None
        assert "not found" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_memory_search_matches(self, server: AttuneMCPServer):
        """Test memory_search returns matching patterns."""
        mock_memory = MagicMock()
        mock_memory.search_patterns = MagicMock(
            return_value=[
                {"key": "pattern-1", "value": "test match"},
                {"key": "pattern-2", "value": "another match"},
            ],
        )
        server._memory = mock_memory

        result = await server.call_tool("memory_search", {"query": "match"})
        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_memory_forget_removes(self, server: AttuneMCPServer):
        """Test memory_forget removes data."""
        mock_memory = MagicMock()
        mock_memory.delete_pattern = MagicMock()
        server._memory = mock_memory

        result = await server.call_tool("memory_forget", {"key": "old-key"})
        assert result["success"] is True
        assert result["key"] == "old-key"

    @pytest.mark.asyncio
    async def test_memory_store_import_error(self, server: AttuneMCPServer):
        """Test memory_store handles ImportError gracefully."""
        server._memory = None  # Force lazy init

        with patch.object(
            server,
            "_get_memory",
            side_effect=ImportError("No memory module"),
        ):
            result = await server.call_tool("memory_store", {"key": "k", "value": "v"})
        assert result["success"] is False
        assert "error" in result


class TestUnknownTool:
    """Test handling of unknown tool names."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, server: AttuneMCPServer):
        """Test that calling an unknown tool returns an error."""
        result = await server.call_tool("nonexistent_tool", {})
        assert result["success"] is False
        assert "Unknown tool" in result["error"]


class TestVersionCheck:
    """Test version check module."""

    def test_version_check_import(self):
        """Test that version_check module can be imported."""
        from attune.mcp.version_check import check_for_updates, get_update_status

        assert callable(check_for_updates)
        assert callable(get_update_status)

    def test_compare_versions(self):
        """Test version comparison logic."""
        from attune.mcp.version_check import _compare_versions

        assert _compare_versions("1.0.0", "2.0.0") is True
        assert _compare_versions("2.0.0", "1.0.0") is False
        assert _compare_versions("1.0.0", "1.0.0") is False
        assert _compare_versions("1.0.0", "1.0.1") is True
        assert _compare_versions("1.9.0", "1.10.0") is True


class TestPersonalMemoryTools:
    """Tests for personal_memory_capture/recall/topics/forget MCP tools."""

    @pytest.mark.asyncio
    async def test_capture_success(self, server: AttuneMCPServer, tmp_path):
        """personal_memory_capture returns success with destination path."""
        mock_pm = MagicMock()
        mock_pm.capture.return_value = tmp_path / "auth-design" / "decision.md"
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool(
                "personal_memory_capture",
                {"topic": "auth-design", "content": "Use JWT", "kind": "decision"},
            )
        assert result["success"] is True
        assert "auth-design" in result["path"]

    @pytest.mark.asyncio
    async def test_capture_invalid_topic_returns_error(self, server: AttuneMCPServer):
        """personal_memory_capture returns error for an invalid topic slug."""
        mock_pm = MagicMock()
        mock_pm.capture.side_effect = ValueError("Invalid topic slug")
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool(
                "personal_memory_capture",
                {"topic": "../etc/passwd", "content": "bad"},
            )
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_capture_import_error(self, server: AttuneMCPServer):
        """personal_memory_capture degrades gracefully when module is absent."""
        import sys

        saved = sys.modules.pop("attune.memory.personal", None)
        sys.modules["attune.memory.personal"] = None  # type: ignore[assignment]
        try:
            result = await server.call_tool(
                "personal_memory_capture",
                {"topic": "auth-design", "content": "Use JWT"},
            )
        finally:
            del sys.modules["attune.memory.personal"]
            if saved is not None:
                sys.modules["attune.memory.personal"] = saved
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_recall_success(self, server: AttuneMCPServer):
        """personal_memory_recall returns matching hits."""
        mock_pm = MagicMock()
        mock_pm.query.return_value = [
            {"path": "auth-design/decision.md", "score": 0.9, "summary": "JWT"},
        ]
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool(
                "personal_memory_recall",
                {"query": "authentication", "k": 1},
            )
        assert result["success"] is True
        assert result["count"] == 1
        assert result["results"][0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_recall_empty(self, server: AttuneMCPServer):
        """personal_memory_recall returns empty results list when nothing matches."""
        mock_pm = MagicMock()
        mock_pm.query.return_value = []
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool("personal_memory_recall", {"query": "nothing"})
        assert result["success"] is True
        assert result["count"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_recall_import_error(self, server: AttuneMCPServer):
        """personal_memory_recall degrades gracefully when module is absent."""
        import sys

        saved = sys.modules.pop("attune.memory.personal", None)
        sys.modules["attune.memory.personal"] = None  # type: ignore[assignment]
        try:
            result = await server.call_tool("personal_memory_recall", {"query": "auth"})
        finally:
            del sys.modules["attune.memory.personal"]
            if saved is not None:
                sys.modules["attune.memory.personal"] = saved
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_topics_success(self, server: AttuneMCPServer):
        """personal_memory_topics returns list of topic slugs."""
        mock_pm = MagicMock()
        mock_pm.list_topics.return_value = ["auth-design", "retry-loop"]
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool("personal_memory_topics", {})
        assert result["success"] is True
        assert result["count"] == 2
        assert "auth-design" in result["topics"]

    @pytest.mark.asyncio
    async def test_topics_empty(self, server: AttuneMCPServer):
        """personal_memory_topics returns empty list when no topics exist."""
        mock_pm = MagicMock()
        mock_pm.list_topics.return_value = []
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool("personal_memory_topics", {})
        assert result["success"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_topics_import_error(self, server: AttuneMCPServer):
        """personal_memory_topics degrades gracefully when module is absent."""
        import sys

        saved = sys.modules.pop("attune.memory.personal", None)
        sys.modules["attune.memory.personal"] = None  # type: ignore[assignment]
        try:
            result = await server.call_tool("personal_memory_topics", {})
        finally:
            del sys.modules["attune.memory.personal"]
            if saved is not None:
                sys.modules["attune.memory.personal"] = saved
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_forget_success(self, server: AttuneMCPServer):
        """personal_memory_forget returns deleted count on success."""
        mock_pm = MagicMock()
        mock_pm.forget_topic.return_value = 1
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool(
                "personal_memory_forget",
                {"topic": "auth-design"},
            )
        assert result["success"] is True
        assert result["deleted"] == 1
        assert result["topic"] == "auth-design"

    @pytest.mark.asyncio
    async def test_forget_topic_not_found(self, server: AttuneMCPServer):
        """personal_memory_forget returns failure when topic does not exist."""
        mock_pm = MagicMock()
        mock_pm.forget_topic.return_value = 0
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool(
                "personal_memory_forget",
                {"topic": "nonexistent"},
            )
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_forget_invalid_topic(self, server: AttuneMCPServer):
        """personal_memory_forget returns error for invalid topic slug."""
        mock_pm = MagicMock()
        mock_pm.forget_topic.side_effect = ValueError("Invalid topic slug")
        with patch("attune.memory.personal.PersonalMemory", return_value=mock_pm):
            result = await server.call_tool(
                "personal_memory_forget",
                {"topic": "../etc"},
            )
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_forget_import_error(self, server: AttuneMCPServer):
        """personal_memory_forget degrades gracefully when module is absent."""
        import sys

        saved = sys.modules.pop("attune.memory.personal", None)
        sys.modules["attune.memory.personal"] = None  # type: ignore[assignment]
        try:
            result = await server.call_tool(
                "personal_memory_forget",
                {"topic": "auth-design"},
            )
        finally:
            del sys.modules["attune.memory.personal"]
            if saved is not None:
                sys.modules["attune.memory.personal"] = saved
        assert result["success"] is False
