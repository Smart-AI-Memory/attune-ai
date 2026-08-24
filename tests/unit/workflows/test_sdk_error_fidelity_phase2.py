"""Tests for sdk-error-fidelity Phase 2 workflow wiring.

Covers Task 2.4 of docs/specs/sdk-error-message-fidelity/tasks.md:

- code-review surfaces the real cause on subprocess failure
  (not the legacy three-cause menu)
- dependency-check surfaces the real cause on subprocess failure
- _error_result on BaseWorkflow threads sdk_stderr + sdk_error_kind
  into WorkflowResult.metadata

The Phase 2 contract:

1. Workflow's broad-except branch calls capture_subprocess_failure +
   classify_subprocess_failure.
2. Returns a typed SdkSubprocessError message via format_user_message.
3. Threads sdk_stderr + sdk_error_kind onto _error_result via
   metadata, so Phase 3's persistence + render layer can surface
   them on the run-view page.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest


def _make_failing_sdk():
    """Build a mock claude_agent_sdk module whose query raises."""
    mock_sdk = MagicMock()
    mock_sdk.query = MagicMock(side_effect=RuntimeError("Command failed"))
    mock_sdk.ClaudeAgentOptions = MagicMock()
    mock_sdk.AgentDefinition = MagicMock()
    return mock_sdk


class TestCodeReviewPhase2:
    """code_review.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """When capture_subprocess_failure returns api_quota stderr, the
        workflow returns 'API quota reached' (not the legacy menu)."""
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value=(
                    "Error: You have reached your specified API usage limits. "
                    "Regain access on 2026-06-01."
                ),
            ),
        ):
            from attune.workflows.code_review import CodeReviewWorkflow

            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert "API quota reached" in (result.error or "")
        assert result.metadata.get("sdk_error_kind") == "api_quota"
        assert "specified API usage limits" in (result.metadata.get("sdk_stderr") or "")
        # Legacy three-cause menu must NOT appear.
        assert "ANTHROPIC_API_KEY" not in (result.error or "")
        assert "isn't installed" not in (result.error or "")

    @pytest.mark.asyncio
    async def test_surfaces_auth_classification(self):
        """401 stderr → 'auth invalid' classification."""
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.code_review.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value="401 Unauthorized: invalid api key",
            ),
        ):
            from attune.workflows.code_review import CodeReviewWorkflow

            wf = CodeReviewWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()


class TestDependencyCheckPhase2:
    """dependency_check.py surfaces real cause on subprocess failure."""

    def test_surfaces_real_cause_on_subprocess_failure(self):
        """Same Phase 2 contract for dependency-check workflow."""
        mock_sdk = _make_failing_sdk()
        with (
            patch(
                "attune.workflows.dependency_check.claude_agent_sdk",
                mock_sdk,
            ),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value="429 Too Many Requests: rate limit exceeded",
            ),
        ):
            from attune.workflows.dependency_check import (
                DependencyCheckWorkflow,
            )

            wf = DependencyCheckWorkflow()
            result = asyncio.run(wf.execute(path="/tmp/proj"))

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "rate_limit"
        assert "rate" in (result.error or "").lower()


class TestErrorResultThreading:
    """_error_result on BaseWorkflow threads the two new kwargs into
    WorkflowResult.metadata."""

    def test_threads_sdk_stderr_into_metadata(self):
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        result = wf._error_result(
            "test error",
            sdk_stderr="captured stderr",
            sdk_error_kind="api_quota",
        )
        assert result.metadata["sdk_stderr"] == "captured stderr"
        assert result.metadata["sdk_error_kind"] == "api_quota"

    def test_omits_metadata_when_kwargs_unset(self):
        """Back-compat: callers not passing the SDK kwargs get empty
        metadata, matching pre-Phase-2 behavior."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        result = wf._error_result("test error")
        assert result.metadata == {}

    def test_threads_only_one_kwarg(self):
        """Passing only one of the two kwargs surfaces just that key."""
        from attune.workflows.code_review import CodeReviewWorkflow

        wf = CodeReviewWorkflow()
        result = wf._error_result("test error", sdk_error_kind="auth")
        assert result.metadata == {"sdk_error_kind": "auth"}
