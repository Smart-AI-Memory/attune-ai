"""Coverage for the chart_render_widget MCP handler (thin delegate).

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import attune.mcp.server as server_module
from attune.widgets import chart_widget_tool


@pytest.fixture(autouse=True)
def stub_kernel(tmp_path, monkeypatch):
    """The kernel artifact is npm-built and gitignored — stub it."""
    stub = tmp_path / "kernel.min.js"
    stub.write_text(
        "/* chartkit v0.0.0-teststub sealed */\nvar ChartKit={render:function(){}};",
        encoding="utf-8",
    )
    monkeypatch.setattr(chart_widget_tool, "_KERNEL_PATH", stub)


def _make_server(tmp_path):
    with patch.object(server_module.AttuneMCPServer, "_register_plugin_tools"):
        return server_module.AttuneMCPServer(workspace_root=str(tmp_path))


SPEC = {
    "v": 1,
    "type": "bar",
    "data": [{"m": "Jan", "n": 3}],
    "encodings": {
        "x": {"field": "m", "type": "nominal"},
        "y": {"field": "n", "type": "quantitative"},
    },
}


@pytest.mark.asyncio
async def test_handler_delegates_and_returns_widget_html(tmp_path):
    server = _make_server(tmp_path)
    result = await server._handle_chart_render_widget({"chart_id": "h1", "spec": SPEC})
    assert result["success"] is True
    assert result["chart_id"] == "h1"
    assert "ChartKit.render" in result["html"]


@pytest.mark.asyncio
async def test_handler_surfaces_field_level_problems(tmp_path):
    server = _make_server(tmp_path)
    bad = dict(SPEC, type="pie")
    result = await server._handle_chart_render_widget({"chart_id": "h2", "spec": bad})
    assert result["success"] is False
    assert any("type" in p for p in result["problems"])


@pytest.mark.asyncio
async def test_handler_rejects_malformed_chart_id(tmp_path):
    server = _make_server(tmp_path)
    result = await server._handle_chart_render_widget({"chart_id": "../escape", "spec": SPEC})
    assert result["success"] is False
    assert "chart_id" in result["error"]
