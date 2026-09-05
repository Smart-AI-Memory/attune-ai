"""Behavioral tests for DeepReviewAgentSDKWorkflow.

Tests the multi-pass deep review workflow covering attributes,
successful execution, depth configuration, focus filtering,
and subagent definitions.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.data_classes import WorkflowResult

SAMPLE_DEEP_REVIEW_OUTPUT = (
    "## Summary\n"
    "Code health score: 72/100. Several security and quality "
    "issues found. Test coverage has significant gaps.\n\n"
    "## Security\n"
    "- eval() usage in src/utils.py:45 — CRITICAL\n"
    "- Hardcoded API key in src/config.py:12 — HIGH\n\n"
    "## Quality\n"
    "- Function process_data() exceeds 80 lines — MEDIUM\n"
    "- Bare except: in src/handler.py:33 — HIGH\n\n"
    "## Test Gaps\n"
    "- No tests for error paths in src/handler.py — HIGH\n"
    "- Missing edge case tests for empty input — MEDIUM\n\n"
    "## Suggestions\n"
    "- Replace eval() with ast.literal_eval() immediately\n"
    "- Move API key to environment variable\n"
    "- Add error path tests for handler.py\n"
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
class TestDeepReviewAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        """Given the workflow class, name is 'deep-review'."""
        from attune.workflows.deep_review import (
            DeepReviewAgentSDKWorkflow,
        )

        wf = DeepReviewAgentSDKWorkflow()
        assert wf.name == "deep-review"

    def test_workflow_has_description(self) -> None:
        """Given the workflow class, description is non-empty."""
        from attune.workflows.deep_review import (
            DeepReviewAgentSDKWorkflow,
        )

        wf = DeepReviewAgentSDKWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        """Given the workflow class, stages list contains 'deep-review'."""
        from attune.workflows.deep_review import (
            DeepReviewAgentSDKWorkflow,
        )

        wf = DeepReviewAgentSDKWorkflow()
        assert isinstance(wf.stages, list)
        assert "deep-review" in wf.stages


@pytest.mark.unit
class TestDeepReviewExecution:
    """Test successful execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_returns_success_on_valid_response(self) -> None:
        """Given mocked SDK returning review text, execute succeeds."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(SAMPLE_DEEP_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.stages is not None
        assert len(result.stages) == 3
        assert result.summary is not None
        assert len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_metadata_includes_workflow_name(self) -> None:
        """Given successful execution, metadata contains workflow name."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(SAMPLE_DEEP_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/")

        assert result.metadata.get("workflow") == "deep-review"

    @pytest.mark.asyncio
    async def test_handles_sdk_exception_gracefully(self) -> None:
        """Given SDK raises exception, execute returns error result."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(side_effect=RuntimeError("SDK crashed"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        # Phase 5 — see test_sdk_error_fidelity_phase5.py.
        assert "claude CLI subprocess failed" in (result.error or "")
        assert result.metadata.get("sdk_error_kind") == "unknown"

    @pytest.mark.asyncio
    async def test_handles_connection_error(self) -> None:
        """Given SDK raises ConnectionError, execute returns error."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(side_effect=ConnectionError("Network down"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert "connection failed" in (result.error or "").lower()


@pytest.mark.unit
class TestDeepReviewDepth:
    """Test depth configuration affects max_turns."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("depth", "expected_turns"),
        [
            ("quick", 15),
            ("standard", 30),
            ("deep", 50),
        ],
    )
    async def test_depth_sets_correct_max_turns(self, depth: str, expected_turns: int) -> None:
        """Given a depth value, correct max_turns is passed to SDK."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(SAMPLE_DEEP_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            await wf.execute(path="src/", depth=depth)

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == expected_turns

    @pytest.mark.asyncio
    async def test_unknown_depth_defaults_to_thirty(self) -> None:
        """Given unknown depth, max_turns defaults to 30."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(SAMPLE_DEEP_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            await wf.execute(path="src/", depth="unknown_depth")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == 30


@pytest.mark.unit
class TestDeepReviewFocus:
    """Test focus filtering selects specific subagents."""

    @pytest.mark.asyncio
    async def test_focus_security_only_creates_one_agent(self) -> None:
        """Given focus=['security'], only security-reviewer is created."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(SAMPLE_DEEP_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/", focus=["security"])

        assert result.success is True
        # Only 1 subagent stage should be created
        assert len(result.stages) == 1

    @pytest.mark.asyncio
    async def test_focus_multiple_passes(self) -> None:
        """Given focus=['security', 'test-gaps'], two agents created."""
        mock_sdk = MagicMock()
        mock_sdk.query = _sdk_stream(SAMPLE_DEEP_REVIEW_OUTPUT)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with patch(
            "attune.workflows.deep_review.claude_agent_sdk",
            mock_sdk,
        ):
            from attune.workflows.deep_review import (
                DeepReviewAgentSDKWorkflow,
            )

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/", focus=["security", "test-gaps"])

        assert result.success is True
        assert len(result.stages) == 2

    @pytest.mark.asyncio
    async def test_invalid_focus_returns_error(self) -> None:
        """Given invalid focus values, execute returns error."""
        from attune.workflows.deep_review import (
            DeepReviewAgentSDKWorkflow,
        )

        wf = DeepReviewAgentSDKWorkflow()
        result = await wf.execute(path="src/", focus=["invalid"])

        assert result.success is False
        assert "Invalid focus" in (result.error or "")


@pytest.mark.unit
class TestDeepReviewSubagents:
    """Test subagent definitions."""

    def test_three_subagents_defined(self) -> None:
        """Given the module constants, exactly 3 subagents defined."""
        from attune.workflows.deep_review import (
            _SUBAGENT_NAMES,
        )

        assert len(_SUBAGENT_NAMES) == 3

    def test_subagent_names_match_expected(self) -> None:
        """Given module constants, subagent names match expected set."""
        from attune.workflows.deep_review import (
            _SUBAGENT_NAMES,
        )

        expected = {
            "security-reviewer",
            "quality-reviewer",
            "test-gap-reviewer",
        }
        assert set(_SUBAGENT_NAMES) == expected

    def test_all_subagents_have_definitions(self) -> None:
        """Given module constants, all subagents have prompt defs."""
        from attune.workflows.deep_review import (
            _SUBAGENT_DEFS,
            _SUBAGENT_NAMES,
        )

        for name in _SUBAGENT_NAMES:
            assert name in _SUBAGENT_DEFS
            assert "description" in _SUBAGENT_DEFS[name]
            assert "prompt" in _SUBAGENT_DEFS[name]

    def test_subagent_prompts_contain_path_placeholder(self) -> None:
        """Given subagent defs, all prompts use {path} placeholder."""
        from attune.workflows.deep_review import (
            _SUBAGENT_DEFS,
        )

        for name, defn in _SUBAGENT_DEFS.items():
            assert "{path}" in defn["prompt"], f"{name} prompt missing {{path}} placeholder"
