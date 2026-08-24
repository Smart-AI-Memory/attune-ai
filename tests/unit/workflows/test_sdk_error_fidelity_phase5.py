"""Tests for sdk-error-fidelity Phase 5 workflow wiring.

Covers Task 5.1 of docs/specs/sdk-error-message-fidelity/tasks.md
for the 5 workflows still using the legacy ``sdk_error_message``
helper at Phase 5 entry:

- simplify-code
- deep-review (the morning-2026-06-01 failure case)
- research-synthesis
- rag-code-gen
- release-prep

Same Phase 2/4 contract — workflow's broad-except branch calls
capture_subprocess_failure + classify_subprocess_failure, returns
a typed SdkSubprocessError message, and threads sdk_stderr +
sdk_error_kind onto _error_result.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_failing_sdk():
    """Build a mock claude_agent_sdk module whose query raises."""
    mock_sdk = MagicMock()
    mock_sdk.query = MagicMock(side_effect=RuntimeError("Command failed"))
    mock_sdk.ClaudeAgentOptions = MagicMock()
    mock_sdk.AgentDefinition = MagicMock()
    return mock_sdk


class TestSimplifyCodePhase5:
    """simplify_code.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.simplify_code.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.sdk_errors.capture_subprocess_failure",
                return_value="401 Unauthorized: invalid api key",
            ),
        ):
            from attune.workflows.simplify_code import SimplifyCodeWorkflow

            wf = SimplifyCodeWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()
        assert "ANTHROPIC_API_KEY" not in (result.error or "")


class TestDeepReviewPhase5:
    """deep_review.py surfaces real cause — THE morning-2026-06-01 case.

    Patrick ran `attune workflow run deep-review` against an expired
    `claude` CLI auth token. The legacy menu blamed
    `ANTHROPIC_API_KEY unset`, `claude not on PATH`, and `SDK version
    mismatch` — all wrong. The real cause (401 auth) was discoverable
    only by running `claude -p` directly. This test pins the new
    behavior.
    """

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.deep_review.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.sdk_errors.capture_subprocess_failure",
                return_value=(
                    "Failed to authenticate. API Error: 401 Invalid " "authentication credentials"
                ),
            ),
        ):
            from attune.workflows.deep_review import DeepReviewAgentSDKWorkflow

            wf = DeepReviewAgentSDKWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()
        # The legacy three-cause menu must NOT appear.
        assert "ANTHROPIC_API_KEY" not in (result.error or "")
        assert "isn't installed" not in (result.error or "")
        assert "SDK version" not in (result.error or "")


class TestResearchSynthesisPhase5:
    """research_synthesis.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.research_synthesis.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.sdk_errors.capture_subprocess_failure",
                return_value="429 Too Many Requests: rate limit exceeded",
            ),
        ):
            from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

            wf = ResearchSynthesisWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "rate_limit"
        assert "rate" in (result.error or "").lower()


class TestRagCodeGenPhase5:
    """rag_code_gen.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        mock_sdk = _make_failing_sdk()
        # RAG pipeline runs BEFORE the SDK query — mock it so execution
        # reaches the SDK error path instead of failing on RAG init
        # (which raises if attune-rag's [attune-help] extra isn't
        # installed in the test env).
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = MagicMock(
            citations=[],
            grounded_prompt="prompt",
            context="",
            metadata={},
        )
        with (
            patch("attune.workflows.rag_code_gen.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.sdk_errors.capture_subprocess_failure",
                return_value=("Error: You have reached your specified API usage limits."),
            ),
            patch(
                "attune.workflows.rag_code_gen.RagCodeGenWorkflow._get_pipeline",
                return_value=mock_pipeline,
            ),
        ):
            from attune.workflows.rag_code_gen import RagCodeGenWorkflow

            wf = RagCodeGenWorkflow()
            result = await wf.execute(query="how do I use the test framework?")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "api_quota"
        assert "API quota reached" in (result.error or "")
        assert "ANTHROPIC_API_KEY" not in (result.error or "")


class TestReleasePrepPhase5:
    """release_prep.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.release_prep.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.sdk_errors.capture_subprocess_failure",
                return_value="401 Unauthorized",
            ),
        ):
            from attune.workflows.release_prep import ReleasePreparationWorkflow

            wf = ReleasePreparationWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()
