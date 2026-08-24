"""Tests for the elicitation_render_widget MCP handler (S1 surface).

Thin wiring of ``form_to_widget_html``: a valid form returns the HTML +
metadata; a malformed form returns problems instead of raising.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from attune.mcp.server import AttuneMCPServer

_FORM = {
    "title": "Scope",
    "fields": [
        {"id": "goal", "text": "Goal?", "type": "single_select", "options": ["a", "b"]},
        {"id": "note", "text": "Note", "type": "textarea", "required": False},
        {"id": "n", "text": "How many?", "type": "number", "minimum": 1, "maximum": 9},
        {"id": "when", "text": "When?", "type": "date", "required": False},
    ],
}


def _make_server() -> AttuneMCPServer:
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch("attune.mcp.version_check.check_for_updates", return_value=None):
            return AttuneMCPServer()


class TestRenderWidgetHandler:
    @pytest.mark.asyncio
    async def test_valid_form_returns_html_and_metadata(self):
        server = _make_server()
        out = await server._handle_elicitation_render_widget({"form": _FORM, "message": "fill it"})
        assert out["success"] is True
        assert out["title"] == "Scope"
        assert out["field_ids"] == ["goal", "note", "n", "when"]
        assert 'id="attune-elicit-form-' in out["html"]
        assert "fill it" in out["html"]
        # the v2.1 rich controls render (D10 enum-honesty fix)
        assert '<input type="number"' in out["html"]
        assert '<input type="date"' in out["html"]

    @pytest.mark.asyncio
    async def test_registered_in_dispatch_table(self):
        server = _make_server()
        assert "elicitation_render_widget" in server._build_dispatch_table()

    @pytest.mark.asyncio
    async def test_malformed_form_returns_problems(self):
        server = _make_server()
        out = await server._handle_elicitation_render_widget({"form": {"title": ""}})
        assert out["success"] is False
        assert out["problems"]
