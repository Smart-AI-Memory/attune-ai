"""Tests for sdk-error-fidelity Phase 4 workflow wiring.

Covers Task 4.2 of docs/specs/sdk-error-message-fidelity/tasks.md:

- bug-predict surfaces the real cause on subprocess failure
- perf-audit surfaces the real cause on subprocess failure
- refactor-plan surfaces the real cause on subprocess failure
- security-audit surfaces the real cause on subprocess failure

Same Phase 2 contract as code-review / dependency-check (see
test_sdk_error_fidelity_phase2.py for the original pattern):

1. Workflow's broad-except branch calls capture_subprocess_failure
   + classify_subprocess_failure.
2. Returns a typed SdkSubprocessError message via format_user_message.
3. Threads sdk_stderr + sdk_error_kind onto _error_result via
   metadata so Phase 3's persistence + render layer surfaces them
   on the run-view page.
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


class TestBugPredictPhase4:
    """bug_predict.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """api_quota stderr → 'API quota reached' (not legacy menu)."""
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.bug_predict.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value=(
                    "Error: You have reached your specified API usage limits. "
                    "Regain access on 2026-06-01."
                ),
            ),
        ):
            from attune.workflows.bug_predict import BugPredictionWorkflow

            wf = BugPredictionWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert "API quota reached" in (result.error or "")
        assert result.metadata.get("sdk_error_kind") == "api_quota"
        assert "specified API usage limits" in (result.metadata.get("sdk_stderr") or "")
        # Legacy three-cause menu must NOT appear.
        assert "ANTHROPIC_API_KEY" not in (result.error or "")
        assert "isn't installed" not in (result.error or "")


class TestPerfAuditPhase4:
    """perf_audit.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """401 stderr → 'auth invalid' classification."""
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.perf_audit.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value="401 Unauthorized: invalid api key",
            ),
        ):
            from attune.workflows.perf_audit import PerformanceAuditWorkflow

            wf = PerformanceAuditWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()
        assert "ANTHROPIC_API_KEY" not in (result.error or "")


class TestRefactorPlanPhase4:
    """refactor_plan.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """429 stderr → 'rate_limit' classification."""
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.refactor_plan.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value="429 Too Many Requests: rate limit exceeded",
            ),
        ):
            from attune.workflows.refactor_plan import RefactorPlanWorkflow

            wf = RefactorPlanWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "rate_limit"
        assert "rate" in (result.error or "").lower()


class TestSecurityAuditPhase4:
    """security_audit.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """api_quota stderr → 'API quota reached' (the morning-2026-06-01 case)."""
        mock_sdk = _make_failing_sdk()
        with (
            patch("attune.workflows.security_audit.claude_agent_sdk", mock_sdk),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value=(
                    "Failed to authenticate. API Error: 401 Invalid " "authentication credentials"
                ),
            ),
        ):
            from attune.workflows.security_audit import SecurityAuditWorkflow

            wf = SecurityAuditWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        # This is the exact morning-2026-06-01 failure mode — auth invalid.
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()
        # The legacy three-cause menu listed ANTHROPIC_API_KEY among
        # possibilities — Phase 4 surfaces the real 401 cause directly.
        assert "ANTHROPIC_API_KEY" not in (result.error or "")
