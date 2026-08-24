"""Tests for the elicitation_ask MCP handler (the v2 renderer).

Drives the full server-side round-trip with a mocked session: build the
requestedSchema, await session.elicit_form, and map the structured result
back through collect_form_response. Covers accept (valid + R4-invalid),
decline, cancel, capability-unsupported, elicit-raises, and a malformed
form definition.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.mcp.server import AttuneMCPServer

_FORM = {
    "title": "Scope",
    "fields": [
        {"id": "goal", "text": "Goal?", "type": "single_select", "options": ["a", "b"]},
        {"id": "age", "text": "Age", "type": "number", "minimum": 0, "maximum": 10},
    ],
}


def _make_server() -> AttuneMCPServer:
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch("attune.mcp.version_check.check_for_updates", return_value=None):
            return AttuneMCPServer()


class _Result:
    def __init__(self, action, content=None):
        self.action = action
        self.content = content


class _Session:
    """Fake ServerSession capturing the elicit_form call."""

    def __init__(self, result=None, raises=None):
        self._result = result
        self._raises = raises
        self.calls = []

    async def elicit_form(self, message, schema, request_id):
        self.calls.append({"message": message, "schema": schema, "request_id": request_id})
        if self._raises:
            raise self._raises
        return self._result


def _with_session(server, session, request_id="req-1"):
    server._elicitation_session = lambda: (session, request_id)


class TestElicitationAsk:
    @pytest.mark.asyncio
    async def test_accept_valid_returns_responses(self):
        server = _make_server()
        sess = _Session(_Result("accept", {"goal": "a", "age": 5}))
        _with_session(server, sess)
        out = await server._handle_elicitation_ask({"form": _FORM, "message": "hi"})
        assert out["success"] is True
        assert out["action"] == "accept"
        assert out["responses"] == {"goal": "a", "age": 5}
        # the built schema reached the session, keyed by field id
        assert sess.calls[0]["schema"]["properties"]["age"]["maximum"] == 10
        assert sess.calls[0]["message"] == "hi"
        assert sess.calls[0]["request_id"] == "req-1"

    @pytest.mark.asyncio
    async def test_accept_invalid_returns_problems(self):
        server = _make_server()
        _with_session(server, _Session(_Result("accept", {"goal": "zzz", "age": 99})))
        out = await server._handle_elicitation_ask({"form": _FORM})
        assert out["success"] is False
        assert out["action"] == "accept"
        assert any("goal" in p for p in out["problems"])
        assert any("age" in p for p in out["problems"])

    @pytest.mark.asyncio
    async def test_message_defaults_to_form_title(self):
        server = _make_server()
        sess = _Session(_Result("accept", {"goal": "a", "age": 0}))
        _with_session(server, sess)
        await server._handle_elicitation_ask({"form": _FORM})
        assert sess.calls[0]["message"] == "Scope"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("action", ["decline", "cancel"])
    async def test_decline_or_cancel(self, action):
        server = _make_server()
        _with_session(server, _Session(_Result(action, None)))
        out = await server._handle_elicitation_ask({"form": _FORM})
        assert out["success"] is False
        assert out["action"] == action
        assert out["responses"] == {}

    @pytest.mark.asyncio
    async def test_unsupported_when_no_session(self):
        server = _make_server()
        server._elicitation_session = lambda: (None, None)
        out = await server._handle_elicitation_ask({"form": _FORM})
        assert out["success"] is False
        assert out["action"] == "unsupported"

    @pytest.mark.asyncio
    async def test_elicit_raises_degrades_to_error(self):
        server = _make_server()
        _with_session(server, _Session(raises=RuntimeError("no elicitation capability")))
        out = await server._handle_elicitation_ask({"form": _FORM})
        assert out["success"] is False
        assert out["action"] == "error"

    @pytest.mark.asyncio
    async def test_malformed_form_rejected_before_eliciting(self):
        server = _make_server()
        sess = _Session(_Result("accept", {}))
        _with_session(server, sess)
        # missing options on a select → bad definition
        bad = {"title": "T", "fields": [{"id": "g", "text": "G", "type": "single_select"}]}
        out = await server._handle_elicitation_ask({"form": bad})
        assert out["success"] is False
        assert "problems" in out
        assert sess.calls == []  # never reached the session

    def test_elicitation_session_outside_request_returns_none(self):
        # No live MCP request context → (None, None), the fallback signal.
        assert AttuneMCPServer._elicitation_session() == (None, None)
