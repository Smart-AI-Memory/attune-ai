"""Tests for sdk-error-fidelity Phase 6 workflow wiring.

Covers the 3 hand-rolled-message workflows that actually call
`claude_agent_sdk.query()` directly:

- test-audit
- doc-audit
- doc-gen (document_gen)

Same contract as Phase 2/4/5: workflow's broad-except branch calls
capture_subprocess_failure + classify_subprocess_failure, returns
a typed SdkSubprocessError message, and threads sdk_stderr +
sdk_error_kind onto _error_result.

**Spec scope correction (documented in PR #549 + #549 follow-up):**
Phase 6 was originally named to cover `test-audit`, `doc-audit`,
`doc-gen`, `discovery-sweep`, `secure-release`. During implementation
we found that `discovery-sweep` and `secure-release` are pipeline
coordinators with no direct `claude_agent_sdk.query()` call — their
error surface is fundamentally different (sub-workflow failure
aggregation). They'd need a Phase 7 if typed-kind errors are ever
wanted at the pipeline level. Phase 6 ships the actual 3 SDK callers.
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


class TestTestAuditPhase6:
    """test_audit/workflow.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """401 stderr → 'auth invalid' classification."""
        mock_sdk = _make_failing_sdk()
        with (
            patch(
                "attune.workflows.test_audit.workflow.claude_agent_sdk",
                mock_sdk,
            ),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value="401 Unauthorized: invalid api key",
            ),
        ):
            from attune.workflows.test_audit.workflow import TestAuditWorkflow

            wf = TestAuditWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "auth"
        assert "auth invalid" in (result.error or "").lower()
        # Legacy hand-rolled "Agent SDK error: RuntimeError" must NOT appear.
        assert "Agent SDK error:" not in (result.error or "")


class TestDocAuditPhase6:
    """doc_audit/workflow.py surfaces real cause on subprocess failure."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """429 stderr → 'rate_limit' classification."""
        mock_sdk = _make_failing_sdk()
        with (
            patch(
                "attune.workflows.doc_audit.workflow.claude_agent_sdk",
                mock_sdk,
            ),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value="429 Too Many Requests: rate limit exceeded",
            ),
        ):
            from attune.workflows.doc_audit.workflow import DocAuditWorkflow

            wf = DocAuditWorkflow()
            result = await wf.execute(path="docs/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "rate_limit"
        assert "rate" in (result.error or "").lower()
        assert "Agent SDK error:" not in (result.error or "")


class TestDocumentGenPhase6:
    """document_gen/workflow.py (doc-gen) surfaces real cause."""

    @pytest.mark.asyncio
    async def test_surfaces_real_cause_on_subprocess_failure(self):
        """api_quota stderr → 'API quota reached' classification."""
        mock_sdk = _make_failing_sdk()
        with (
            patch(
                "attune.workflows.document_gen.workflow.claude_agent_sdk",
                mock_sdk,
            ),
            patch(
                "attune.workflows.agent_sdk_adapter.capture_subprocess_failure",
                return_value=("Error: You have reached your specified API usage limits."),
            ),
        ):
            from attune.workflows.document_gen.workflow import (
                DocumentGenerationWorkflow,
            )

            wf = DocumentGenerationWorkflow()
            result = await wf.execute(path="src/")

        assert result.success is False
        assert result.metadata.get("sdk_error_kind") == "api_quota"
        assert "API quota reached" in (result.error or "")
        assert "Agent SDK error:" not in (result.error or "")
