"""Behavioral tests for TestAuditAgentSDKWorkflow.

Tests the Agent SDK test audit workflow covering attributes,
SDK unavailability, successful execution, depth configuration,
and subagent definitions.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.data_classes import WorkflowResult


@pytest.mark.unit
class TestTestAuditAgentSDKWorkflowAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        """Given the workflow class, name is 'test-audit-sdk'."""
        from attune.workflows.test_audit_agent_sdk import TestAuditAgentSDKWorkflow

        wf = TestAuditAgentSDKWorkflow()
        assert wf.name == "test-audit-sdk"

    def test_workflow_has_description(self) -> None:
        """Given the workflow class, description is a non-empty string."""
        from attune.workflows.test_audit_agent_sdk import TestAuditAgentSDKWorkflow

        wf = TestAuditAgentSDKWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        """Given the workflow class, stages list contains 'agent-audit'."""
        from attune.workflows.test_audit_agent_sdk import TestAuditAgentSDKWorkflow

        wf = TestAuditAgentSDKWorkflow()
        assert isinstance(wf.stages, list)
        assert "agent-audit" in wf.stages


@pytest.mark.unit
class TestTestAuditAgentSDKWorkflowSdkUnavailable:
    """Test behavior when claude_agent_sdk is not installed."""

    @pytest.mark.asyncio
    async def test_execute_returns_failure_when_sdk_unavailable(self) -> None:
        """Given SDK unavailable, execute returns WorkflowResult with success=False."""
        from attune.workflows.test_audit_agent_sdk import TestAuditAgentSDKWorkflow

        wf = TestAuditAgentSDKWorkflow()

        with patch("attune.workflows.test_audit_agent_sdk._SDK_AVAILABLE", False):
            result = await wf.execute(src_path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "claude-agent-sdk not installed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_returns_failure_when_src_path_missing(self) -> None:
        """Given no src_path argument, execute returns WorkflowResult with error."""
        from attune.workflows.test_audit_agent_sdk import TestAuditAgentSDKWorkflow

        wf = TestAuditAgentSDKWorkflow()

        result = await wf.execute()

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "src_path" in (result.error or "").lower()


@pytest.mark.unit
class TestTestAuditAgentSDKWorkflowExecution:
    """Test successful execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_execute_returns_success_on_valid_sdk_response(self) -> None:
        """Given a mocked SDK returning audit text, execute returns success."""
        sample_text = (
            "## Summary\n"
            "Test health score: 78/100. Good coverage with some gaps.\n\n"
            "## Coverage\n"
            "- Overall line coverage: 82%\n"
            "- Branch coverage: 71%\n\n"
            "## Test Gaps\n"
            "- src/attune/workflows/base.py:45 - untested error branch\n"
            "- src/attune/memory/encryption.py:90 - missing edge case\n\n"
            "## Suggestions\n"
            "- Add test for encryption key rotation (HIGH, small effort)\n"
            "- Add boundary tests for batch runner (MEDIUM, medium effort)\n"
        )

        fake_result = MagicMock()
        fake_result.text = sample_text

        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=fake_result)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch("attune.workflows.test_audit_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.test_audit_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.test_audit_agent_sdk import (
                TestAuditAgentSDKWorkflow,
            )

            wf = TestAuditAgentSDKWorkflow()
            result = await wf.execute(src_path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.stages is not None
        assert len(result.stages) == 3
        assert result.summary is not None
        assert len(result.summary) > 0

    @pytest.mark.asyncio
    async def test_execute_handles_sdk_exception_gracefully(self) -> None:
        """Given SDK raises an exception, execute returns error result."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(side_effect=RuntimeError("SDK crashed"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch("attune.workflows.test_audit_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.test_audit_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.test_audit_agent_sdk import (
                TestAuditAgentSDKWorkflow,
            )

            wf = TestAuditAgentSDKWorkflow()
            result = await wf.execute(src_path="src/")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "RuntimeError" in (result.error or "")


@pytest.mark.unit
class TestTestAuditAgentSDKWorkflowDepth:
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
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch("attune.workflows.test_audit_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.test_audit_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.test_audit_agent_sdk import (
                TestAuditAgentSDKWorkflow,
            )

            wf = TestAuditAgentSDKWorkflow()
            await wf.execute(src_path="src/", depth=depth)

        # Verify max_turns was passed to ClaudeAgentOptions
        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == expected_turns

    @pytest.mark.asyncio
    async def test_unknown_depth_defaults_to_twenty(self) -> None:
        """Given an unknown depth value, max_turns defaults to 20."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch("attune.workflows.test_audit_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.test_audit_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.test_audit_agent_sdk import (
                TestAuditAgentSDKWorkflow,
            )

            wf = TestAuditAgentSDKWorkflow()
            await wf.execute(src_path="src/", depth="unknown_depth")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == 20


@pytest.mark.unit
class TestTestAuditAgentSDKWorkflowSubagents:
    """Test subagent definitions."""

    def test_three_subagents_defined(self) -> None:
        """Given the module constants, exactly 3 subagents are defined."""
        from attune.workflows.test_audit_agent_sdk import _SUBAGENT_NAMES

        assert len(_SUBAGENT_NAMES) == 3

    def test_subagent_names_match_expected(self) -> None:
        """Given the module constants, subagent names match expected set."""
        from attune.workflows.test_audit_agent_sdk import _SUBAGENT_NAMES

        expected = {
            "coverage-auditor",
            "gap-analyzer",
            "test-planner",
        }
        assert set(_SUBAGENT_NAMES) == expected
