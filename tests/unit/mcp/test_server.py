"""Unit tests for attune.mcp.server module.

Tests cover:
- _get_default_user_id: OS login fallback
- AttuneMCPServer.__init__: tool/resource/prompt registration
- _register_tools: merges all schema groups
- _build_dispatch_table: all tool names mapped
- _dispatch_tool: rate limiting, unknown tools, error handling
- call_tool: voice layer wrapping, skip tools
- get_tool_list / get_resource_list / get_prompt_list
- get_prompt_messages: delegation and error
- attune level handlers: get/set/validation
- context handlers: get/set

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import (
    ATTUNE_LEVEL_DESCRIPTIONS,
    ATTUNE_LEVEL_NAMES,
    _get_default_user_id,
)

# -- Helpers ---------------------------------------------------------


def _make_server(tmp_path: Any = None, **kwargs: Any) -> Any:
    """Build an AttuneMCPServer with patched init side-effects."""
    with patch(
        "attune.mcp.server.AttuneMCPServer._register_plugin_tools",
    ):
        from attune.mcp.server import AttuneMCPServer

        ws = str(tmp_path) if tmp_path else None
        return AttuneMCPServer(workspace_root=ws, **kwargs)


# -- _get_default_user_id --------------------------------------------


class TestGetDefaultUserId:
    """Tests for _get_default_user_id()."""

    def test_returns_login_name(self) -> None:
        with patch("os.getlogin", return_value="alice"):
            assert _get_default_user_id() == "alice"

    def test_falls_back_on_os_error(self) -> None:
        with patch("os.getlogin", side_effect=OSError):
            assert _get_default_user_id() == "mcp-session"


# -- AttuneMCPServer init ------------------------------------------


class TestServerInit:
    """Tests for AttuneMCPServer construction."""

    def test_default_workspace_root(self) -> None:
        """Uses cwd when workspace_root not provided."""
        server = _make_server()
        assert server._workspace_root  # non-empty

    def test_custom_workspace_root(self, tmp_path: Any) -> None:
        server = _make_server(tmp_path)
        assert server._workspace_root == str(tmp_path)

    def test_env_var_workspace_root(self, tmp_path: Any, monkeypatch: Any) -> None:
        """ATTUNE_MCP_WORKSPACE_ROOT broadens the sandbox without code changes.

        Use case: the MCP server launches in a git worktree but needs to
        operate on a sibling main checkout. Setting the env var lets the
        user opt into the wider scope explicitly.
        """
        from attune.mcp.server import AttuneMCPServer

        monkeypatch.setenv("ATTUNE_MCP_WORKSPACE_ROOT", str(tmp_path))
        server = AttuneMCPServer()
        assert server._workspace_root == str(tmp_path)

    def test_explicit_arg_overrides_env_var(self, tmp_path: Any, monkeypatch: Any) -> None:
        """Explicit workspace_root argument wins over env var."""
        from attune.mcp.server import AttuneMCPServer

        env_path = tmp_path / "from-env"
        env_path.mkdir()
        arg_path = tmp_path / "from-arg"
        arg_path.mkdir()

        monkeypatch.setenv("ATTUNE_MCP_WORKSPACE_ROOT", str(env_path))
        server = AttuneMCPServer(workspace_root=str(arg_path))
        assert server._workspace_root == str(arg_path)

    def test_claude_project_dir_workspace_root(self, tmp_path: Any, monkeypatch: Any) -> None:
        """CLAUDE_PROJECT_DIR is used when no explicit arg / ATTUNE var.

        Claude Code sets CLAUDE_PROJECT_DIR in the spawned MCP server's
        environment to the project root, so the sandbox tracks the
        project even when the server's cwd differs.
        """
        from attune.mcp.server import AttuneMCPServer

        monkeypatch.delenv("ATTUNE_MCP_WORKSPACE_ROOT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        server = AttuneMCPServer()
        assert server._workspace_root == str(tmp_path)

    def test_attune_var_overrides_claude_project_dir(self, tmp_path: Any, monkeypatch: Any) -> None:
        """ATTUNE_MCP_WORKSPACE_ROOT wins over CLAUDE_PROJECT_DIR."""
        from attune.mcp.server import AttuneMCPServer

        attune_path = tmp_path / "from-attune"
        attune_path.mkdir()
        claude_path = tmp_path / "from-claude"
        claude_path.mkdir()

        monkeypatch.setenv("ATTUNE_MCP_WORKSPACE_ROOT", str(attune_path))
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude_path))
        server = AttuneMCPServer()
        assert server._workspace_root == str(attune_path)

    def test_explicit_arg_overrides_claude_project_dir(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        """Explicit workspace_root argument wins over CLAUDE_PROJECT_DIR."""
        from attune.mcp.server import AttuneMCPServer

        claude_path = tmp_path / "from-claude"
        claude_path.mkdir()
        arg_path = tmp_path / "from-arg"
        arg_path.mkdir()

        monkeypatch.delenv("ATTUNE_MCP_WORKSPACE_ROOT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(claude_path))
        server = AttuneMCPServer(workspace_root=str(arg_path))
        assert server._workspace_root == str(arg_path)

    def test_custom_user_id(self) -> None:
        server = _make_server(user_id="test-user")
        assert server._user_id == "test-user"

    def test_tools_registered(self) -> None:
        server = _make_server()
        assert isinstance(server.tools, dict)
        assert len(server.tools) > 0

    def test_resources_registered(self) -> None:
        server = _make_server()
        assert isinstance(server.resources, dict)
        assert len(server.resources) > 0

    def test_prompts_registered(self) -> None:
        server = _make_server()
        assert isinstance(server.prompts, dict)
        assert len(server.prompts) > 0

    def test_default_attune_level(self) -> None:
        server = _make_server()
        assert server._attune_level == 3


# -- _register_tools -------------------------------------------------


class TestRegisterTools:
    """Tests for _register_tools()."""

    def test_includes_workflow_tools(self) -> None:
        from attune.mcp.server import AttuneMCPServer

        tools = AttuneMCPServer._register_tools()
        assert "security_audit" in tools

    def test_includes_memory_tools(self) -> None:
        from attune.mcp.server import AttuneMCPServer

        tools = AttuneMCPServer._register_tools()
        assert "memory_store" in tools

    def test_includes_utility_tools(self) -> None:
        from attune.mcp.server import AttuneMCPServer

        tools = AttuneMCPServer._register_tools()
        assert "auth_status" in tools

    def test_includes_help_tools(self) -> None:
        from attune.mcp.server import AttuneMCPServer

        tools = AttuneMCPServer._register_tools()
        assert "help_lookup" in tools


# -- _build_dispatch_table -------------------------------------------


class TestBuildDispatchTable:
    """Tests for _build_dispatch_table()."""

    def test_all_tools_have_handlers(self) -> None:
        """Every registered tool name has a dispatch entry."""
        server = _make_server()
        for tool_name in server.tools:
            assert tool_name in server._tool_handlers, f"Tool '{tool_name}' has no dispatch handler"

    def test_handlers_are_callable(self) -> None:
        server = _make_server()
        for name, handler in server._tool_handlers.items():
            assert callable(handler), f"Handler for '{name}' not callable"


# -- _dispatch_tool --------------------------------------------------


class TestDispatchTool:
    """Tests for _dispatch_tool()."""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self) -> None:
        """Returns error when rate limiter blocks."""
        server = _make_server()
        server._rate_limiter = MagicMock()
        server._rate_limiter.check.return_value = False

        result = await server._dispatch_tool("security_audit", {})
        assert "Rate limit exceeded" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_tool(self) -> None:
        """Returns error for unregistered tool name."""
        server = _make_server()
        result = await server._dispatch_tool("nonexistent_tool", {})
        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    @pytest.mark.asyncio
    async def test_handler_exception_caught(self) -> None:
        """Catches handler exceptions and returns error dict."""
        server = _make_server()
        server._tool_handlers["security_audit"] = AsyncMock(
            side_effect=RuntimeError("boom"),
        )
        result = await server._dispatch_tool("security_audit", {})
        assert result["success"] is False
        assert "RuntimeError" in result["error"]

    @pytest.mark.asyncio
    async def test_delegates_to_handler(self) -> None:
        """Calls the correct handler with arguments."""
        server = _make_server()
        mock_handler = AsyncMock(return_value={"success": True})
        server._tool_handlers["security_audit"] = mock_handler

        result = await server._dispatch_tool("security_audit", {"path": "."})
        mock_handler.assert_awaited_once_with({"path": "."})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_delegates_to_plugin_handler(self) -> None:
        """Falls through to plugin handlers when not in dispatch table."""
        server = _make_server()
        mock_plugin = AsyncMock(return_value={"plugin": True})
        server._plugin_handlers["custom_tool"] = mock_plugin

        result = await server._dispatch_tool("custom_tool", {"x": 1})
        mock_plugin.assert_awaited_once_with(server, {"x": 1})
        assert result["plugin"] is True


# -- call_tool -------------------------------------------------------


class TestCallTool:
    """Tests for call_tool() voice layer wrapping."""

    @pytest.mark.asyncio
    async def test_applies_voice_layer(self) -> None:
        """Voice layer wraps workflow tool results."""
        server = _make_server()
        server._tool_handlers["security_audit"] = AsyncMock(
            return_value={"success": True},
        )

        with patch(
            "attune.voice.formatter.format_mcp_response",
            return_value={"success": True, "voice": True},
        ) as mock_voice:
            result = await server.call_tool("security_audit", {"path": "."})

        mock_voice.assert_called_once()
        assert result.get("voice") is True

    @pytest.mark.asyncio
    async def test_skips_voice_for_utility_tools(self) -> None:
        """Voice layer skipped for tools in _VOICE_SKIP_TOOLS."""
        server = _make_server()
        server._tool_handlers["memory_store"] = AsyncMock(
            return_value={"success": True},
        )

        with patch(
            "attune.voice.formatter.format_mcp_response",
        ) as mock_voice:
            result = await server.call_tool("memory_store", {"key": "k", "value": "v"})

        mock_voice.assert_not_called()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_voice_layer_failure_is_non_fatal(self) -> None:
        """Voice layer error doesn't break the tool result."""
        server = _make_server()
        server._tool_handlers["code_review"] = AsyncMock(
            return_value={"success": True, "feedback": "ok"},
        )

        with patch(
            "attune.voice.formatter.format_mcp_response",
            side_effect=ImportError("no voice"),
        ):
            result = await server.call_tool("code_review", {"path": "."})

        assert result["success"] is True


# -- get_tool_list / get_resource_list / get_prompt_list -------------


class TestListMethods:
    """Tests for list accessor methods."""

    def test_get_tool_list_returns_list_of_dicts(self) -> None:
        server = _make_server()
        tools = server.get_tool_list()
        assert isinstance(tools, list)
        assert all("name" in t for t in tools)
        assert all("description" in t for t in tools)

    def test_get_resource_list_returns_list(self) -> None:
        server = _make_server()
        resources = server.get_resource_list()
        assert isinstance(resources, list)
        assert len(resources) > 0

    def test_get_prompt_list_returns_list(self) -> None:
        server = _make_server()
        prompts = server.get_prompt_list()
        assert isinstance(prompts, list)
        assert len(prompts) > 0


# -- get_prompt_messages ---------------------------------------------


class TestGetPromptMessages:
    """Tests for get_prompt_messages()."""

    def test_delegates_to_prompts_module(self) -> None:
        server = _make_server()
        with patch(
            "attune.mcp.prompts.get_prompt_messages",
            return_value=[{"role": "user", "content": {"text": "hi"}}],
        ) as mock_fn:
            result = server.get_prompt_messages("security-scan", {"path": "."})

        mock_fn.assert_called_once()
        assert len(result) == 1

    def test_raises_for_unknown_prompt(self) -> None:
        server = _make_server()
        with pytest.raises(ValueError):
            server.get_prompt_messages("nonexistent", {})


# -- attune level handlers -------------------------------------------


class TestAttuneLevelHandlers:
    """Tests for attune_get_level / attune_set_level."""

    @pytest.mark.asyncio
    async def test_get_level_returns_default(self) -> None:
        server = _make_server()
        result = await server._handle_attune_get_level()
        assert result["success"] is True
        assert result["level"] == 3
        assert result["name"] == "Proactive"

    @pytest.mark.asyncio
    async def test_set_level_valid(self) -> None:
        server = _make_server()
        result = await server._handle_attune_set_level({"level": 5})
        assert result["success"] is True
        assert result["previous_level"] == 3
        assert result["current_level"] == 5
        assert result["name"] == "Systems"

    @pytest.mark.asyncio
    async def test_set_level_invalid_too_high(self) -> None:
        server = _make_server()
        result = await server._handle_attune_set_level({"level": 6})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_set_level_invalid_too_low(self) -> None:
        server = _make_server()
        result = await server._handle_attune_set_level({"level": 0})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_set_level_invalid_type(self) -> None:
        server = _make_server()
        result = await server._handle_attune_set_level({"level": "high"})
        assert result["success"] is False


# -- context handlers ------------------------------------------------


class TestContextHandlers:
    """Tests for context_get / context_set."""

    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        server = _make_server()
        await server._handle_context_set({"key": "foo", "value": "bar"})
        result = await server._handle_context_get({"key": "foo"})
        assert result["success"] is True
        assert result["value"] == "bar"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_get_missing_key(self) -> None:
        server = _make_server()
        result = await server._handle_context_get({"key": "missing"})
        assert result["success"] is True
        assert result["value"] is None
        assert result["found"] is False


# -- Constants -------------------------------------------------------


class TestConstants:
    """Tests for module-level constants."""

    def test_level_names_covers_1_to_5(self) -> None:
        assert set(ATTUNE_LEVEL_NAMES.keys()) == {1, 2, 3, 4, 5}

    def test_level_descriptions_covers_1_to_5(self) -> None:
        assert set(ATTUNE_LEVEL_DESCRIPTIONS.keys()) == {1, 2, 3, 4, 5}
