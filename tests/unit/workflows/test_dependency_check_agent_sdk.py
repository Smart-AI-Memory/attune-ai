"""Behavioral tests for DependencyCheckAgentSDKWorkflow.

Tests the Agent SDK dependency check workflow covering attributes,
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
class TestDependencyCheckAgentSDKWorkflowAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        """Given the workflow class, name is 'dependency-check-sdk'."""
        from attune.workflows.dependency_check_agent_sdk import (
            DependencyCheckAgentSDKWorkflow,
        )

        wf = DependencyCheckAgentSDKWorkflow()
        assert wf.name == "dependency-check-sdk"

    def test_workflow_has_description(self) -> None:
        """Given the workflow class, description is a non-empty string."""
        from attune.workflows.dependency_check_agent_sdk import (
            DependencyCheckAgentSDKWorkflow,
        )

        wf = DependencyCheckAgentSDKWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        """Given the workflow class, stages list contains 'agent-check'."""
        from attune.workflows.dependency_check_agent_sdk import (
            DependencyCheckAgentSDKWorkflow,
        )

        wf = DependencyCheckAgentSDKWorkflow()
        assert isinstance(wf.stages, list)
        assert "agent-check" in wf.stages


@pytest.mark.unit
class TestDependencyCheckAgentSDKWorkflowSdkUnavailable:
    """Test behavior when claude_agent_sdk is not installed."""

    @pytest.mark.asyncio
    async def test_execute_returns_failure_when_sdk_unavailable(self) -> None:
        """Given SDK unavailable, execute returns WorkflowResult with success=False."""
        from attune.workflows.dependency_check_agent_sdk import (
            DependencyCheckAgentSDKWorkflow,
        )

        wf = DependencyCheckAgentSDKWorkflow()

        with patch("attune.workflows.dependency_check_agent_sdk._SDK_AVAILABLE", False):
            result = await wf.execute(path=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "claude-agent-sdk not installed" in (result.error or "")

    @pytest.mark.asyncio
    async def test_execute_returns_failure_when_path_missing(self) -> None:
        """Given no path argument, execute returns WorkflowResult with error."""
        from attune.workflows.dependency_check_agent_sdk import (
            DependencyCheckAgentSDKWorkflow,
        )

        wf = DependencyCheckAgentSDKWorkflow()

        result = await wf.execute()

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "path" in (result.error or "").lower()


@pytest.mark.unit
class TestDependencyCheckAgentSDKWorkflowExecution:
    """Test successful execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_execute_returns_success_on_valid_sdk_response(self) -> None:
        """Given a mocked SDK returning dependency text, execute returns success."""
        sample_text = (
            "## Summary\n"
            "Dependency health score: 78/100. Most packages up to date.\n\n"
            "## Dependencies\n"
            "- requests 2.31.0 (latest: 2.32.0)\n"
            "- pydantic 2.5.0 (latest: 2.6.1) — minor update available\n\n"
            "## Suggestions\n"
            "- Update requests to 2.32.0 (no breaking changes)\n"
            "- Update pydantic to 2.6.1 (minor, check changelog)\n"
        )

        fake_result = MagicMock()
        fake_result.text = sample_text

        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=fake_result)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch("attune.workflows.dependency_check_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.dependency_check_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.dependency_check_agent_sdk import (
                DependencyCheckAgentSDKWorkflow,
            )

            wf = DependencyCheckAgentSDKWorkflow()
            result = await wf.execute(path=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.stages is not None
        assert len(result.stages) == 2
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
            patch("attune.workflows.dependency_check_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.dependency_check_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.dependency_check_agent_sdk import (
                DependencyCheckAgentSDKWorkflow,
            )

            wf = DependencyCheckAgentSDKWorkflow()
            result = await wf.execute(path=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "RuntimeError" in (result.error or "")


@pytest.mark.unit
class TestDependencyCheckAgentSDKWorkflowDepth:
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
            patch("attune.workflows.dependency_check_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.dependency_check_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.dependency_check_agent_sdk import (
                DependencyCheckAgentSDKWorkflow,
            )

            wf = DependencyCheckAgentSDKWorkflow()
            await wf.execute(path=".", depth=depth)

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
            patch("attune.workflows.dependency_check_agent_sdk._SDK_AVAILABLE", True),
            patch(
                "attune.workflows.dependency_check_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.dependency_check_agent_sdk import (
                DependencyCheckAgentSDKWorkflow,
            )

            wf = DependencyCheckAgentSDKWorkflow()
            await wf.execute(path=".", depth="unknown_depth")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == 20


@pytest.mark.unit
class TestDependencyCheckAgentSDKWorkflowSubagents:
    """Test subagent definitions."""

    def test_two_subagents_defined(self) -> None:
        """Given the module constants, exactly 2 subagents are defined."""
        from attune.workflows.dependency_check_agent_sdk import _SUBAGENT_NAMES

        assert len(_SUBAGENT_NAMES) == 2

    def test_subagent_names_match_expected(self) -> None:
        """Given the module constants, subagent names match expected set."""
        from attune.workflows.dependency_check_agent_sdk import _SUBAGENT_NAMES

        expected = {
            "inventory-assessor",
            "update-advisor",
        }
        assert set(_SUBAGENT_NAMES) == expected
