"""Tests for TestGenerationWorkflow execute(), _run_agent_gen(), _error_result().

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
    """Create a TestGenerationWorkflow instance."""
    from attune.workflows.test_gen.workflow import TestGenerationWorkflow

    return TestGenerationWorkflow()


@pytest.fixture
def mock_result_message():
    """Create a mock ResultMessage from claude_agent_sdk."""
    msg = MagicMock()
    msg.result = "## Summary\nGenerated 10 test cases."
    msg.structured_output = None
    msg.total_cost_usd = 0.20
    msg.usage = {"input_tokens": 2000, "output_tokens": 800}
    msg.duration_ms = 8000
    msg.duration_api_ms = 7000
    msg.num_turns = 5
    msg.session_id = "test-gen-session"
    msg.is_error = False
    return msg


class TestTestGenExecute:
    """Tests for TestGenerationWorkflow.execute()."""

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

    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
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

    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
    def test_execute_import_error(self, mock_sdk, workflow):
        """execute() handles ImportError gracefully."""

        async def fake_query(*args, **kwargs):
            raise ImportError("No module named 'claude_agent_sdk'")
            yield  # noqa: E501

        mock_sdk.query = fake_query
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        result = asyncio.run(workflow.execute(path="/tmp/test"))
        assert result.success is False
        assert "Agent SDK unavailable" in result.error

    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
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

    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
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

    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
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
        """execute() defaults to 'standard' depth (20 turns)."""
        with patch.object(workflow, "_run_agent_gen", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(path="/tmp/test"))
            args = mock_run.call_args
            assert args[0][1] == 20

    def test_execute_deep_depth(self, workflow):
        """execute() with depth='deep' uses 40 max_turns."""
        with patch.object(workflow, "_run_agent_gen", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(path="/tmp/test", depth="deep"))
            args = mock_run.call_args
            assert args[0][1] == 40

    def test_execute_quick_depth(self, workflow):
        """execute() with depth='quick' uses 10 max_turns."""
        with patch.object(workflow, "_run_agent_gen", new_callable=AsyncMock) as mock_run:
            from attune.workflows.agent_sdk_adapter import AgentRunResult

            mock_run.return_value = AgentRunResult(result_text="done")
            asyncio.run(workflow.execute(path="/tmp/test", depth="quick"))
            args = mock_run.call_args
            assert args[0][1] == 10


class TestTestGenErrorResult:
    """Tests for TestGenerationWorkflow._error_result()."""

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


class TestTestGenMain:
    """Tests for the main() entry point."""

    @patch("attune.workflows.test_gen.workflow.claude_agent_sdk")
    def test_main_runs(self, mock_sdk):
        """main() executes without error."""

        async def fake_query(*args, **kwargs):
            msg = MagicMock()
            msg.result = "Test results"
            msg.structured_output = None
            msg.total_cost_usd = 0.1
            msg.usage = {"input_tokens": 100, "output_tokens": 50}
            msg.duration_ms = 1000
            msg.duration_api_ms = 900
            msg.num_turns = 1
            msg.session_id = "s"
            msg.is_error = False
            import claude_agent_sdk

            msg.__class__ = type(claude_agent_sdk.ResultMessage)
            yield msg

        mock_sdk.query = fake_query
        import claude_agent_sdk

        mock_sdk.ClaudeAgentOptions = claude_agent_sdk.ClaudeAgentOptions
        mock_sdk.AgentDefinition = claude_agent_sdk.AgentDefinition
        mock_sdk.ResultMessage = claude_agent_sdk.ResultMessage
        mock_sdk.AssistantMessage = claude_agent_sdk.AssistantMessage

        # main() uses asyncio.run internally so just verify it doesn't crash
        from attune.workflows.test_gen import workflow as wf_module

        with patch.object(wf_module, "TestGenerationWorkflow") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.execute = AsyncMock(
                return_value=WorkflowResult(
                    success=True,
                    stages=[],
                    final_output="Test output",
                    cost_report=MagicMock(total_cost=0.1, savings=0.0, savings_percent=0.0),
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    total_duration_ms=100,
                    provider="anthropic",
                )
            )
            mock_cls.return_value = mock_instance
            wf_module.main()
