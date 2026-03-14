"""Behavioral tests for HealthCheckAgentSDKWorkflow.

Tests the Agent SDK health check workflow covering attributes,
SDK unavailability, successful execution, depth configuration,
mode-based subagent selection, and error handling.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from attune.workflows.data_classes import WorkflowResult


@pytest.mark.unit
class TestHealthCheckAgentSDKWorkflowAttributes:
    """Test workflow class attributes."""

    def test_workflow_has_correct_name(self) -> None:
        """Given the workflow class, name is 'health-check'."""
        from attune.workflows.health_check import HealthCheckAgentSDKWorkflow

        wf = HealthCheckAgentSDKWorkflow()
        assert wf.name == "health-check"

    def test_workflow_has_description(self) -> None:
        """Given the workflow class, description is a non-empty string."""
        from attune.workflows.health_check import HealthCheckAgentSDKWorkflow

        wf = HealthCheckAgentSDKWorkflow()
        assert isinstance(wf.description, str)
        assert len(wf.description) > 0

    def test_workflow_has_stages_list(self) -> None:
        """Given the workflow class, stages list contains 'agent-check'."""
        from attune.workflows.health_check import HealthCheckAgentSDKWorkflow

        wf = HealthCheckAgentSDKWorkflow()
        assert isinstance(wf.stages, list)
        assert "agent-check" in wf.stages


@pytest.mark.unit
class TestHealthCheckAgentSDKWorkflowExecution:
    """Test successful execution with mocked SDK."""

    @pytest.mark.asyncio
    async def test_execute_returns_success_on_valid_sdk_response(self) -> None:
        """Given a mocked SDK returning health check text, execute returns success."""
        sample_text = (
            "## Summary\n"
            "Project health score: 90/100. Well-maintained codebase.\n\n"
            "## Test Health\n"
            "- 127 tests passing, 85% coverage\n\n"
            "## Dependencies\n"
            "- All dependencies up to date\n\n"
            "## Code Quality\n"
            "- No ruff violations found\n\n"
            "## CI/CD\n"
            "- All workflows passing\n\n"
            "## Documentation\n"
            "- API docs complete\n\n"
            "## Recommendations\n"
            "- Increase test coverage to 90%\n"
        )

        fake_result = MagicMock()
        fake_result.text = sample_text

        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=fake_result)
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch(
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            result = await wf.execute(project_root=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is True
        assert result.stages is not None
        assert len(result.stages) > 0
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
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            result = await wf.execute(project_root=".")

        assert isinstance(result, WorkflowResult)
        assert result.success is False
        assert "RuntimeError" in (result.error or "")


@pytest.mark.unit
class TestHealthCheckAgentSDKWorkflowDepth:
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
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            await wf.execute(project_root=".", depth=depth)

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
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            await wf.execute(project_root=".", depth="unknown_depth")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        assert options_call.kwargs.get("max_turns") == 20


@pytest.mark.unit
class TestHealthCheckAgentSDKWorkflowModes:
    """Test mode-based dynamic subagent selection."""

    def test_quick_mode_uses_three_subagents(self) -> None:
        """Given mode='quick', three subagents are selected."""
        from attune.workflows.health_check import _MODE_SUBAGENTS

        assert len(_MODE_SUBAGENTS["quick"]) == 3
        assert set(_MODE_SUBAGENTS["quick"]) == {
            "test-checker",
            "dep-checker",
            "lint-checker",
        }

    def test_standard_mode_uses_five_subagents(self) -> None:
        """Given mode='standard', five subagents are selected."""
        from attune.workflows.health_check import _MODE_SUBAGENTS

        assert len(_MODE_SUBAGENTS["standard"]) == 5
        assert set(_MODE_SUBAGENTS["standard"]) == {
            "test-checker",
            "dep-checker",
            "lint-checker",
            "ci-checker",
            "doc-checker",
        }

    def test_full_mode_uses_six_subagents(self) -> None:
        """Given mode='full', all six subagents are selected."""
        from attune.workflows.health_check import _MODE_SUBAGENTS

        assert len(_MODE_SUBAGENTS["full"]) == 6
        assert set(_MODE_SUBAGENTS["full"]) == {
            "test-checker",
            "dep-checker",
            "lint-checker",
            "ci-checker",
            "doc-checker",
            "security-checker",
        }

    @pytest.mark.asyncio
    async def test_quick_mode_passes_three_agents_to_sdk(self) -> None:
        """Given mode='quick', only 3 AgentDefinitions are passed to SDK."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch(
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            await wf.execute(project_root=".", mode="quick")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        agents_dict = options_call.kwargs.get("agents", {})
        assert len(agents_dict) == 3

    @pytest.mark.asyncio
    async def test_full_mode_passes_six_agents_to_sdk(self) -> None:
        """Given mode='full', all 6 AgentDefinitions are passed to SDK."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch(
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            await wf.execute(project_root=".", mode="full")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        agents_dict = options_call.kwargs.get("agents", {})
        assert len(agents_dict) == 6

    @pytest.mark.asyncio
    async def test_unknown_mode_defaults_to_standard(self) -> None:
        """Given an unknown mode, defaults to 'standard' (5 subagents)."""
        mock_sdk = MagicMock()
        mock_sdk.query = MagicMock(return_value=MagicMock(text="## Summary\nOK"))
        mock_sdk.ClaudeAgentOptions = MagicMock()
        mock_sdk.AgentDefinition = MagicMock()

        with (
            patch(
                "attune.workflows.health_check.claude_agent_sdk",
                mock_sdk,
            ),
        ):
            from attune.workflows.health_check import (
                HealthCheckAgentSDKWorkflow,
            )

            wf = HealthCheckAgentSDKWorkflow()
            await wf.execute(project_root=".", mode="nonexistent")

        options_call = mock_sdk.ClaudeAgentOptions.call_args
        assert options_call is not None
        agents_dict = options_call.kwargs.get("agents", {})
        assert len(agents_dict) == 5
