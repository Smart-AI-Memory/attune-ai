"""Integration tests for voice layer wiring.

Verifies that the voice layer is actually invoked at the
wiring points: workflow CLI, MCP call_tool, and error paths.
These tests protect the wiring from future refactors.

Copyright 2026 Smart-AI-Memory
Licensed under Apache 2.0
"""

from __future__ import annotations

import types
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from attune.voice import personality
from attune.workflows.data_classes import CostReport, WorkflowResult


@pytest.fixture(autouse=True)
def _disable_spend_gate(monkeypatch):
    """Disable the spend gate so these voice-wiring tests run the
    workflow (the gate, collaboration-gates, would otherwise block a
    non-TTY run before execution).
    """
    monkeypatch.setenv("ATTUNE_SPEND_GATE", "off")
    # Auth-evidence for the pre-gate auth pre-flight (setup-friction
    # F1/F4): CI runners have no ~/.claude and an empty key, and these
    # tests target dispatch, not auth.
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-evidence")  # pragma: allowlist secret


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**kwargs) -> types.SimpleNamespace:
    """Create args for cmd_workflow_run."""
    defaults = {
        "name": "test-wf",
        "input": None,
        "path": None,
        "target": None,
        "json": False,
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def _make_workflow_result(
    success: bool = True,
    score: int | None = None,
    error: str | None = None,
) -> WorkflowResult:
    """Build a real WorkflowResult for integration testing."""
    now = datetime.now(timezone.utc)
    final_output = {"formatted_report": "## Findings\n\n3 issues found."}
    if score is not None:
        final_output["score"] = score
    return WorkflowResult(
        success=success,
        stages=[],
        final_output=final_output,
        cost_report=CostReport(
            total_cost=0.0123,
            baseline_cost=0.025,
            savings=0.0127,
            savings_percent=50.8,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=2500,
        error=error,
    )


def _make_workflow_class(result: WorkflowResult) -> type:
    """Build a workflow class that returns the given result."""

    def execute(self, **kwargs):
        return result

    return type("TestWorkflow", (), {"execute": execute})


# ===========================================================================
# 1. Workflow CLI wiring — full voice flow
# ===========================================================================


class TestWorkflowCliVoiceWiring:
    """Verify _print_workflow_result routes through the voice layer."""

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    @patch("attune.workflows.get_workflow")
    def test_voice_greeting_appears(self, mock_get, _mock_steps, capsys):
        """Output includes voiced greeting, not 'Workflow completed'."""
        result = _make_workflow_result(success=True)
        mock_get.return_value = _make_workflow_class(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="code-review"))
        assert rc == 0
        out = capsys.readouterr().out
        assert personality.GREETING_SUCCESS in out
        assert "Workflow completed" not in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    @patch("attune.workflows.get_workflow")
    def test_voice_score_commentary(self, mock_get, _mock_steps, capsys):
        """Output with a score shows voiced commentary."""
        result = _make_workflow_result(success=True, score=92)
        mock_get.return_value = _make_workflow_class(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="security-audit"))
        assert rc == 0
        out = capsys.readouterr().out
        assert personality.score_commentary(92) in out
        assert "92/100" in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    @patch("attune.workflows.get_workflow")
    def test_voice_cost_line(self, mock_get, _mock_steps, capsys):
        """Output includes cost and duration."""
        result = _make_workflow_result()
        mock_get.return_value = _make_workflow_class(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="test-gen"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "$0.0123" in out
        assert "2.5s" in out
        assert personality.HEADER_COST in out

    @patch(
        "attune.voice.formatter.get_next_steps",
        return_value=["I'd run `attune workflow run test-gen` next — coverage gaps"],
    )
    @patch("attune.workflows.get_workflow")
    def test_voice_next_steps(self, mock_get, _mock_steps, capsys):
        """Output includes voiced next-step suggestions."""
        result = _make_workflow_result()
        mock_get.return_value = _make_workflow_class(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="code-review"))
        assert rc == 0
        out = capsys.readouterr().out
        assert personality.HEADER_NEXT_STEPS in out
        assert "test-gen" in out

    @patch("attune.voice.formatter.get_next_steps", return_value=[])
    @patch("attune.workflows.get_workflow")
    def test_voice_report_content(self, mock_get, _mock_steps, capsys):
        """Output includes the workflow's formatted report."""
        result = _make_workflow_result()
        mock_get.return_value = _make_workflow_class(result)

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="bug-predict"))
        assert rc == 0
        out = capsys.readouterr().out
        assert "3 issues found" in out


# ===========================================================================
# 2. Error path wiring — format_error instead of raw print
# ===========================================================================


class TestErrorPathVoiceWiring:
    """Verify error paths use the voice layer."""

    @patch("attune.workflows.get_workflow")
    def test_error_uses_voice_prefix(self, mock_get, capsys):
        """Workflow exception uses voiced error, not raw 'Workflow failed'."""

        class FailingWorkflow:
            def execute(self, **kwargs):
                raise RuntimeError("API connection lost")

        mock_get.return_value = FailingWorkflow

        from attune.cli_commands.workflow_commands import cmd_workflow_run

        rc = cmd_workflow_run(_make_args(name="code-review"))
        # Uncaught exception → exit 2 (unplanned failure) per the
        # workflow-failure-exit-propagation contract.
        assert rc == 2
        out = capsys.readouterr().out
        assert personality.ERROR_PREFIX in out
        assert "API connection lost" in out
        assert "Workflow failed" not in out


# ===========================================================================
# 3. MCP call_tool wiring — voice fields in response
# ===========================================================================


class TestMcpCallToolVoiceWiring:
    """Verify call_tool adds voice fields to workflow responses."""

    @pytest.mark.asyncio
    async def test_workflow_response_gets_voice_summary(self):
        """Workflow tool responses include voice_summary."""
        from attune.mcp.server import EmpathyMCPServer

        server = EmpathyMCPServer(workspace_root="/tmp")

        # Mock the dispatch to return a raw workflow response
        raw_response = {"success": True, "score": 85, "findings": []}
        server._dispatch_tool = AsyncMock(return_value=raw_response)

        result = await server.call_tool("security_audit", {"path": "."})

        assert "voice_summary" in result
        assert result["score"] == 85

    @pytest.mark.asyncio
    async def test_utility_tools_skip_voice(self):
        """Utility tools (memory, auth, etc.) don't get voice fields."""
        from attune.mcp.server import EmpathyMCPServer

        server = EmpathyMCPServer(workspace_root="/tmp")

        raw_response = {"success": True, "memories": []}
        server._dispatch_tool = AsyncMock(return_value=raw_response)

        result = await server.call_tool("memory_store", {"key": "test"})

        assert "voice_summary" not in result
        assert result == raw_response

    @pytest.mark.asyncio
    async def test_failed_voice_layer_degrades_gracefully(self):
        """If voice layer fails, raw response is returned unchanged."""
        from attune.mcp.server import EmpathyMCPServer

        server = EmpathyMCPServer(workspace_root="/tmp")

        raw_response = {"success": True, "data": "test"}
        server._dispatch_tool = AsyncMock(return_value=raw_response)

        # Force voice layer to fail
        with patch(
            "attune.voice.formatter.format_mcp_response",
            side_effect=RuntimeError("voice broke"),
        ):
            result = await server.call_tool("code_review", {"path": "."})

        # Should still get the raw response back
        assert result["success"] is True
        assert result["data"] == "test"
