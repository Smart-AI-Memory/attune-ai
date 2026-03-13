"""Behavioral tests for ReleasePrepAgentSDKWorkflow.

Tests the Agent SDK release prep workflow covering attributes,
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
class TestReleasePrepAgentSDKWorkflowAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        """Given the workflow class, name is 'release-prep-sdk'."""
        from attune.workflows.release_prep_agent_sdk import ReleasePrepAgentSDKWorkflow

        wf = ReleasePrepAgentSDKWorkflow()
        assert wf.name == "release-prep-sdk"

    def test_workflow_has_description(self) -> None:
        """Given the workflow class, description is a non-empty string."""
        from attune.workflows.release_prep_agent_sdk import ReleasePrepAgentSDKWorkflow

        wf = ReleasePrepAgentSDKWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        """Given the workflow class, stages list contains 'agent-prep'."""
        from attune.workflows.release_prep_agent_sdk import ReleasePrepAgentSDKWorkflow

        wf = ReleasePrepAgentSDKWorkflow()
        assert isinstance(wf.stages, list)
        assert "agent-prep" in wf.stages


@pytest.mark.unit
class TestReleasePrepAgentSDKWorkflowExecution:
    """Test successful execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_execute_returns_success_on_valid_sdk_response(self) -> None:
        """Given a mocked SDK returning release prep text, execute returns success."""
        sample_text = (
            "## Summary\n"
            "Release readiness score: 90/100. Project is ready for release.\n\n"
            "## Health\n"
            "- All 127 tests passing\n"
            "- Dependencies up to date\n\n"
            "## Security\n"
            "- No known vulnerabilities\n"
            "- No hardcoded secrets detected\n\n"
            "## Changelog\n"
            "### Features\n"
            "- Added Agent SDK release prep workflow\n\n"
            "## Suggestions\n"
            "- Bump version in pyproject.toml\n"
            "- Tag release after merge\n"
        )

        fake_result = MagicMock()
        fake_result.text = sample_text

        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=fake_result)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch(
                "attune.workflows.release_prep_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.release_prep_agent_sdk import (
                ReleasePrepAgentSDKWorkflow,
            )

            wf = ReleasePrepAgentSDKWorkflow()
            result = await wf.execute(path=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.stages is not None
        assert len(result.stages) == 4
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
            patch(
                "attune.workflows.release_prep_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.release_prep_agent_sdk import (
                ReleasePrepAgentSDKWorkflow,
            )

            wf = ReleasePrepAgentSDKWorkflow()
            result = await wf.execute(path=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "RuntimeError" in (result.error or "")


@pytest.mark.unit
class TestReleasePrepAgentSDKWorkflowDepth:
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
            patch(
                "attune.workflows.release_prep_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.release_prep_agent_sdk import (
                ReleasePrepAgentSDKWorkflow,
            )

            wf = ReleasePrepAgentSDKWorkflow()
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
            patch(
                "attune.workflows.release_prep_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.release_prep_agent_sdk import (
                ReleasePrepAgentSDKWorkflow,
            )

            wf = ReleasePrepAgentSDKWorkflow()
            await wf.execute(path=".", depth="unknown_depth")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == 20


@pytest.mark.unit
class TestReleasePrepAgentSDKWorkflowSubagents:
    """Test subagent definitions."""

    def test_four_subagents_defined(self) -> None:
        """Given the module constants, exactly 4 subagents are defined."""
        from attune.workflows.release_prep_agent_sdk import _SUBAGENT_NAMES

        assert len(_SUBAGENT_NAMES) == 4

    def test_subagent_names_match_expected(self) -> None:
        """Given the module constants, subagent names match expected set."""
        from attune.workflows.release_prep_agent_sdk import _SUBAGENT_NAMES

        expected = {
            "health-checker",
            "security-scanner",
            "changelog-generator",
            "release-assessor",
        }
        assert set(_SUBAGENT_NAMES) == expected

    @pytest.mark.asyncio
    async def test_allowed_tools_include_bash(self) -> None:
        """Given SDK execution, allowed_tools includes Bash for health and changelog agents."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch(
                "attune.workflows.release_prep_agent_sdk.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.release_prep_agent_sdk import (
                ReleasePrepAgentSDKWorkflow,
            )

            wf = ReleasePrepAgentSDKWorkflow()
            await wf.execute(path=".")

        # Verify top-level allowed_tools includes Bash
        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        allowed_tools = options_call.kwargs.get("allowed_tools")
        assert "Bash" in allowed_tools
        assert "Read" in allowed_tools
        assert "Agent" in allowed_tools
