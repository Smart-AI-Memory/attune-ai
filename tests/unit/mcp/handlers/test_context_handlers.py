"""Unit tests for context and attune level handler methods on AttuneMCPServer."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer


def _make_server(context: dict | None = None, attune_level: int = 3) -> AttuneMCPServer:
    """Build a server instance with optional pre-set context and level."""
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            server = AttuneMCPServer()
    if context is not None:
        server._context = context
    server._attune_level = attune_level
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


class TestHandleAttuneGetLevel:
    """Tests for _handle_attune_get_level()."""

    @pytest.mark.asyncio
    async def test_get_level_returns_all_keys(self):
        """Result contains success, level, name, description."""
        server = _make_server(attune_level=3)
        result = await server._handle_attune_get_level()

        assert result["success"] is True
        assert "level" in result
        assert "name" in result
        assert "description" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "level, expected_name",
        [
            (1, "Reactive"),
            (2, "Guided"),
            (3, "Proactive"),
            (4, "Anticipatory"),
            (5, "Systems"),
        ],
    )
    async def test_get_level_name_for_each_level(self, level: int, expected_name: str):
        """Returns the correct name for each valid level 1-5."""
        server = _make_server(attune_level=level)
        result = await server._handle_attune_get_level()

        assert result["level"] == level
        assert result["name"] == expected_name

    @pytest.mark.asyncio
    async def test_get_level_unknown_level(self):
        """Out-of-range level returns 'Unknown' name and empty description."""
        server = _make_server(attune_level=99)
        result = await server._handle_attune_get_level()

        assert result["name"] == "Unknown"
        assert result["description"] == ""

    @pytest.mark.asyncio
    async def test_get_level_description_not_empty_for_valid_levels(self):
        """Each valid level has a non-empty description."""
        for level in range(1, 6):
            server = _make_server(attune_level=level)
            result = await server._handle_attune_get_level()
            assert result["description"], f"Expected non-empty description for level {level}"


class TestHandleAttuneSetLevel:
    """Tests for _handle_attune_set_level()."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
    async def test_set_level_valid_levels_succeed(self, level: int):
        """All integer levels 1-5 are accepted."""
        server = _make_server(attune_level=1)
        result = await server._handle_attune_set_level({"level": level})

        assert result["success"] is True
        assert result["current_level"] == level
        assert server._attune_level == level

    @pytest.mark.asyncio
    async def test_set_level_returns_previous_level(self):
        """previous_level reflects the level before the update."""
        server = _make_server(attune_level=2)
        result = await server._handle_attune_set_level({"level": 4})

        assert result["previous_level"] == 2
        assert result["current_level"] == 4

    @pytest.mark.asyncio
    async def test_set_level_returns_name(self):
        """Result includes the name of the new level."""
        server = _make_server(attune_level=1)
        result = await server._handle_attune_set_level({"level": 3})

        assert result["name"] == "Proactive"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_level", [0, 6, -1, 100])
    async def test_set_level_out_of_range_returns_error(self, bad_level: int):
        """Integers outside 1-5 return success=False with error message."""
        server = _make_server(attune_level=3)
        result = await server._handle_attune_set_level({"level": bad_level})

        assert result["success"] is False
        assert "error" in result
        assert server._attune_level == 3  # unchanged

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_value", ["3", 3.5, None, [], {}])
    async def test_set_level_non_integer_returns_error(self, bad_value):
        """Non-integer values return success=False."""
        server = _make_server(attune_level=2)
        result = await server._handle_attune_set_level({"level": bad_value})

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    @pytest.mark.parametrize("bad_bool", [True, False])
    async def test_set_level_rejects_bool(self, bad_bool):
        """bool is an int subclass, so True/False would otherwise pass the
        isinstance(int) check and be used as 1/0 — they must be rejected."""
        server = _make_server(attune_level=2)
        result = await server._handle_attune_set_level({"level": bad_bool})

        assert result["success"] is False
        assert "error" in result
        assert server._attune_level == 2  # unchanged

    @pytest.mark.asyncio
    async def test_set_level_missing_level_key_returns_error(self):
        """Missing level key (returns None from .get()) returns error."""
        server = _make_server(attune_level=1)
        result = await server._handle_attune_set_level({})

        assert result["success"] is False


class TestLevelToolsDeprecation:
    """The level tools are deprecated in 14.x, removed in 15.0.0 (D2).

    Ruled by the 15.0.0 manifest (release-15-manifest decisions.md D2,
    chair 2026-08-24): the interaction-level concept is retired. These pins keep the 14.x deprecation surface honest —
    both handlers warn, both success payloads carry the notice, and
    both tool schemas lead with DEPRECATED.
    """

    @pytest.mark.asyncio
    async def test_get_level_emits_deprecation_warning(self):
        """_handle_attune_get_level warns DeprecationWarning naming 15.0.0."""
        server = _make_server(attune_level=3)
        with pytest.warns(DeprecationWarning, match="removed in 15.0.0"):
            result = await server._handle_attune_get_level()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_set_level_emits_deprecation_warning(self):
        """_handle_attune_set_level warns DeprecationWarning naming 15.0.0."""
        server = _make_server(attune_level=2)
        with pytest.warns(DeprecationWarning, match="removed in 15.0.0"):
            result = await server._handle_attune_set_level({"level": 4})
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_success_payloads_carry_deprecation_notice(self):
        """Both success responses include a 'deprecated' field naming 15.0.0."""
        server = _make_server(attune_level=3)
        with pytest.warns(DeprecationWarning):
            got = await server._handle_attune_get_level()
        with pytest.warns(DeprecationWarning):
            set_result = await server._handle_attune_set_level({"level": 5})

        assert "removed in 15.0.0" in got["deprecated"]
        assert "removed in 15.0.0" in set_result["deprecated"]

    @pytest.mark.asyncio
    async def test_invalid_set_level_still_errors(self):
        """The deprecation warning does not change the validation contract."""
        server = _make_server(attune_level=2)
        with pytest.warns(DeprecationWarning):
            result = await server._handle_attune_set_level({"level": 9})
        assert result["success"] is False
        assert server._attune_level == 2

    def test_tool_schemas_lead_with_deprecated(self):
        """Both level tool descriptions start with DEPRECATED."""
        from attune.mcp.tool_schemas import get_utility_tools

        tools = get_utility_tools()
        for name in ("attune_get_level", "attune_set_level"):
            assert tools[name]["description"].startswith("DEPRECATED"), name
