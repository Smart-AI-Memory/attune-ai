"""Real MCP dispatch for the handoff tools (spec R6, transport receipt-2 pattern).

Separate file from test_mcp_dispatch.py to avoid a held-queue
collision with #1594, which modifies that module. Same discipline:
a real EmpathyMCPServer, the real dispatch table, the real
attune.handoff core — only the repo is a tmp fixture.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from attune.mcp.server import EmpathyMCPServer


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.email=fixture@test",
            "-c",
            "user.name=Fixture",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "base.txt").write_text("base\n", encoding="utf-8")
    _git(root, "add", "base.txt")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "checkout", "-q", "-b", "feature/hand")
    (root / "feat.txt").write_text("feature\n", encoding="utf-8")
    _git(root, "add", "feat.txt")
    _git(root, "commit", "-q", "-m", "feature work")
    return root


@pytest.fixture
def server(repo: Path) -> EmpathyMCPServer:
    """Real server rooted at the fixture repo; plugins/version-check off."""
    with patch.object(EmpathyMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return EmpathyMCPServer(workspace_root=str(repo))


class TestHandoffDispatch:
    """call_tool → _dispatch_tool → handoff handlers → attune.handoff."""

    def test_tools_registered(self, server: EmpathyMCPServer) -> None:
        names = {t["name"] for t in server.get_tool_list()}
        assert {"handoff_create", "handoff_resume"} <= names

    @pytest.mark.asyncio
    async def test_create_then_resume_round_trip(
        self, server: EmpathyMCPServer, repo: Path
    ) -> None:
        created = await server.call_tool(
            "handoff_create",
            {
                "goal": "Dispatch round trip",
                "next_action": "Resume and verify",
                "provider": "test-suite",
            },
        )
        assert created["ok"] is True
        assert created["slug"] == "feature-hand"
        packet_file = Path(created["path"])
        assert packet_file.exists()

        report = await server.call_tool("handoff_resume", {})
        assert report["ok"] is True
        assert report["verified"]["branch"] == "feature/hand"
        assert report["verified"]["provider"] == "test-suite"
        assert report["asserted"]["goal"] == "Dispatch round trip"
        assert report["warnings"] == []
        assert report["memory"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_resume_missing_packet_truthful(self, server: EmpathyMCPServer) -> None:
        result = await server.call_tool("handoff_resume", {})
        assert result["ok"] is False
        assert result["reason"] == "packet_not_found"

    @pytest.mark.asyncio
    async def test_create_cap_rejection_through_dispatch(self, server: EmpathyMCPServer) -> None:
        result = await server.call_tool("handoff_create", {"goal": "x" * 3000})
        # call_tool appends voice-layer keys — assert the contract subset,
        # never exact dict equality (repo lesson: additive keys break it).
        assert result["ok"] is False
        assert result["reason"] == "field_over_cap"
        assert result["field"] == "goal"
        assert result["limit"] == 2048
