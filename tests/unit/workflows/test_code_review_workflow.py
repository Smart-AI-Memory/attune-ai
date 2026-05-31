"""Tests for CodeReviewWorkflow (SDK-native).

This test suite covers:
- Initialization and class attributes
- SDK-native execution with mocked SDK
- Depth configuration
- Error handling
- Re-exported utilities

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.base import ModelTier
from attune.workflows.code_review import CodeReviewWorkflow
from attune.workflows.data_classes import WorkflowResult

# ============================================================================
# Test: Workflow Initialization
# ============================================================================


@pytest.mark.unit
class TestWorkflowInitialization:
    """Tests for workflow initialization and configuration."""

    def test_default_initialization(self):
        """Test workflow initializes with correct defaults."""
        wf = CodeReviewWorkflow()
        assert wf.name == "code-review"

    def test_stages_is_single_agent_review(self):
        """Test stages list contains only 'agent-review'."""
        wf = CodeReviewWorkflow()
        assert wf.stages == ["agent-review"]

    def test_tier_map_is_capable(self):
        """Test tier map assigns CAPABLE to agent-review."""
        wf = CodeReviewWorkflow()
        assert wf.tier_map["agent-review"] == ModelTier.CAPABLE

    def test_description_mentions_agent_sdk(self):
        """Test description mentions Agent SDK."""
        wf = CodeReviewWorkflow()
        assert "Agent SDK" in wf.description


# ============================================================================
# Test: SDK-Native Execution
# ============================================================================


@pytest.mark.unit
class TestWorkflowExecution:
    """Tests for end-to-end workflow execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_execute_returns_workflow_result(self):
        """Test execute returns a WorkflowResult on success."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nScore: 90/100"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk):
            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execute_without_path_returns_error(self):
        """Test execute with no path returns error result."""
        wf = CodeReviewWorkflow()
        result = await wf.execute()

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "path" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_with_empty_path_returns_error(self):
        """Test execute with empty path returns error result."""
        wf = CodeReviewWorkflow()
        result = await wf.execute(path="")

        assert isinstance(result, WorkflowResult)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_execute_handles_runtime_error(self):
        """Test execute catches RuntimeError from SDK and returns the
        Phase 2 typed error result (sdk-error-message-fidelity spec)."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(side_effect=RuntimeError("boom"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk):
            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        # Phase 2 surfaces the classifier's user-facing message instead
        # of the raw exception type. The mock exception has no argv
        # shape, so the classifier falls back to "unknown" with a
        # synthetic capture-failure stderr inlined.
        assert "claude CLI subprocess failed" in (result.error or "")
        assert result.metadata.get("sdk_error_kind") == "unknown"
        assert "sdk_stderr" in result.metadata

    @pytest.mark.asyncio
    async def test_execute_handles_connection_error(self):
        """Test execute catches ConnectionError from SDK."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(side_effect=ConnectionError("no network"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk):
            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "connection" in (result.error or "").lower()

    @pytest.mark.asyncio
    async def test_execute_passes_depth_to_sdk(self):
        """Test execute passes depth-based max_turns to SDK."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk):
            wf = CodeReviewWorkflow()
            await wf.execute(path="src/", depth="deep")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call.kwargs.get("max_turns") == 40

    @pytest.mark.asyncio
    async def test_execute_result_has_four_stages(self):
        """Test successful result has 4 stages (one per subagent)."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk):
            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert len(result.stages) == 4

    @pytest.mark.asyncio
    async def test_execute_result_has_metadata(self):
        """Test successful result includes path and depth metadata."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk):
            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/", depth="quick")

        assert result.metadata is not None
        assert result.metadata.get("depth") == "quick"
        assert result.metadata.get("max_turns") == 10


# ============================================================================
# Test: Report Formatting (re-exported)
# ============================================================================
