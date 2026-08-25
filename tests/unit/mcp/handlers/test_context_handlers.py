"""Unit tests for context handler methods on AttuneMCPServer."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer


def _make_server(context: dict | None = None) -> AttuneMCPServer:
    """Build a server instance with optional pre-set context."""
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            server = AttuneMCPServer()
    if context is not None:
        server._context = context
    return server


class TestHandleContextGet:
    """Tests for _handle_context_get()."""

    @pytest.mark.asyncio
    async def test_context_get_existing_key_returns_value(self):
        """Returns found=True and correct value for a key that exists."""
        server = _make_server(context={"my_key": "hello"})
        result = await server._handle_context_get({"key": "my_key"})

        assert result["success"] is True
        assert result["key"] == "my_key"
        assert result["value"] == "hello"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_context_get_missing_key_returns_none(self):
        """Returns found=False and value=None for a key that does not exist."""
        server = _make_server(context={})
        result = await server._handle_context_get({"key": "ghost"})

        assert result["success"] is True
        assert result["key"] == "ghost"
        assert result["value"] is None
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_context_get_dict_value(self):
        """Works correctly when stored value is a dict."""
        server = _make_server(context={"cfg": {"level": 2}})
        result = await server._handle_context_get({"key": "cfg"})

        assert result["value"] == {"level": 2}
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_context_get_integer_value(self):
        """Works correctly when stored value is an integer."""
        server = _make_server(context={"count": 42})
        result = await server._handle_context_get({"key": "count"})

        assert result["value"] == 42
        assert result["found"] is True


class TestHandleContextSet:
    """Tests for _handle_context_set()."""

    @pytest.mark.asyncio
    async def test_context_set_stores_value(self):
        """Stores the value in server._context under the given key."""
        server = _make_server()
        result = await server._handle_context_set({"key": "token", "value": "abc123"})

        assert result["success"] is True
        assert result["key"] == "token"
        assert result["value"] == "abc123"
        assert server._context["token"] == "abc123"

    @pytest.mark.asyncio
    async def test_context_set_overwrites_existing(self):
        """Overwrites a previously set key."""
        server = _make_server(context={"k": "old"})
        await server._handle_context_set({"key": "k", "value": "new"})

        assert server._context["k"] == "new"

    @pytest.mark.asyncio
    async def test_context_set_none_value(self):
        """Stores None as a valid value."""
        server = _make_server()
        result = await server._handle_context_set({"key": "nullish", "value": None})

        assert result["value"] is None
        assert server._context["nullish"] is None

    @pytest.mark.asyncio
    async def test_context_set_dict_value(self):
        """Stores a nested dict as the value."""
        server = _make_server()
        payload = {"a": 1, "b": [1, 2, 3]}
        result = await server._handle_context_set({"key": "nested", "value": payload})

        assert result["value"] == payload
        assert server._context["nested"] == payload
