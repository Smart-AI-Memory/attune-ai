"""Tests for TestAuditWorkflow execute(), _run_agent_audit(), _error_result().

Covers the Agent SDK execution paths that are mocked to avoid real API calls.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.data_classes import WorkflowResult


@pytest.fixture
def workflow():
    """Create a TestAuditWorkflow instance."""
    from attune.workflows.test_audit.workflow import TestAuditWorkflow

    return TestAuditWorkflow()


@pytest.fixture
def mock_result_message():
    """Create a mock ResultMessage from claude_agent_sdk."""
    msg = MagicMock()
    msg.result = "## Summary\nAudit complete. Coverage: 85%."
    msg.structured_output = None
    msg.total_cost_usd = 0.18
    msg.usage = {"input_tokens": 1500, "output_tokens": 600}
    msg.duration_ms = 6000
    msg.duration_api_ms = 5000
    msg.num_turns = 4
    msg.session_id = "audit-session-123"
    msg.is_error = False
    return msg


class TestTestAuditExecute:
    """Tests for TestAuditWorkflow.execute()."""

    def test_execute_missing_path_returns_error(self, workflow):
        """execute() with no path returns error result."""
        result = asyncio.run(workflow.execute())
        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "path argument is required" in result.error

    def test_execute_empty_path_returns_error(self, workflow):
        """execute() with empty path returns error result."""
        result = asyncio.run(workflow.execute(path=""))
        assert result.success is False
        assert "path argument is required" in result.error

    @patch("attune.workflows.test_audit.workflow.claude_agent_sdk")
    def test_execute_success(self, mock_sdk, workflow, mock_result_message):
        """execute() with valid src_path returns successful result."""
        import claude_agent_sdk

        mock_result_message.__class__ = type(claude_agent_sdk.ResultMessage)

        async def fake_query(*args, **kwargs):
            yield mock_result_message

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = claude_agent_sdk.ClaudeAgentOptions
        mock_sdk.AgentDefinition = claude_agent_sdk.AgentDefinition
        mock_sdk.ResultMessage = claude_agent_sdk.ResultMessage
        mock_sdk.AssistantMessage = claude_agent_sdk.AssistantMessage

        result = asyncio.run(workflow.execute(src_path="/tmp/test", depth="quick"))
        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.provider == "anthropic"

    @patch("attune.workflows.test_audit.workflow.claude_agent_sdk")
    def test_execute_import_error(self, mock_sdk, workflow):
        """execute() handles ImportError gracefully."""

        async def fake_query(*args, **kwargs):
            raise ImportError("No module named 'claude_agent_sdk'")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(src_path="/tmp/test"))
        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    @patch("attune.workflows.test_audit.workflow.claude_agent_sdk")
    def test_execute_connection_error(self, mock_sdk, workflow):
        """execute() handles ConnectionError gracefully."""

        async def fake_query(*args, **kwargs):
            raise ConnectionError("Connection refused")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(src_path="/tmp/test"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    @patch("attune.workflows.test_audit.workflow.claude_agent_sdk")
    def test_execute_timeout_error(self, mock_sdk, workflow):
        """execute() handles TimeoutError gracefully."""

        async def fake_query(*args, **kwargs):
            raise TimeoutError("Request timed out")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(src_path="/tmp/test"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    @patch("attune.workflows.test_audit.workflow.claude_agent_sdk")
    def test_execute_generic_exception(self, mock_sdk, workflow):
        """execute() handles unexpected exceptions gracefully."""

        async def fake_query(*args, **kwargs):
            raise RuntimeError("Unexpected SDK error")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(src_path="/tmp/test"))
        assert result.success is False
        # Phase 6 of docs/specs/sdk-error-message-fidelity/ replaced the
        # hand-rolled "Agent SDK error: <type>: <msg>" leak with the
        # structured SdkSubprocessError message. Mock exceptions with
        # no argv shape classify as "unknown".
        assert "claude CLI subprocess failed" in result.error
        assert result.metadata.get("sdk_error_kind") == "unknown"

    def test_execute_default_depth(self, workflow):
        """execute() defaults to 'standard' depth (20 turns)."""
        with patch.object(workflow, "_run_agent_audit", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(src_path="/tmp/test"))
            args = mock_run.call_args
            assert args[0][1] == 20

    def test_execute_deep_depth(self, workflow):
        """execute() with depth='deep' uses 40 max_turns."""
        with patch.object(workflow, "_run_agent_audit", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(src_path="/tmp/test", depth="deep"))
            args = mock_run.call_args
            assert args[0][1] == 40

    def test_execute_quick_depth(self, workflow):
        """execute() with depth='quick' uses 10 max_turns."""
        with patch.object(workflow, "_run_agent_audit", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(src_path="/tmp/test", depth="quick"))
            args = mock_run.call_args
            assert args[0][1] == 10


class TestTestAuditErrorResult:
    """Tests for TestAuditWorkflow._error_result()."""

    def test_error_result_structure(self, workflow):
        """_error_result() returns well-formed WorkflowResult."""
        result = workflow._error_result("something broke")
        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert result.error == "something broke"
        assert result.total_duration_ms == 0
        assert result.cost_report.total_cost == 0.0
        assert result.provider == "anthropic"

    def test_error_result_has_stage(self, workflow):
        """_error_result() includes workflow name as stage name."""
        result = workflow._error_result("test error")
        assert len(result.stages) == 1
        assert result.stages[0].name == workflow.name
        assert result.stages[0].tier == ModelTier.CAPABLE

    def test_error_result_timestamps(self, workflow):
        """_error_result() sets started_at and completed_at."""
        before = datetime.now()
        result = workflow._error_result("test")
        after = datetime.now()
        assert before <= result.started_at <= after
        assert before <= result.completed_at <= after


class TestExecutePathKwarg:
    """Tests for the `path=` kwarg migration in `execute()`.

    PR-3 of workflow-path-arg-unification (2026-05-13) renames the
    `src_path=` kwarg to `path=`, keeping the legacy name as a
    deprecated alias for one major version. The `required=True`
    semantic in `PATH_ARG_REGISTRY` is preserved — calling
    `execute()` with no path still returns an error.
    """

    @pytest.fixture
    def _mock_sdk(self, mock_result_message):
        """Patch claude_agent_sdk.query to short-circuit the audit."""
        with patch("attune.workflows.test_audit.workflow.claude_agent_sdk") as mock_sdk:

            async def fake_query(**_kwargs):
                yield mock_result_message

            mock_sdk.query = fake_query
            mock_sdk.ClaudeAgentOptions = MagicMock()
            mock_sdk.AgentDefinition = MagicMock()
            yield mock_sdk

    def test_execute_accepts_path_kwarg(self, workflow, _mock_sdk):
        """execute(path=...) runs without DeprecationWarning."""
        import warnings as _warnings

        with _warnings.catch_warnings(record=True) as captured:
            _warnings.simplefilter("always")
            result = asyncio.run(workflow.execute(path="/tmp/test"))
        deprecations = [w for w in captured if issubclass(w.category, DeprecationWarning)]
        assert deprecations == []
        assert result.success is True

    def test_execute_legacy_src_path_warns(self, workflow, _mock_sdk):
        """execute(src_path=...) emits DeprecationWarning AND still runs."""
        with pytest.warns(DeprecationWarning, match="src_path"):
            result = asyncio.run(workflow.execute(src_path="/tmp/test"))
        assert result.success is True

    def test_execute_both_kwargs_path_wins(self, workflow, _mock_sdk):
        """execute(path=A, src_path=B) uses A and warns about the conflict.

        The conflict warning is the load-bearing assertion. We don't
        check the exact resolved-path string in metadata because
        `Path.resolve()` prepends a drive letter on Windows (e.g.
        `/tmp/via_path` → `D:\\tmp\\via_path`), per the cross-platform
        lesson in CLAUDE.md. We assert instead that the LEGACY value
        did not make it through.
        """
        with pytest.warns(DeprecationWarning, match="both"):
            result = asyncio.run(workflow.execute(path="/tmp/via_path", src_path="/tmp/legacy"))
        assert result.success is True
        resolved = str(result.metadata.get("src_path", ""))
        assert "legacy" not in resolved, (
            f"`src_path=` should have been overridden by `path=`; "
            f"resolved metadata path was: {resolved!r}"
        )

    def test_execute_no_path_returns_required_error(self, workflow):
        """execute() with no path returns the required-arg error.

        Confirms `PATH_ARG_REGISTRY`'s `required=True` semantic
        carries into the workflow body: a path is still required
        after the rename.
        """
        result = asyncio.run(workflow.execute())
        assert result.success is False
        assert "path argument is required" in result.error
