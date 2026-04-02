"""Tests for SimplifyCodeWorkflow execute(), _run_agent_simplify(), _error_result().

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
    """Create a SimplifyCodeWorkflow instance."""
    from attune.workflows.simplify_code import SimplifyCodeWorkflow

    return SimplifyCodeWorkflow()


@pytest.fixture
def mock_result_message():
    """Create a mock ResultMessage from claude_agent_sdk."""
    msg = MagicMock()
    msg.result = "## Summary\nSimplification complete."
    msg.structured_output = None
    msg.total_cost_usd = 0.15
    msg.usage = {"input_tokens": 1000, "output_tokens": 500}
    msg.duration_ms = 5000
    msg.duration_api_ms = 4000
    msg.num_turns = 3
    msg.session_id = "test-session-123"
    msg.is_error = False
    return msg


@pytest.fixture
def mock_assistant_message():
    """Create a mock AssistantMessage from claude_agent_sdk."""
    import claude_agent_sdk

    text_block = MagicMock(spec=claude_agent_sdk.types.TextBlock)
    text_block.text = "Analyzing complexity..."

    msg = MagicMock(spec=claude_agent_sdk.AssistantMessage)
    msg.parent_tool_use_id = None
    msg.content = [text_block]
    return msg


class TestSimplifyCodeExecute:
    """Tests for SimplifyCodeWorkflow.execute()."""

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

    @patch("attune.workflows.simplify_code.claude_agent_sdk")
    def test_execute_success(self, mock_sdk, workflow, mock_result_message):
        """execute() with valid path returns successful result."""
        import claude_agent_sdk

        mock_result_message.__class__ = type(claude_agent_sdk.ResultMessage)

        async def fake_query(*args, **kwargs):
            yield mock_result_message

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = claude_agent_sdk.ClaudeAgentOptions
        mock_sdk.AgentDefinition = claude_agent_sdk.AgentDefinition
        mock_sdk.ResultMessage = claude_agent_sdk.ResultMessage
        mock_sdk.AssistantMessage = claude_agent_sdk.AssistantMessage

        result = asyncio.run(workflow.execute(path="/tmp/test", depth="quick"))
        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.provider == "anthropic"

    @patch("attune.workflows.simplify_code.claude_agent_sdk")
    def test_execute_import_error(self, mock_sdk, workflow):
        """execute() handles ImportError gracefully."""

        async def fake_query(*args, **kwargs):
            raise ImportError("No module named 'claude_agent_sdk'")
            yield  # make it a generator  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(path="/tmp/test"))
        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    @patch("attune.workflows.simplify_code.claude_agent_sdk")
    def test_execute_connection_error(self, mock_sdk, workflow):
        """execute() handles ConnectionError gracefully."""

        async def fake_query(*args, **kwargs):
            raise ConnectionError("Connection refused")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(path="/tmp/test"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    @patch("attune.workflows.simplify_code.claude_agent_sdk")
    def test_execute_timeout_error(self, mock_sdk, workflow):
        """execute() handles TimeoutError gracefully."""

        async def fake_query(*args, **kwargs):
            raise TimeoutError("Request timed out")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(path="/tmp/test"))
        assert result.success is False
        assert "connection failed" in result.error.lower()

    @patch("attune.workflows.simplify_code.claude_agent_sdk")
    def test_execute_generic_exception(self, mock_sdk, workflow):
        """execute() handles unexpected exceptions gracefully."""

        async def fake_query(*args, **kwargs):
            raise RuntimeError("Unexpected SDK error")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(path="/tmp/test"))
        assert result.success is False
        assert "RuntimeError" in result.error

    def test_execute_default_depth(self, workflow):
        """execute() defaults to 'standard' depth."""
        with patch.object(workflow, "_run_agent_simplify", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(path="/tmp/test"))
            mock_run.assert_called_once()
            args = mock_run.call_args
            assert args[0][1] == 20  # standard max_turns

    def test_execute_deep_depth(self, workflow):
        """execute() with depth='deep' uses 40 max_turns."""
        with patch.object(workflow, "_run_agent_simplify", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(path="/tmp/test", depth="deep"))
            args = mock_run.call_args
            assert args[0][1] == 40


class TestSimplifyCodeErrorResult:
    """Tests for SimplifyCodeWorkflow._error_result()."""

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
