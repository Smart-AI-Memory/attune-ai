"""Unit tests for MCP SDK handler functions in attune.mcp.server.

Tests cover the handler functions registered with the MCP SDK Server:
- _handle_list_tools returns Tool objects from AttuneMCPServer schemas
- _handle_call_tool delegates to AttuneMCPServer.call_tool()
- _handle_list_resources returns Resource objects
- _handle_list_prompts returns Prompt objects
- _handle_get_prompt returns GetPromptResult with messages

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from attune_forms import MCP_APP_RESOURCE_URI, mcp_app_resource, mcp_app_tool_meta
from mcp.types import ClientCapabilities

from attune.mcp.server import (
    _handle_call_tool,
    _handle_get_prompt,
    _handle_list_prompts,
    _handle_list_resources,
    _handle_list_tools,
    _handle_read_resource,
)


def _make_app(
    tools: dict | None = None,
    resources: dict | None = None,
    prompts: dict | None = None,
    call_tool_result: dict | None = None,
    prompt_messages: list | None = None,
    prompt_raises: Exception | None = None,
) -> MagicMock:
    """Build a mock AttuneMCPServer with sensible defaults."""
    app = MagicMock()
    app.tools = tools or {}
    app.resources = resources or {}
    app.prompts = prompts or {}
    app.call_tool = AsyncMock(return_value=call_tool_result or {})

    if prompt_raises is not None:
        app.get_prompt_messages.side_effect = prompt_raises
    else:
        app.get_prompt_messages.return_value = prompt_messages or []

    return app


@pytest.mark.unit
class TestHandleListTools:
    """Tests for _handle_list_tools handler."""

    async def test_returns_tool_objects(self) -> None:
        """Test that list_tools returns a list of Tool objects."""
        app = _make_app(
            tools={
                "my_tool": {
                    "description": "A tool",
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
        )
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_list_tools()
        assert len(result) == 1
        assert result[0].name == "my_tool"
        assert result[0].description == "A tool"

    async def test_empty_tools(self) -> None:
        """Test list_tools with no registered tools."""
        app = _make_app(tools={})
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_list_tools()
        assert result == []

    async def test_multiple_tools(self) -> None:
        """Test list_tools returns all registered tools."""
        app = _make_app(
            tools={
                "a": {
                    "description": "Tool A",
                    "input_schema": {"type": "object", "properties": {}},
                },
                "b": {
                    "description": "Tool B",
                    "input_schema": {"type": "object", "properties": {}},
                },
            },
        )
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_list_tools()
        assert len(result) == 2
        names = {t.name for t in result}
        assert names == {"a", "b"}

    async def test_mcp_apps_metadata_is_negotiated_for_fix_preview_only(self) -> None:
        """A positively advertised UI profile decorates only its renderer."""
        capabilities = ClientCapabilities.model_validate(
            {
                "extensions": {
                    "io.modelcontextprotocol/ui": {"mimeTypes": ["text/html;profile=mcp-app"]}
                }
            }
        )
        sdk_server = MagicMock()
        sdk_server.request_context.session.client_params.capabilities = capabilities
        app = _make_app(
            tools={
                "fix_workspace_preview": {"input_schema": {"type": "object"}},
                "fix_workspace_collect_action": {"input_schema": {"type": "object"}},
            }
        )
        with (
            patch("attune.mcp.server._mcp_server", sdk_server),
            patch("attune.mcp.server._get_app", return_value=app),
        ):
            tools = await _handle_list_tools()

        assert tools[0].meta == mcp_app_tool_meta()
        assert tools[1].meta is None

    async def test_no_request_context_keeps_tool_metadata_absent(self) -> None:
        """Negotiation fails closed for direct calls and legacy clients."""
        app = _make_app(tools={"fix_workspace_preview": {"input_schema": {"type": "object"}}})
        with patch("attune.mcp.server._get_app", return_value=app):
            tools = await _handle_list_tools()

        assert tools[0].meta is None


@pytest.mark.unit
class TestHandleCallTool:
    """Tests for _handle_call_tool handler."""

    async def test_returns_text_content(self) -> None:
        """Test that call_tool returns a list of TextContent."""
        app = _make_app(call_tool_result={"ok": True})
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_call_tool("my_tool", {"x": 1})
        assert len(result) == 1
        assert result[0].type == "text"

    async def test_content_is_json(self) -> None:
        """Test that TextContent text is JSON-serialised tool result."""
        payload = {"status": "ok", "value": 42}
        app = _make_app(call_tool_result=payload)
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_call_tool("tool", {})
        decoded = json.loads(result[0].text)
        assert decoded == payload

    async def test_passes_name_and_arguments(self) -> None:
        """Test that call_tool delegates with correct name and args."""
        app = _make_app(call_tool_result={})
        with patch("attune.mcp.server._get_app", return_value=app):
            await _handle_call_tool("scan_tool", {"key": "val"})
        app.call_tool.assert_awaited_once_with("scan_tool", {"key": "val"})

    async def test_none_arguments_defaults_to_empty_dict(self) -> None:
        """Test that None arguments defaults to empty dict."""
        app = _make_app(call_tool_result={})
        with patch("attune.mcp.server._get_app", return_value=app):
            await _handle_call_tool("tool", None)
        app.call_tool.assert_awaited_once_with("tool", {})


@pytest.mark.unit
class TestHandleListResources:
    """Tests for _handle_list_resources handler."""

    async def test_returns_resource_objects(self) -> None:
        """Test that list_resources returns Resource objects."""
        app = _make_app(
            resources={
                "workflows": {
                    "uri": "attune://workflows",
                    "name": "Workflows",
                    "description": "Available workflows",
                    "mime_type": "application/json",
                },
            },
        )
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_list_resources()
        assert len(result) == 1
        assert result[0].name == "Workflows"

    async def test_empty_resources(self) -> None:
        """Test list_resources with no resources."""
        app = _make_app(resources={})
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_list_resources()
        assert result == []

    async def test_shared_ui_resource_maps_metadata_and_reads_exact_html(self) -> None:
        """The listed resource is the released attune-forms source of truth."""
        resource = mcp_app_resource()
        app = _make_app(resources={"dynamic_surface": resource})
        with patch("attune.mcp.server._get_app", return_value=app):
            listed = await _handle_list_resources()
            contents = await _handle_read_resource(MCP_APP_RESOURCE_URI)

        assert listed[0].meta == resource["meta"]
        assert contents[0].content == resource["text"]
        assert contents[0].mime_type == resource["mime_type"]

    async def test_unknown_resource_fails_closed(self) -> None:
        app = _make_app(resources={"dynamic_surface": mcp_app_resource()})
        with patch("attune.mcp.server._get_app", return_value=app):
            with pytest.raises(ValueError, match="Unknown or unreadable resource"):
                await _handle_read_resource("attune://missing")


@pytest.mark.unit
class TestHandleListPrompts:
    """Tests for _handle_list_prompts handler."""

    async def test_returns_prompt_objects(self) -> None:
        """Test that list_prompts returns Prompt objects."""
        app = _make_app(
            prompts={
                "test-gen": {
                    "name": "test-gen",
                    "description": "Generate tests",
                    "arguments": [
                        {
                            "name": "module",
                            "description": "Module path",
                            "required": True,
                        },
                    ],
                },
            },
        )
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_list_prompts()
        assert len(result) == 1
        assert result[0].name == "test-gen"
        assert len(result[0].arguments) == 1


@pytest.mark.unit
class TestHandleGetPrompt:
    """Tests for _handle_get_prompt handler."""

    async def test_success_returns_get_prompt_result(self) -> None:
        """Test that get_prompt returns a GetPromptResult."""
        messages = [
            {
                "role": "user",
                "content": {"type": "text", "text": "Run security scan"},
            },
        ]
        app = _make_app(prompt_messages=messages)
        with patch("attune.mcp.server._get_app", return_value=app):
            result = await _handle_get_prompt("security-scan", {"path": "src/"})
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"

    async def test_passes_name_and_arguments(self) -> None:
        """Test that get_prompt_messages is called correctly."""
        app = _make_app(prompt_messages=[])
        with patch("attune.mcp.server._get_app", return_value=app):
            await _handle_get_prompt("test-gen", {"module": "foo.py"})
        app.get_prompt_messages.assert_called_once_with(
            "test-gen",
            {"module": "foo.py"},
        )

    async def test_none_arguments_defaults_to_empty_dict(self) -> None:
        """Test that None arguments defaults to empty dict."""
        app = _make_app(prompt_messages=[])
        with patch("attune.mcp.server._get_app", return_value=app):
            await _handle_get_prompt("test-gen", None)
        app.get_prompt_messages.assert_called_once_with("test-gen", {})

    async def test_value_error_propagates(self) -> None:
        """Test that ValueError from get_prompt_messages propagates."""
        app = _make_app(prompt_raises=ValueError("Unknown prompt"))
        with patch("attune.mcp.server._get_app", return_value=app):
            with pytest.raises(ValueError, match="Unknown prompt"):
                await _handle_get_prompt("bad", {})
