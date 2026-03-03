"""Unit tests for attune.mcp.request_handler module.

Tests cover:
- tools/list method routing
- tools/call method routing (with async call_tool)
- resources/list method routing
- prompts/list method routing
- prompts/get method routing (success and ValueError)
- unknown method returns -32601 error

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from attune.mcp.request_handler import handle_request


def _make_server(
    tool_list: list | None = None,
    resource_list: list | None = None,
    prompt_list: list | None = None,
    call_tool_result: dict | None = None,
    prompt_messages: list | None = None,
    prompt_raises: Exception | None = None,
) -> MagicMock:
    """Build a MagicMock server with sensible defaults.

    Args:
        tool_list: Return value for get_tool_list().
        resource_list: Return value for get_resource_list().
        prompt_list: Return value for get_prompt_list().
        call_tool_result: Return value for call_tool().
        prompt_messages: Return value for get_prompt_messages().
        prompt_raises: Exception to raise from get_prompt_messages().

    Returns:
        Configured MagicMock server instance.

    """
    server = MagicMock()
    server.get_tool_list.return_value = tool_list or []
    server.get_resource_list.return_value = resource_list or []
    server.get_prompt_list.return_value = prompt_list or []

    if call_tool_result is not None:
        server.call_tool = AsyncMock(return_value=call_tool_result)
    else:
        server.call_tool = AsyncMock(return_value={})

    if prompt_raises is not None:
        server.get_prompt_messages.side_effect = prompt_raises
    else:
        server.get_prompt_messages.return_value = prompt_messages or []

    return server


@pytest.mark.unit
class TestHandleRequestToolsList:
    """Tests for tools/list method routing."""

    async def test_tools_list_returns_tools_key(self) -> None:
        """Test that tools/list returns a dict with a 'tools' key."""
        server = _make_server(tool_list=[{"name": "my_tool"}])
        result = await handle_request(server, {"method": "tools/list"})
        assert "tools" in result

    async def test_tools_list_delegates_to_get_tool_list(self) -> None:
        """Test that the tools value comes from server.get_tool_list()."""
        expected = [{"name": "tool_a"}, {"name": "tool_b"}]
        server = _make_server(tool_list=expected)
        result = await handle_request(server, {"method": "tools/list"})
        assert result["tools"] == expected

    async def test_tools_list_empty_tools(self) -> None:
        """Test tools/list with an empty tool list."""
        server = _make_server(tool_list=[])
        result = await handle_request(server, {"method": "tools/list"})
        assert result["tools"] == []


@pytest.mark.unit
class TestHandleRequestToolsCall:
    """Tests for tools/call method routing."""

    async def test_tools_call_returns_content_key(self) -> None:
        """Test that tools/call response contains a 'content' key."""
        server = _make_server(call_tool_result={"ok": True})
        request = {
            "method": "tools/call",
            "params": {"name": "my_tool", "arguments": {"x": 1}},
        }
        result = await handle_request(server, request)
        assert "content" in result

    async def test_tools_call_content_is_list(self) -> None:
        """Test that 'content' is a list."""
        server = _make_server(call_tool_result={})
        request = {
            "method": "tools/call",
            "params": {"name": "tool", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert isinstance(result["content"], list)

    async def test_tools_call_content_item_type_is_text(self) -> None:
        """Test that the content item has type 'text'."""
        server = _make_server(call_tool_result={})
        request = {
            "method": "tools/call",
            "params": {"name": "tool", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert result["content"][0]["type"] == "text"

    async def test_tools_call_content_text_is_json(self) -> None:
        """Test that the text field contains JSON-serialised tool result."""
        payload = {"status": "ok", "value": 42}
        server = _make_server(call_tool_result=payload)
        request = {
            "method": "tools/call",
            "params": {"name": "tool", "arguments": {}},
        }
        result = await handle_request(server, request)
        decoded = json.loads(result["content"][0]["text"])
        assert decoded == payload

    async def test_tools_call_passes_tool_name_and_arguments(self) -> None:
        """Test that call_tool is called with the correct name and arguments."""
        server = _make_server(call_tool_result={})
        args = {"key": "val"}
        request = {
            "method": "tools/call",
            "params": {"name": "scan_tool", "arguments": args},
        }
        await handle_request(server, request)
        server.call_tool.assert_awaited_once_with("scan_tool", args)

    async def test_tools_call_missing_arguments_defaults_to_empty_dict(self) -> None:
        """Test that missing 'arguments' key defaults to empty dict."""
        server = _make_server(call_tool_result={})
        request = {"method": "tools/call", "params": {"name": "tool"}}
        await handle_request(server, request)
        server.call_tool.assert_awaited_once_with("tool", {})


@pytest.mark.unit
class TestHandleRequestResourcesList:
    """Tests for resources/list method routing."""

    async def test_resources_list_returns_resources_key(self) -> None:
        """Test that resources/list returns a 'resources' key."""
        server = _make_server(resource_list=[{"uri": "mem://x"}])
        result = await handle_request(server, {"method": "resources/list"})
        assert "resources" in result

    async def test_resources_list_value_from_server(self) -> None:
        """Test that the resources value comes from server.get_resource_list()."""
        expected = [{"uri": "mem://a"}, {"uri": "mem://b"}]
        server = _make_server(resource_list=expected)
        result = await handle_request(server, {"method": "resources/list"})
        assert result["resources"] == expected

    async def test_resources_list_empty(self) -> None:
        """Test resources/list with empty resource list."""
        server = _make_server(resource_list=[])
        result = await handle_request(server, {"method": "resources/list"})
        assert result["resources"] == []


@pytest.mark.unit
class TestHandleRequestPromptsList:
    """Tests for prompts/list method routing."""

    async def test_prompts_list_returns_prompts_key(self) -> None:
        """Test that prompts/list returns a 'prompts' key."""
        server = _make_server(prompt_list=[{"name": "p1"}])
        result = await handle_request(server, {"method": "prompts/list"})
        assert "prompts" in result

    async def test_prompts_list_value_from_server(self) -> None:
        """Test that the prompts value comes from server.get_prompt_list()."""
        expected = [{"name": "security-scan"}, {"name": "test-gen"}]
        server = _make_server(prompt_list=expected)
        result = await handle_request(server, {"method": "prompts/list"})
        assert result["prompts"] == expected


@pytest.mark.unit
class TestHandleRequestPromptsGet:
    """Tests for prompts/get method routing."""

    async def test_prompts_get_success_returns_messages_key(self) -> None:
        """Test that a successful prompts/get returns a 'messages' key."""
        messages = [{"role": "user", "content": {"type": "text", "text": "hi"}}]
        server = _make_server(prompt_messages=messages)
        request = {
            "method": "prompts/get",
            "params": {"name": "security-scan", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert "messages" in result

    async def test_prompts_get_success_messages_value(self) -> None:
        """Test that the messages value is what the server returns."""
        messages = [{"role": "user", "content": {"type": "text", "text": "scan"}}]
        server = _make_server(prompt_messages=messages)
        request = {
            "method": "prompts/get",
            "params": {"name": "security-scan", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert result["messages"] == messages

    async def test_prompts_get_passes_name_and_arguments(self) -> None:
        """Test that get_prompt_messages is called with correct name and arguments."""
        server = _make_server(prompt_messages=[])
        args = {"path": "src/"}
        request = {
            "method": "prompts/get",
            "params": {"name": "security-scan", "arguments": args},
        }
        await handle_request(server, request)
        server.get_prompt_messages.assert_called_once_with("security-scan", args)

    async def test_prompts_get_value_error_returns_error_response(self) -> None:
        """Test that ValueError from get_prompt_messages returns an error dict."""
        server = _make_server(prompt_raises=ValueError("Unknown prompt: bad"))
        request = {
            "method": "prompts/get",
            "params": {"name": "bad", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert "error" in result

    async def test_prompts_get_value_error_code_is_32602(self) -> None:
        """Test that ValueError maps to error code -32602."""
        server = _make_server(prompt_raises=ValueError("Unknown prompt: bad"))
        request = {
            "method": "prompts/get",
            "params": {"name": "bad", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert result["error"]["code"] == -32602

    async def test_prompts_get_value_error_message_in_response(self) -> None:
        """Test that the ValueError message appears in the error response."""
        server = _make_server(prompt_raises=ValueError("Unknown prompt: bad"))
        request = {
            "method": "prompts/get",
            "params": {"name": "bad", "arguments": {}},
        }
        result = await handle_request(server, request)
        assert "Unknown prompt: bad" in result["error"]["message"]

    async def test_prompts_get_missing_arguments_defaults_to_empty_dict(self) -> None:
        """Test that missing 'arguments' in params defaults to empty dict."""
        server = _make_server(prompt_messages=[])
        request = {"method": "prompts/get", "params": {"name": "test-gen"}}
        await handle_request(server, request)
        server.get_prompt_messages.assert_called_once_with("test-gen", {})


@pytest.mark.unit
class TestHandleRequestUnknownMethod:
    """Tests for unknown method routing."""

    async def test_unknown_method_returns_error_key(self) -> None:
        """Test that an unknown method returns a dict with 'error' key."""
        server = _make_server()
        result = await handle_request(server, {"method": "unknown/method"})
        assert "error" in result

    async def test_unknown_method_error_code_is_32601(self) -> None:
        """Test that unknown method error code is -32601."""
        server = _make_server()
        result = await handle_request(server, {"method": "not/a/method"})
        assert result["error"]["code"] == -32601

    async def test_unknown_method_message_contains_method_name(self) -> None:
        """Test that error message contains the unrecognised method name."""
        server = _make_server()
        result = await handle_request(server, {"method": "weird/method"})
        assert "weird/method" in result["error"]["message"]

    async def test_none_method_returns_error(self) -> None:
        """Test that a request with no 'method' key returns an error."""
        server = _make_server()
        result = await handle_request(server, {})
        assert "error" in result

    async def test_missing_params_does_not_raise(self) -> None:
        """Test that a request without 'params' does not raise an exception."""
        server = _make_server(tool_list=[])
        # tools/list doesn't use params — should succeed without them
        result = await handle_request(server, {"method": "tools/list"})
        assert "tools" in result
