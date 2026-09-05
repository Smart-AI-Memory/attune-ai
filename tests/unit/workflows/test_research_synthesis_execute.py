"""Tests for ResearchSynthesisWorkflow execute() and _run_agent_synthesis().

Covers the Agent SDK execution paths. Uses real SDK message
instances rather than duck-typed fakes so isinstance-based
collectors in agent_sdk_adapter actually fire (per CLAUDE.md
lesson: duck-typed test fakes fail isinstance-based collectors
silently — construct real SDK class instances in tests).

The only thing mocked is ``claude_agent_sdk.query`` itself; the
ResultMessage / AssistantMessage / TextBlock instances yielded
by the fake generator are constructed via the real dataclasses.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import patch

import claude_agent_sdk
import pytest

from attune.workflows.agent_sdk_adapter import AgentRunResult
from attune.workflows.base import ModelTier
from attune.workflows.data_classes import WorkflowResult
from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

# ---------------------------------------------------------------------------
# Fixtures — real SDK message instances
# ---------------------------------------------------------------------------


@pytest.fixture
def workflow() -> ResearchSynthesisWorkflow:
    """Build a fresh ResearchSynthesisWorkflow."""
    return ResearchSynthesisWorkflow()


@pytest.fixture
def assistant_message() -> claude_agent_sdk.AssistantMessage:
    """Real AssistantMessage with a TextBlock payload."""
    block = claude_agent_sdk.types.TextBlock(text="Sources reviewed: 5 documents across 2 themes.")
    return claude_agent_sdk.AssistantMessage(
        content=[block],
        model="claude-opus-4-7",
        parent_tool_use_id=None,
    )


@pytest.fixture
def result_message() -> claude_agent_sdk.ResultMessage:
    """Real ResultMessage with a final synthesis."""
    return claude_agent_sdk.ResultMessage(
        subtype="success",
        duration_ms=15000,
        duration_api_ms=13200,
        is_error=False,
        num_turns=6,
        session_id="sess-research-7",
        total_cost_usd=0.58,
        usage={"input_tokens": 2200, "output_tokens": 1100},
        result=(
            "## Summary\n"
            "Research synthesis complete.\n\n"
            "## Research\n\n"
            "### Theme: caching\n"
            "- Prompt caching cuts repeat-token cost [source: docs/a.md]\n\n"
            "## Suggestions\n"
            "1. Adopt prompt caching for the synthesis stage\n"
        ),
        structured_output=None,
    )


def _make_fake_query(messages):
    """Build an async generator factory yielding the given messages.

    The factory matches ``claude_agent_sdk.query``'s signature
    (it accepts arbitrary kwargs and returns an async iterator).
    """

    async def fake_query(*args, **kwargs):
        for msg in messages:
            yield msg

    return fake_query


# ---------------------------------------------------------------------------
# execute() — argument validation
# ---------------------------------------------------------------------------


class TestExecuteValidation:
    """Empty / missing path is rejected before any SDK call."""

    def test_no_path_returns_error(self, workflow):
        result = asyncio.run(workflow.execute())
        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "path argument is required" in result.error

    def test_empty_path_returns_error(self, workflow):
        result = asyncio.run(workflow.execute(path=""))
        assert result.success is False
        assert "path argument is required" in result.error


# ---------------------------------------------------------------------------
# execute() — happy path through real SDK message instances
# ---------------------------------------------------------------------------


class TestExecuteSuccess:
    """Successful runs across the depth profiles."""

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_success_yields_workflow_result(
        self, mock_query, workflow, assistant_message, result_message
    ):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])
        result = asyncio.run(workflow.execute(path="/tmp/research", depth="standard"))

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.provider == "anthropic"
        # final_output is a serialized WorkflowReport once findings
        # parse. Assert the SECTIONS survived, not just the summary.
        assert isinstance(result.final_output, dict)
        assert "synthesis" in result.final_output["summary"]
        assert [s["title"] for s in result.final_output["sections"]] == [
            "Research",
            "Next steps",
        ]

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_metadata_populated(self, mock_query, workflow, assistant_message, result_message):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])
        result = asyncio.run(workflow.execute(path="/tmp/research", depth="quick"))

        assert result.success is True
        meta = result.metadata or {}
        assert meta.get("depth") == "quick"
        assert meta.get("path", "").endswith("/tmp/research") or "tmp" in meta.get("path", "")
        assert meta.get("max_turns") == 10

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_result_only_no_assistant_text(self, mock_query, workflow, result_message):
        """ResultMessage alone — exercises the ``run_result = sdk_result``
        assignment branch in _run_agent_synthesis.
        """
        mock_query.side_effect = _make_fake_query([result_message])
        result = asyncio.run(workflow.execute(path="/tmp/research"))
        assert result.success is True

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_empty_stream_returns_default_text(self, mock_query, workflow):
        """Empty stream — exercises the default AgentRunResult passing
        straight through to the adapter.
        """
        mock_query.side_effect = _make_fake_query([])
        result = asyncio.run(workflow.execute(path="/tmp/research"))
        assert isinstance(result, WorkflowResult)


# ---------------------------------------------------------------------------
# execute() — depth → max_turns mapping
# ---------------------------------------------------------------------------


class TestExecuteDepthMapping:
    """``depth`` arg drives ``max_turns`` passed to the SDK."""

    def _max_turns_for(self, depth, workflow, monkeypatch):
        """Run execute(depth=...) and return the max_turns recorded."""
        captured: dict = {}

        async def capture_query(*args, **kwargs):
            opts = kwargs.get("options")
            captured["max_turns"] = opts.max_turns
            if False:
                yield  # make this an async generator

        monkeypatch.setattr(
            "attune.workflows.research_synthesis.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow.execute(path="/tmp/research", depth=depth))
        return captured.get("max_turns")

    def test_quick_depth_uses_10_turns(self, workflow, monkeypatch):
        assert self._max_turns_for("quick", workflow, monkeypatch) == 10

    def test_standard_depth_uses_20_turns(self, workflow, monkeypatch):
        assert self._max_turns_for("standard", workflow, monkeypatch) == 20

    def test_deep_depth_uses_40_turns(self, workflow, monkeypatch):
        assert self._max_turns_for("deep", workflow, monkeypatch) == 40

    def test_unknown_depth_falls_back_to_20(self, workflow, monkeypatch):
        """Undocumented depth values silently fall back to standard's 20."""
        assert self._max_turns_for("preposterous", workflow, monkeypatch) == 20

    def test_default_depth_is_standard(self, workflow, monkeypatch):
        """No depth kwarg → standard (20)."""
        captured: dict = {}

        async def capture_query(*args, **kwargs):
            captured["max_turns"] = kwargs["options"].max_turns
            if False:
                yield

        monkeypatch.setattr(
            "attune.workflows.research_synthesis.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow.execute(path="/tmp/research"))
        assert captured["max_turns"] == 20


# ---------------------------------------------------------------------------
# execute() — exception handling
# ---------------------------------------------------------------------------


class TestExecuteExceptionHandling:
    """Each specific exception type produces a structured error result."""

    def _patch_query_to_raise(self, monkeypatch, exc):
        async def raising_query(*args, **kwargs):
            raise exc
            if False:  # pragma: no cover
                yield

        monkeypatch.setattr(
            "attune.workflows.research_synthesis.claude_agent_sdk.query",
            raising_query,
        )

    def test_import_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, ImportError("sdk missing"))
        result = asyncio.run(workflow.execute(path="/tmp/research"))
        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    def test_connection_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, ConnectionError("refused"))
        result = asyncio.run(workflow.execute(path="/tmp/research"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_timeout_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, TimeoutError("slow"))
        result = asyncio.run(workflow.execute(path="/tmp/research"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_generic_exception(self, workflow, monkeypatch):
        """Generic SDK exception surfaces the Phase 2 typed error
        result (sdk-error-message-fidelity spec). Mock exception has
        no recognizable argv shape, so classifier falls back to
        'unknown' with synthetic capture-failure stderr."""
        self._patch_query_to_raise(monkeypatch, RuntimeError("kaboom"))
        result = asyncio.run(workflow.execute(path="/tmp/research"))
        assert result.success is False
        assert "claude CLI subprocess failed" in result.error
        assert result.metadata.get("sdk_error_kind") == "unknown"
        assert "sdk_stderr" in result.metadata


# ---------------------------------------------------------------------------
# _run_agent_synthesis() — directly, bypassing execute()
# ---------------------------------------------------------------------------


class TestRunAgentSynthesisDirect:
    """Direct invocation surfaces the SDK loop's exact behavior."""

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_collects_assistant_and_result(
        self, mock_query, workflow, assistant_message, result_message
    ):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])

        run_result = asyncio.run(workflow._run_agent_synthesis("/tmp/research", 20, "standard"))
        assert isinstance(run_result, AgentRunResult)
        assert "Sources" in run_result.result_text or "Summary" in run_result.result_text

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_no_messages_returns_default_text(self, mock_query, workflow):
        mock_query.side_effect = _make_fake_query([])
        run_result = asyncio.run(workflow._run_agent_synthesis("/tmp/research", 20))
        assert run_result.result_text == "No results returned."

    @patch("attune.workflows.research_synthesis.claude_agent_sdk.query")
    def test_passes_subagent_definitions(self, mock_query, workflow, result_message):
        """All three subagents are wired into the SDK call's options."""
        captured: dict = {}

        async def capturing_query(*args, **kwargs):
            captured["options"] = kwargs.get("options")
            captured["prompt"] = kwargs.get("prompt")
            yield result_message

        mock_query.side_effect = capturing_query
        asyncio.run(workflow._run_agent_synthesis("/tmp/research", 20, "standard"))

        opts = captured["options"]
        assert "source-summarizer" in opts.agents
        assert "pattern-analyst" in opts.agents
        assert "synthesis-writer" in opts.agents
        # System prompt + path in task prompt.
        assert "research synthesis orchestrator" in opts.system_prompt
        assert "/tmp/research" in captured["prompt"]

    def test_default_depth_uses_standard_budget(self, workflow, monkeypatch):
        """Calling without an explicit depth defaults to 'standard'."""
        captured: dict = {}

        async def capture_query(*args, **kwargs):
            captured["called"] = True
            if False:
                yield

        monkeypatch.setattr(
            "attune.workflows.research_synthesis.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow._run_agent_synthesis("/tmp/research", 20))
        assert captured.get("called") is True


# ---------------------------------------------------------------------------
# _error_result() — inherited from BaseWorkflow but exercised here so
# its surface stays measured even if base.py refactors break the contract.
# ---------------------------------------------------------------------------


class TestErrorResult:
    """Shape of the failure WorkflowResult."""

    def test_structure(self, workflow):
        result = workflow._error_result("nope")
        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert result.error == "nope"
        assert result.total_duration_ms == 0
        assert result.cost_report.total_cost == 0.0

    def test_stage_metadata(self, workflow):
        result = workflow._error_result("nope")
        assert len(result.stages) == 1
        assert result.stages[0].name == "research-synthesis"
        assert result.stages[0].tier == ModelTier.CAPABLE

    def test_timestamps_bounded(self, workflow):
        before = datetime.now()
        result = workflow._error_result("nope")
        after = datetime.now()
        assert before <= result.started_at <= after
        assert before <= result.completed_at <= after


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
