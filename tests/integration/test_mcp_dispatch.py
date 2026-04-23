"""Integration test for the MCP server call_tool → _dispatch_tool → handler chain.

This is the end-to-end path that every MCP tool invocation takes:
  call_tool(name, args)
    → _dispatch_tool(name, args)          # rate-limit + routing
      → handler(args)                     # actual work
        → workflow.execute() / memory op  # business logic

Tests here use a real EmpathyMCPServer instance with workflows mocked at the
boundary so no LLM calls or Redis connections are needed.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import EmpathyMCPServer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def server(tmp_path):
    """Real EmpathyMCPServer with plugin registration and version-check suppressed."""
    with patch.object(EmpathyMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return EmpathyMCPServer(workspace_root=str(tmp_path))


# ---------------------------------------------------------------------------
# Dispatch routing
# ---------------------------------------------------------------------------


class TestDispatchRouting:
    """call_tool routes to the right handler and returns structured output."""

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, server):
        result = await server.call_tool("no_such_tool", {})
        assert result.get("success") is False or "error" in result

    @pytest.mark.asyncio
    async def test_attune_get_level_dispatches_correctly(self, server):
        """attune_get_level is a pure-memory handler — no workflow, no mock needed."""
        result = await server.call_tool("attune_get_level", {})
        assert "level" in result
        assert isinstance(result["level"], int)
        assert 1 <= result["level"] <= 5

    @pytest.mark.asyncio
    async def test_attune_set_then_get_level(self, server):
        """set_level → get_level round-trip exercises two handlers in sequence."""
        await server.call_tool("attune_set_level", {"level": 4})
        result = await server.call_tool("attune_get_level", {})
        assert result["level"] == 4

    @pytest.mark.asyncio
    async def test_context_set_and_get(self, server):
        """context_set / context_get round-trip through the same server instance."""
        await server.call_tool("context_set", {"key": "project", "value": "attune-ai"})
        result = await server.call_tool("context_get", {"key": "project"})
        assert result.get("value") == "attune-ai" or result.get("project") == "attune-ai"

    @pytest.mark.asyncio
    async def test_personal_memory_capture_dispatches(self, server):
        """personal_memory_capture goes through the full dispatch chain.
        Assertion is intentionally loose — the tool is registered and dispatched;
        result is either success or a structured error (never an exception)."""
        result = await server.call_tool(
            "personal_memory_capture",
            {"topic": "dispatch_test", "content": "verifying dispatch works"},
        )
        assert isinstance(result, dict)
        # Dispatch worked: result is structured (not a raw exception)
        assert "success" in result or "error" in result


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_after_limit(self, server):
        """When the rate limiter denies, _dispatch_tool returns an error without
        calling the handler."""
        with patch.object(server._rate_limiter, "check", return_value=False):
            result = await server.call_tool("attune_get_level", {})

        assert "error" in result
        assert "Rate limit" in result["error"]


# ---------------------------------------------------------------------------
# Workflow handler integration: health_check through the full chain
# ---------------------------------------------------------------------------


class TestWorkflowDispatch:
    @pytest.mark.asyncio
    async def test_health_check_dispatches_to_workflow(self, server, tmp_path):
        """health_check tool goes through call_tool → _dispatch_tool →
        _run_health_check → HealthCheckWorkflow.execute().

        The workflow is mocked at execute() so no LLM call is made,
        but the entire dispatch chain above it runs for real.
        """
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.final_output = {
            "score": 95,
            "checks": [],
            "recommendations": [],
        }
        mock_result.cost_report = MagicMock(total_cost=0.01)

        with patch(
            "attune.workflows.orchestrated_health_check.OrchestratedHealthCheckWorkflow.execute",
            new=AsyncMock(return_value=mock_result),
        ):
            result = await server.call_tool("health_check", {"project_root": str(tmp_path)})

        assert result.get("success") is True
        assert "health_score" in result or "score" in result or "checks" in result

    @pytest.mark.asyncio
    async def test_exception_in_handler_returns_structured_error(self, server):
        """If a handler raises unexpectedly, _dispatch_tool catches it and
        returns a structured error instead of propagating the exception."""
        with patch.dict(
            server._tool_handlers,
            {"attune_get_level": AsyncMock(side_effect=RuntimeError("boom"))},
        ):
            result = await server.call_tool("attune_get_level", {})

        assert result.get("success") is False
        assert "error" in result
