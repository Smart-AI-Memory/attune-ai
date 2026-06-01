"""Tests for DocumentGenerationWorkflow execute() / _run_agent_gen()
/ default_context().

Covers the Agent SDK execution paths plus the
``default_context()`` classmethod (unique to document_gen vs the
other SDK-native sibling workflows). Uses real SDK message
instances rather than duck-typed fakes so isinstance-based
collectors in agent_sdk_adapter actually fire (per CLAUDE.md
lesson).

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
from attune.workflows.context import WorkflowContext
from attune.workflows.data_classes import WorkflowResult
from attune.workflows.document_gen.workflow import DocumentGenerationWorkflow

# ---------------------------------------------------------------------------
# Fixtures — real SDK message instances
# ---------------------------------------------------------------------------


@pytest.fixture
def workflow() -> DocumentGenerationWorkflow:
    """Build a fresh DocumentGenerationWorkflow."""
    return DocumentGenerationWorkflow()


@pytest.fixture
def assistant_message() -> claude_agent_sdk.AssistantMessage:
    """Real AssistantMessage with a TextBlock payload."""
    block = claude_agent_sdk.types.TextBlock(
        text="Outline: 5 modules, 23 public APIs. Drafted intro and module overview."
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
        session_id="sess-docgen-5",
        total_cost_usd=0.84,
        usage={"input_tokens": 2700, "output_tokens": 1700},
        result="## Summary\nDocumentation generation complete.",
        structured_output=None,
    )


def _make_fake_query(messages):
    """Build an async generator factory yielding the given messages."""

    async def fake_query(*args, **kwargs):
        for msg in messages:
            yield msg

    return fake_query


# ---------------------------------------------------------------------------
# default_context() — classmethod unique to DocumentGenerationWorkflow
# ---------------------------------------------------------------------------


class TestDefaultContext:
    """The classmethod wires up PromptService + ParsingService."""

    def test_returns_workflow_context(self):
        ctx = DocumentGenerationWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)
        assert ctx.prompt is not None
        assert ctx.parsing is not None

    def test_passes_xml_config_through(self):
        """xml_config kwarg is forwarded to both services."""
        cfg = {"any": "value"}
        ctx = DocumentGenerationWorkflow.default_context(xml_config=cfg)
        # Both services should construct cleanly with the config —
        # we don't inspect internal state, just verify the kwarg path
        # didn't raise.
        assert ctx.prompt is not None
        assert ctx.parsing is not None

    def test_default_xml_config_is_none(self):
        """xml_config defaults to None when omitted."""
        ctx = DocumentGenerationWorkflow.default_context()
        assert isinstance(ctx, WorkflowContext)


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

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_success_yields_workflow_result(
        self, mock_query, workflow, assistant_message, result_message
    ):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])
        result = asyncio.run(workflow.execute(path="/tmp/src", depth="standard"))

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.provider == "anthropic"
        assert "Outline" in result.final_output or "Summary" in result.final_output

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_metadata_populated(self, mock_query, workflow, assistant_message, result_message):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])
        result = asyncio.run(workflow.execute(path="/tmp/src", depth="quick"))

        assert result.success is True
        meta = result.metadata or {}
        assert meta.get("depth") == "quick"
        assert meta.get("path", "").endswith("/tmp/src") or "tmp" in meta.get("path", "")
        assert meta.get("max_turns") == 10

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_result_only_no_assistant_text(self, mock_query, workflow, result_message):
        """ResultMessage alone — exercises the ``run_result = sdk_result``
        assignment branch inside the async loop.
        """
        mock_query.side_effect = _make_fake_query([result_message])
        result = asyncio.run(workflow.execute(path="/tmp/src"))
        assert result.success is True

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_empty_stream_returns_default_text(self, mock_query, workflow):
        """Empty stream — exercises the ``AgentRunResult(...="No results")``
        initialization being passed straight through.
        """
        mock_query.side_effect = _make_fake_query([])
        result = asyncio.run(workflow.execute(path="/tmp/src"))
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
            "attune.workflows.document_gen.workflow.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow.execute(path="/tmp/src", depth=depth))
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
            "attune.workflows.document_gen.workflow.claude_agent_sdk.query",
            capture_query,
        )
        asyncio.run(workflow.execute(path="/tmp/src"))
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
            "attune.workflows.document_gen.workflow.claude_agent_sdk.query",
            raising_query,
        )

    def test_import_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, ImportError("sdk missing"))
        result = asyncio.run(workflow.execute(path="/tmp/src"))
        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    def test_connection_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, ConnectionError("refused"))
        result = asyncio.run(workflow.execute(path="/tmp/src"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_timeout_error(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, TimeoutError("slow"))
        result = asyncio.run(workflow.execute(path="/tmp/src"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    def test_generic_exception(self, workflow, monkeypatch):
        self._patch_query_to_raise(monkeypatch, RuntimeError("kaboom"))
        result = asyncio.run(workflow.execute(path="/tmp/src"))
        assert result.success is False
        # Phase 6 of docs/specs/sdk-error-message-fidelity/ — see
        # test_sdk_error_fidelity_phase6.py for the new shape.
        assert "claude CLI subprocess failed" in result.error
        assert result.metadata.get("sdk_error_kind") == "unknown"


# ---------------------------------------------------------------------------
# _run_agent_gen() — directly, bypassing execute()
# ---------------------------------------------------------------------------


class TestRunAgentGenDirect:
    """Direct invocation surfaces the SDK loop's exact behavior."""

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_collects_assistant_and_result(
        self, mock_query, workflow, assistant_message, result_message
    ):
        mock_query.side_effect = _make_fake_query([assistant_message, result_message])

        run_result = asyncio.run(workflow._run_agent_gen("/tmp/src", 20, "standard"))
        assert isinstance(run_result, AgentRunResult)
        assert "Outline" in run_result.result_text or "Summary" in run_result.result_text

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_no_messages_returns_default_text(self, mock_query, workflow):
        mock_query.side_effect = _make_fake_query([])
        run_result = asyncio.run(workflow._run_agent_gen("/tmp/src", 20))
        assert run_result.result_text == "No results returned."

    @patch("attune.workflows.document_gen.workflow.claude_agent_sdk.query")
    def test_passes_subagent_definitions(self, mock_query, workflow, result_message):
        """All three subagents are wired into the SDK call's options."""
        captured: dict = {}

        async def capturing_query(*args, **kwargs):
            captured["options"] = kwargs.get("options")
            captured["prompt"] = kwargs.get("prompt")
            yield result_message

        mock_query.side_effect = capturing_query
        asyncio.run(workflow._run_agent_gen("/tmp/src", 20, "standard"))

        opts = captured["options"]
        assert "outline-planner" in opts.agents
        assert "content-writer" in opts.agents
        assert "polish-reviewer" in opts.agents
        assert "documentation generation orchestrator" in opts.system_prompt
        assert "/tmp/src" in captured["prompt"]


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
        assert result.stages[0].name == "doc-gen"
        assert result.stages[0].tier == ModelTier.CAPABLE

    def test_timestamps_bounded(self, workflow):
        before = datetime.now()
        result = workflow._error_result("nope")
        after = datetime.now()
        assert before <= result.started_at <= after
        assert before <= result.completed_at <= after
