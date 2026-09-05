"""Behavioral tests for CodeReviewWorkflow (SDK-native).

Tests the merged SDK-native code review workflow covering attributes,
successful execution, depth configuration, and subagent definitions.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.data_classes import WorkflowResult

_SAMPLE_CODE_REVIEW_OUTPUT = (
    "## Summary\n"
    "Code health score: 90/100.\n\n"
    "## Security\n- No eval/exec usage found\n\n"
    "## Quality\n- Good test coverage\n\n"
    "## Performance\n- No N+1 patterns detected\n\n"
    "## Architecture\n- Clean module boundaries\n\n"
    "## Suggestions\n1. Consider adding input validation\n"
)


def _sdk_stream(text: str):
    """Return a ``query``-shaped callable yielding one real ResultMessage.

    The hollow ``MagicMock(text=...)`` these tests used to pass yielded
    NO messages, so the adapter fell back to its "No results returned."
    default and ``result.success`` was true no matter what the agent
    said. Emitting a real ResultMessage makes the success assertions
    mean something.
    """
    import claude_agent_sdk

    def factory(*args, **kwargs):
        async def gen():
            yield claude_agent_sdk.ResultMessage(
                subtype="success",
                duration_ms=1000,
                duration_api_ms=900,
                is_error=False,
                num_turns=2,
                session_id="sess-test",
                total_cost_usd=0.01,
                usage={"input_tokens": 10, "output_tokens": 10},
                result=text,
                structured_output=None,
            )

        return gen()

    return factory


@pytest.mark.unit
class TestCodeReviewWorkflowAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        """Given the workflow class, name is 'code-review'."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        assert wf.name == "code-review"

    def test_workflow_has_description(self) -> None:
        """Given the workflow class, description is a non-empty string."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_description_mentions_agent_sdk(self) -> None:
        """Given the workflow class, description mentions Agent SDK."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        assert "Agent SDK" in wf.description

    def test_workflow_has_stages_list(self) -> None:
        """Given the workflow class, stages list contains 'agent-review'."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        assert isinstance(wf.stages, list)
        assert "agent-review" in wf.stages


@pytest.mark.unit
class TestCodeReviewWorkflowExecution:
    """Test successful execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_execute_returns_success_on_valid_sdk_response(self) -> None:
        """Given a mocked SDK returning review text, execute returns success."""
        sample_text = (
            "## Summary\n"
            "Code health score: 85/100. Generally solid codebase.\n\n"
            "## Security\n"
            "- No eval/exec usage found\n\n"
            "## Quality\n"
            "- Good test coverage\n\n"
            "## Performance\n"
            "- No N+1 patterns detected\n\n"
            "## Architecture\n"
            "- Clean module boundaries\n\n"
            "## Suggestions\n"
            "- Consider adding input validation\n"
            "- Run security audit quarterly\n"
        )

        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(sample_text)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.code_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.code_review import CodeReviewWorkflow

            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.stages is not None
        assert len(result.stages) == 4
        assert result.summary is not None
        assert len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_execute_handles_sdk_exception_gracefully(self) -> None:
        """Given SDK raises an exception, execute returns the Phase 2
        typed error result (sdk-error-message-fidelity spec)."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(side_effect=RuntimeError("SDK crashed"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.code_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.code_review import CodeReviewWorkflow

            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        # Phase 2 surfaces the classifier's user-facing message; the
        # mock exception has no recognizable argv shape so the
        # classifier falls back to "unknown".
        assert "claude CLI subprocess failed" in (result.error or "")
        assert result.metadata.get("sdk_error_kind") == "unknown"

    @pytest.mark.asyncio
    async def test_execute_without_path_returns_error(self) -> None:
        """Given no path argument, execute returns error result."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        result = await wf.execute()

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "path" in (result.error or "").lower()


@pytest.mark.unit
class TestCodeReviewWorkflowDepth:
    """Test depth configuration affects max_turns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("depth", "expected_turns"),
        [
            ("quick", 10),
            ("standard", 20),
            ("deep", 40),
        ],
    )
    async def test_depth_sets_correct_max_turns(self, depth: str, expected_turns: int) -> None:
        """Given a depth value, the correct max_turns is passed to SDK."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(_SAMPLE_CODE_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.code_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.code_review import CodeReviewWorkflow

            wf = CodeReviewWorkflow()
            await wf.execute(path="src/", depth=depth)

        # Verify max_turns was passed to ClaudeAgentOptions
        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == expected_turns

    @pytest.mark.asyncio
    async def test_unknown_depth_defaults_to_twenty(self) -> None:
        """Given an unknown depth value, max_turns defaults to 20."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(_SAMPLE_CODE_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.code_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.code_review import CodeReviewWorkflow

            wf = CodeReviewWorkflow()
            await wf.execute(path="src/", depth="unknown_depth")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == 20


@pytest.mark.unit
class TestCodeReviewWorkflowSubagents:
    """Test subagent definitions."""

    def test_four_subagents_defined(self) -> None:
        """Given the module constants, exactly 4 subagents are defined."""
        from attune.workflows.code_review import _SUBAGENT_NAMES

        assert len(_SUBAGENT_NAMES) == 4

    def test_subagent_names_match_expected(self) -> None:
        """Given the module constants, subagent names match expected set."""
        from attune.workflows.code_review import _SUBAGENT_NAMES

        expected = {
            "security-reviewer",
            "quality-reviewer",
            "perf-reviewer",
            "architect-reviewer",
        }
        assert set(_SUBAGENT_NAMES) == expected


@pytest.mark.unit
class TestCodeReviewWorkflowReExports:
    """Test backward-compatible re-exports from code_review module."""

    def test_code_review_steps_accessible(self) -> None:
        """Given the module, CODE_REVIEW_STEPS is importable."""
        from attune.workflows.code_review import CODE_REVIEW_STEPS

        assert "architect_review" in CODE_REVIEW_STEPS
