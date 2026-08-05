"""Widget test fixtures.

The kernel artifact (chartkit/dist/kernel.min.js) is npm-built and
gitignored, so it does not exist in CI checkouts. Tool tests must
never depend on it: every test gets a stub kernel on a tmp path.
The stub carries the real banner shape so banner assertions hold.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import pytest

from attune.widgets import chart_widget_tool


@pytest.fixture(autouse=True)
def stub_kernel(tmp_path, monkeypatch):
    """Point _KERNEL_PATH at a stub so tests never need npm build."""
    stub = tmp_path / "kernel.min.js"
    stub.write_text(
        "/* chartkit v0.0.0-teststub sealed */\nvar ChartKit={render:function(){}};",
        encoding="utf-8",
    )
    monkeypatch.setattr(chart_widget_tool, "_KERNEL_PATH", stub)
    return stub
