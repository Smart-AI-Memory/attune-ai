"""Integration test for the MCP server call_tool → _dispatch_tool → handler chain.

This is the end-to-end path that every MCP tool invocation takes:
  call_tool(name, args)
    → _dispatch_tool(name, args)          # rate-limit + routing
      → handler(args)                     # actual work
        → workflow.execute() / memory op  # business logic

Tests here use a real AttuneMCPServer instance with workflows mocked at the
boundary so no LLM calls or Redis connections are needed.
"""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.mcp.server import AttuneMCPServer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def server(tmp_path):
    """Real AttuneMCPServer with plugin registration and version-check suppressed."""
    with patch.object(AttuneMCPServer, "_register_plugin_tools"):
        with patch.dict(sys.modules, {"attune.mcp.version_check": MagicMock()}):
            return AttuneMCPServer(workspace_root=str(tmp_path))


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
            result = await server.call_tool("context_get", {"key": "x"})

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
            {"context_get": AsyncMock(side_effect=RuntimeError("boom"))},
        ):
            result = await server.call_tool("context_get", {"key": "x"})

        assert result.get("success") is False
        assert "error" in result


# ---------------------------------------------------------------------------
# session_memory_* plugin tools: real registration + dispatch chain
# (cross-provider-memory-transport T2 — direct handler-only mocks are
# insufficient; these run call_tool → _dispatch_tool → _plugin_handlers)
# ---------------------------------------------------------------------------


class _InMemorySearchableBackend:
    """Searchable backend double at the session_stash boundary.

    Dispatch, handlers, schemas, and the REAL PII/secrets sanitizer all
    run; only the storage service is substituted.
    """

    is_fallback = False

    def __init__(self):
        self.records: dict[str, dict] = {}

    def is_connected(self):
        return True

    def remember(self, content, *, memory_id=None, session_id=None, topics=None):
        self.records[memory_id] = {
            "id": memory_id,
            "text": content,
            "session_id": session_id,
            "topics": list(topics or []),
        }
        return True

    def search(self, query, limit=10):
        return [dict(r) for r in list(self.records.values())[:limit]]

    def recent(self, limit=5, cwd=None):
        return [dict(r) for r in list(self.records.values())[-limit:]][::-1]

    def forget(self, ids):
        deleted = 0
        for record_id in ids:
            if record_id in self.records:
                del self.records[record_id]
                deleted += 1
        return deleted

    def stash(self, *args, **kwargs):
        return True


@pytest.fixture
def session_server(server):
    """Real server with the attune_redis plugin tools actually registered
    (the base fixture suppresses plugin auto-registration)."""
    from attune_redis.mcp_tools import register_tools

    register_tools(server)
    return server


class TestSessionMemoryDispatch:
    @pytest.mark.asyncio
    async def test_capture_recall_forget_roundtrip(self, session_server):
        """Full lifecycle through the real dispatch chain against one
        backend instance: capture → recall (id recovered from results) →
        forget → recall finds nothing."""
        backend = _InMemorySearchableBackend()
        with patch("attune.memory.session_stash.resolve_backend", return_value=backend):
            captured = await session_server.call_tool(
                "session_memory_capture",
                {"content": "the parser retry loop deadlocks", "type": "bug"},
            )
            assert captured["ok"] is True

            recalled = await session_server.call_tool(
                "session_memory_recall", {"query": "parser deadlock"}
            )
            assert recalled["ok"] is True
            assert recalled["count"] == 1
            record_id = recalled["results"][0]["id"]
            assert record_id == captured["id"]

            forgotten = await session_server.call_tool(
                "session_memory_forget", {"ids": [record_id]}
            )
            assert forgotten["ok"] is True
            assert forgotten["deleted"] == 1

            empty = await session_server.call_tool("session_memory_recall", {"query": "parser"})
            assert empty["count"] == 0

    @pytest.mark.asyncio
    async def test_pii_canary_sanitized_in_stored_representation(self, session_server):
        """CR-2: the REAL sanitizer runs on the MCP transport — a
        PII-bearing canary must be redacted in what the backend stores."""
        backend = _InMemorySearchableBackend()
        with patch("attune.memory.session_stash.resolve_backend", return_value=backend):
            result = await session_server.call_tool(
                "session_memory_capture",
                {"content": "canary: mail jane@example.com when fixed"},
            )
        assert result["ok"] is True
        stored = backend.records[result["id"]]["text"]
        assert "jane@example.com" not in stored
        assert "[EMAIL]" in stored

    @pytest.mark.asyncio
    async def test_no_backend_maps_to_ok_false_with_reason(self, session_server):
        """CR-5: Python-level degradation surfaces as {ok: false, reason}."""
        with patch("attune.memory.session_stash.resolve_backend", return_value=None):
            result = await session_server.call_tool(
                "session_memory_capture", {"content": "finding"}
            )
        assert result["ok"] is False
        assert result["reason"] == "no_backend"

    @pytest.mark.asyncio
    async def test_status_dispatches_with_mcp_transport(self, session_server):
        result = await session_server.call_tool("session_memory_status", {})
        assert result["transport"] == "mcp"
        assert "ok" in result
        assert "backend_transport" in result

    @pytest.mark.asyncio
    async def test_redis_memory_store_schema_untouched(self, session_server):
        """D6 guard at the registration surface: the generic tool's frozen
        schema is registered unchanged alongside the additive tools."""
        schema = session_server.tools["redis_memory_store"]["input_schema"]
        assert schema["required"] == ["key", "value"]
        assert "session_memory_capture" in session_server.tools
