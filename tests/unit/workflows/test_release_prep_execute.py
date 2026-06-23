"""Tests for ReleasePreparationWorkflow execute() and _run_agent_prep().

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
from attune.workflows.release_prep import ReleasePreparationWorkflow

# ---------------------------------------------------------------------------
# Fixtures — real SDK message instances
# ---------------------------------------------------------------------------


@pytest.fixture
def workflow() -> ReleasePreparationWorkflow:
    """Build a fresh ReleasePreparationWorkflow."""
    return ReleasePreparationWorkflow()


@pytest.fixture
def assistant_message() -> claude_agent_sdk.AssistantMessage:
    """Real AssistantMessage with a TextBlock payload."""
    block = claude_agent_sdk.types.TextBlock(
        text="Health: tests passing. Security: no CVEs. Changelog: 3 features."
    )
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
        duration_ms=24000,
        duration_api_ms=20000,
        is_error=False,
        num_turns=8,
        session_id="sess-release-9",
        total_cost_usd=1.24,
        usage={"input_tokens": 3200, "output_tokens": 1500},
        result="## Summary\nRelease readiness: 92/100. Go.",
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
    """Successful runs across the three depth profiles."""

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_success_yields_workflow_result(
        self, mock_query, workflow, assistant_message, result_message
    ):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])
        result = asyncio.run(workflow.execute(path="/tmp/proj", depth="standard"))

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.provider == "anthropic"
        assert "Health" in result.final_output or "Summary" in result.final_output

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_metadata_populated(self, mock_query, workflow, assistant_message, result_message):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])
        result = asyncio.run(workflow.execute(path="/tmp/proj", depth="quick"))

        assert result.success is True
        meta = result.metadata or {}
        assert meta.get("depth") == "quick"
        # path is resolved to absolute; just check it ends with our segment.
        assert meta.get("path", "").endswith("/tmp/proj") or "tmp" in meta.get("path", "")
        assert meta.get("max_turns") == 10

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_result_only_no_assistant_text(self, mock_query, workflow, result_message):
        """ResultMessage alone — exercises the ``run_result = sdk_result``
        assignment branch in _run_agent_prep.
        """
        mock_query.side_effect = _make_fake_query([result_message])
        result = asyncio.run(workflow.execute(path="/tmp/proj"))
        assert result.success is True

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_empty_stream_returns_default_text(self, mock_query, workflow):
        """Empty stream — exercises the ``AgentRunResult(...="No results")``
        initialization being passed straight through.
        """
        mock_query.side_effect = _make_fake_query([])
        result = asyncio.run(workflow.execute(path="/tmp/proj"))
        # Adapter still produces a WorkflowResult; result_text defaulted.
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
            "attune.workflows.release_prep.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow.execute(path="/tmp/proj", depth=depth))
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
            "attune.workflows.release_prep.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow.execute(path="/tmp/proj"))
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
            "attune.workflows.release_prep.claude_agent_sdk.query",
            raising_query,
        )

    def test_import_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, ImportError("sdk missing"))
        result = asyncio.run(workflow.execute(path="/tmp/proj"))
        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    def test_connection_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, ConnectionError("refused"))
        result = asyncio.run(workflow.execute(path="/tmp/proj"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_timeout_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, TimeoutError("slow"))
        result = asyncio.run(workflow.execute(path="/tmp/proj"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_generic_exception(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, RuntimeError("kaboom"))
        result = asyncio.run(workflow.execute(path="/tmp/proj"))
        assert result.success is False
        # Phase 5 of docs/specs/sdk-error-message-fidelity/ — see
        # test_sdk_error_fidelity_phase5.py for the new shape.
        assert "claude CLI subprocess failed" in result.error
        assert result.metadata.get("sdk_error_kind") == "unknown"


# ---------------------------------------------------------------------------
# _run_agent_prep() — directly, bypassing execute()
# ---------------------------------------------------------------------------


class TestRunAgentPrepDirect:
    """Direct invocation surfaces the SDK loop's exact behavior."""

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_collects_assistant_and_result(
        self, mock_query, workflow, assistant_message, result_message
    ):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])

        run_result = asyncio.run(workflow._run_agent_prep("/tmp/proj", 20, "standard"))
        assert isinstance(run_result, AgentRunResult)
        # build_result_text prefers assistant_parts when they're at least as
        # long as result_parts; here both are short and assistant wins by length.
        assert "Health" in run_result.result_text or "Summary" in run_result.result_text

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_no_messages_returns_default_text(self, mock_query, workflow):
        mock_query.side_effect = _make_fake_query([])
        run_result = asyncio.run(workflow._run_agent_prep("/tmp/proj", 20))
        assert run_result.result_text == "No results returned."

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_passes_subagent_definitions(self, mock_query, workflow, result_message):
        """All four subagents (health-checker, security-scanner,
        changelog-generator, release-assessor) are wired into the SDK
        call's options.

        Note: release-prep has 4 subagents while sibling SDK workflows
        (refactor_plan, perf_audit, etc.) have 3 — see CLAUDE.md lesson
        "count subagents in the source before writing the
        test_passes_subagent_definitions assertion."
        """
        captured: dict = {}

        async def capturing_query(*args, **kwargs):
            captured["options"] = kwargs.get("options")
            captured["prompt"] = kwargs.get("prompt")
            yield result_message

        mock_query.side_effect = capturing_query
        asyncio.run(workflow._run_agent_prep("/tmp/proj", 20, "standard"))

        opts = captured["options"]
        assert "health-checker" in opts.agents
        assert "security-scanner" in opts.agents
        assert "changelog-generator" in opts.agents
        assert "release-assessor" in opts.agents
        # System prompt + path in task prompt.
        assert "release preparation orchestrator" in opts.system_prompt
        assert "/tmp/proj" in captured["prompt"]

    @patch("attune.workflows.release_prep.claude_agent_sdk.query")
    def test_default_depth_kwarg(self, mock_query, workflow, result_message):
        """``depth`` kwarg defaults to 'standard' when omitted."""
        mock_query.side_effect = _make_fake_query([result_message])
        run_result = asyncio.run(workflow._run_agent_prep("/tmp/proj", 20))
        assert isinstance(run_result, AgentRunResult)


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
        assert result.stages[0].name == "release-notes"
        assert result.stages[0].tier == ModelTier.CAPABLE

    def test_timestamps_bounded(self, workflow):
        before = datetime.now()
        result = workflow._error_result("nope")
        after = datetime.now()
        assert before <= result.started_at <= after
        assert before <= result.completed_at <= after
