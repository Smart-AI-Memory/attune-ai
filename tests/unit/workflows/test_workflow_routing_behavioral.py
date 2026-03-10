"""Behavioral tests for workflow smart routing and SDK variant resolution.

Tests the get_workflow() smart routing, is_using_api_fallback() detection,
list_workflows() deduplication, and CLI command integration.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from argparse import Namespace
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from attune.workflows import (
    _SDK_REVERSE_MAP,
    _SDK_WORKFLOW_MAP,
    get_workflow,
    is_using_api_fallback,
    list_workflows,
)
from attune.workflows.base import ModelTier
from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage

# ---------------------------------------------------------------------------
# _SDK_WORKFLOW_MAP / _SDK_REVERSE_MAP constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSDKWorkflowMapConstants:
    """Test the mapping constants are correctly defined."""

    def test_sdk_workflow_map_has_thirteen_entries(self) -> None:
        """Given the map, it contains exactly 13 base-to-SDK mappings."""
        assert len(_SDK_WORKFLOW_MAP) == 13

    def test_sdk_workflow_map_values_end_with_sdk(self) -> None:
        """Given each SDK mapping, the value ends with '-sdk'."""
        for base_name, sdk_name in _SDK_WORKFLOW_MAP.items():
            assert sdk_name.endswith("-sdk"), f"{sdk_name} does not end with -sdk"
            assert sdk_name == f"{base_name}-sdk"

    def test_sdk_reverse_map_is_inverse_of_forward_map(self) -> None:
        """Given the reverse map, it inverts the forward map exactly."""
        assert len(_SDK_REVERSE_MAP) == len(_SDK_WORKFLOW_MAP)
        for base_name, sdk_name in _SDK_WORKFLOW_MAP.items():
            assert _SDK_REVERSE_MAP[sdk_name] == base_name

    def test_sdk_workflow_map_contains_core_workflows(self) -> None:
        """Given the map, it includes all expected base workflow names."""
        expected = {
            "code-review",
            "security-audit",
            "perf-audit",
            "release-prep",
            "test-audit",
            "bug-predict",
            "refactor-plan",
            "test-gen",
            "doc-audit",
            "doc-gen",
            "simplify-code",
            "dependency-check",
            "research-synthesis",
        }
        assert set(_SDK_WORKFLOW_MAP.keys()) == expected


# ---------------------------------------------------------------------------
# get_workflow() smart routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetWorkflowSmartRouting:
    """Test get_workflow() prefers SDK variant when available."""

    def test_routes_to_sdk_variant_when_sdk_available(self) -> None:
        """Given SDK is available, requesting 'security-audit' returns the SDK class."""
        with patch("attune.workflows._is_sdk_available", return_value=True):
            cls = get_workflow("security-audit")
        assert cls.__name__ == "SecurityAuditAgentSDKWorkflow"

    def test_returns_base_variant_when_sdk_unavailable(self) -> None:
        """Given SDK is unavailable, requesting 'security-audit' returns the API class."""
        with patch("attune.workflows._is_sdk_available", return_value=False):
            cls = get_workflow("security-audit")
        assert cls.__name__ == "SecurityAuditWorkflow"

    def test_explicit_sdk_name_works_regardless_of_availability(self) -> None:
        """Given explicit '-sdk' suffix, returns SDK class even without routing."""
        cls = get_workflow("security-audit-sdk")
        assert cls.__name__ == "SecurityAuditAgentSDKWorkflow"

    def test_native_workflow_unaffected_by_sdk_status(self) -> None:
        """Given a native workflow with no SDK variant, returns it directly."""
        with patch("attune.workflows._is_sdk_available", return_value=True):
            cls = get_workflow("secure-release")
        assert cls.__name__ == "SecureReleasePipeline"

    def test_unknown_workflow_raises_key_error(self) -> None:
        """Given an unknown name, raises KeyError with available names."""
        with pytest.raises(KeyError, match="Unknown workflow"):
            get_workflow("nonexistent-workflow")

    def test_all_mapped_workflows_route_to_sdk_when_available(self) -> None:
        """Given SDK is available, all 13 mapped workflows resolve to different class than API."""
        for base_name in _SDK_WORKFLOW_MAP:
            with patch("attune.workflows._is_sdk_available", return_value=True):
                sdk_cls = get_workflow(base_name)
            with patch("attune.workflows._is_sdk_available", return_value=False):
                api_cls = get_workflow(base_name)
            assert (
                sdk_cls is not api_cls
            ), f"{base_name}: SDK and API resolved to same class {sdk_cls.__name__}"

    def test_all_mapped_workflows_return_api_when_sdk_unavailable(self) -> None:
        """Given SDK is unavailable, all 13 mapped workflows resolve to API classes."""
        with patch("attune.workflows._is_sdk_available", return_value=False):
            for base_name in _SDK_WORKFLOW_MAP:
                cls = get_workflow(base_name)
                assert (
                    "AgentSDK" not in cls.__name__
                ), f"{base_name} resolved to {cls.__name__}, expected API variant"


# ---------------------------------------------------------------------------
# is_using_api_fallback()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsUsingApiFallback:
    """Test is_using_api_fallback() detection."""

    def test_returns_true_for_mapped_workflow_when_sdk_unavailable(self) -> None:
        """Given a mapped workflow and no SDK, returns True."""
        with patch("attune.workflows._is_sdk_available", return_value=False):
            assert is_using_api_fallback("security-audit") is True

    def test_returns_false_for_mapped_workflow_when_sdk_available(self) -> None:
        """Given a mapped workflow and SDK installed, returns False."""
        with patch("attune.workflows._is_sdk_available", return_value=True):
            assert is_using_api_fallback("security-audit") is False

    def test_returns_false_for_native_workflow(self) -> None:
        """Given a native workflow with no SDK variant, returns False."""
        with patch("attune.workflows._is_sdk_available", return_value=False):
            assert is_using_api_fallback("secure-release") is False

    def test_returns_false_for_unknown_workflow(self) -> None:
        """Given an unknown workflow name, returns False."""
        assert is_using_api_fallback("nonexistent") is False

    def test_returns_false_for_explicit_sdk_name(self) -> None:
        """Given an explicit '-sdk' name, returns False (not in forward map)."""
        assert is_using_api_fallback("security-audit-sdk") is False


# ---------------------------------------------------------------------------
# list_workflows() deduplication
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListWorkflowsDeduplication:
    """Test list_workflows() hides SDK duplicates."""

    def test_deduplicated_list_excludes_sdk_suffixed_names(self) -> None:
        """Given default listing, no workflow name ends with '-sdk' that has a base."""
        workflows = list_workflows()
        names = {wf["name"] for wf in workflows}
        for sdk_name, base_name in _SDK_REVERSE_MAP.items():
            if base_name in names:
                assert sdk_name not in names, f"Both '{base_name}' and '{sdk_name}' are visible"

    def test_deduplicated_list_keeps_base_names_visible(self) -> None:
        """Given default listing, all 13 base workflow names are present."""
        workflows = list_workflows()
        names = {wf["name"] for wf in workflows}
        for base_name in _SDK_WORKFLOW_MAP:
            assert base_name in names, f"Base workflow '{base_name}' is missing"

    def test_show_all_includes_sdk_variants(self) -> None:
        """Given show_all=True, SDK-suffixed entries are included."""
        all_wfs = list_workflows(show_all=True)
        all_names = {wf["name"] for wf in all_wfs}
        for sdk_name in _SDK_REVERSE_MAP:
            assert sdk_name in all_names, f"SDK workflow '{sdk_name}' missing in show_all"

    def test_show_all_has_more_entries_than_default(self) -> None:
        """Given both listing modes, show_all returns more workflows."""
        default = list_workflows()
        full = list_workflows(show_all=True)
        assert len(full) > len(default)

    def test_sdk_only_workflows_are_visible_in_default(self) -> None:
        """Given SDK-only workflows (no base), they appear in default list."""
        workflows = list_workflows()
        names = {wf["name"] for wf in workflows}
        # deep-review-sdk and health-check-sdk have no base counterpart
        assert "deep-review-sdk" in names
        assert "health-check-sdk" in names


# ---------------------------------------------------------------------------
# list_workflows() engine tagging
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListWorkflowsEngineTag:
    """Test list_workflows() engine field."""

    def test_mapped_workflows_tagged_sdk_when_available(self) -> None:
        """Given SDK is available, mapped workflows have engine='sdk'."""
        with patch("attune.workflows._is_sdk_available", return_value=True):
            workflows = list_workflows()
        by_name = {wf["name"]: wf for wf in workflows}
        for base_name in _SDK_WORKFLOW_MAP:
            assert by_name[base_name]["engine"] == "sdk", f"{base_name} should be tagged 'sdk'"

    def test_mapped_workflows_tagged_api_when_unavailable(self) -> None:
        """Given SDK is unavailable, mapped workflows have engine='api'."""
        with patch("attune.workflows._is_sdk_available", return_value=False):
            workflows = list_workflows()
        by_name = {wf["name"]: wf for wf in workflows}
        for base_name in _SDK_WORKFLOW_MAP:
            assert by_name[base_name]["engine"] == "api", f"{base_name} should be tagged 'api'"

    def test_native_workflows_tagged_native(self) -> None:
        """Given a workflow with no SDK variant, engine='native'."""
        workflows = list_workflows()
        by_name = {wf["name"]: wf for wf in workflows}
        assert by_name["secure-release"]["engine"] == "native"

    def test_each_workflow_has_engine_field(self) -> None:
        """Given any listing mode, all entries have an engine field."""
        for wf in list_workflows(show_all=True):
            assert "engine" in wf, f"Workflow '{wf['name']}' missing engine field"
            assert wf["engine"] in {
                "sdk",
                "api",
                "native",
            }, f"Unexpected engine '{wf['engine']}' for {wf['name']}"


# ---------------------------------------------------------------------------
# Helpers for CLI tests
# ---------------------------------------------------------------------------


def _make_mock_result() -> WorkflowResult:
    """Build a minimal WorkflowResult for mocked workflow execution."""
    now = datetime.now()
    return WorkflowResult(
        success=True,
        stages=[WorkflowStage(name="test", tier=ModelTier.CAPABLE, description="test")],
        final_output="mocked output",
        cost_report=CostReport(
            total_cost=0.0,
            baseline_cost=0.0,
            savings=0.0,
            savings_percent=0.0,
        ),
        started_at=now,
        completed_at=now,
        total_duration_ms=100,
        provider="test",
    )


# ---------------------------------------------------------------------------
# CLI: cmd_workflow_run API fallback warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdWorkflowRunFallbackWarning:
    """Test CLI prints warning when falling back to API version."""

    @staticmethod
    def _make_run_args(name: str) -> Namespace:
        """Build CLI args for cmd_workflow_run."""
        return Namespace(
            name=name,
            input='{"path": "/tmp/test"}',
            path=None,
            target=None,
            json=False,
        )

    @staticmethod
    def _mock_workflow_cls() -> MagicMock:
        """Build a mock workflow class whose instance.execute() returns a result."""
        mock_cls = MagicMock()
        mock_cls.return_value.execute.return_value = _make_mock_result()
        return mock_cls

    def test_prints_warning_when_sdk_unavailable(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given SDK unavailable and a mapped workflow, warning is printed."""
        from attune.cli_commands.workflow_commands import cmd_workflow_run

        with (
            patch("attune.workflows._is_sdk_available", return_value=False),
            patch("attune.workflows.get_workflow", return_value=self._mock_workflow_cls()),
        ):
            cmd_workflow_run(self._make_run_args("security-audit"))

        captured = capsys.readouterr()
        assert "Using API version" in captured.out
        assert "pip install claude-agent-sdk" in captured.out

    def test_no_warning_when_sdk_available(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given SDK available, no warning is printed."""
        from attune.cli_commands.workflow_commands import cmd_workflow_run

        with (
            patch("attune.workflows._is_sdk_available", return_value=True),
            patch("attune.workflows.get_workflow", return_value=self._mock_workflow_cls()),
        ):
            cmd_workflow_run(self._make_run_args("security-audit"))

        captured = capsys.readouterr()
        assert "Using API version" not in captured.out

    def test_no_warning_for_native_workflow(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given a native workflow, no warning is printed regardless of SDK status."""
        from attune.cli_commands.workflow_commands import cmd_workflow_run

        with (
            patch("attune.workflows._is_sdk_available", return_value=False),
            patch("attune.workflows.get_workflow", return_value=self._mock_workflow_cls()),
        ):
            cmd_workflow_run(self._make_run_args("secure-release"))

        captured = capsys.readouterr()
        assert "Using API version" not in captured.out


# ---------------------------------------------------------------------------
# CLI: cmd_workflow_list
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdWorkflowList:
    """Test CLI list command uses deduplicated output."""

    def test_list_shows_sdk_tag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given SDK available, list shows [SDK] tags for mapped workflows."""
        from attune.cli_commands.workflow_commands import cmd_workflow_list

        args = Namespace(all=False)

        with patch("attune.workflows._is_sdk_available", return_value=True):
            result = cmd_workflow_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "[SDK]" in captured.out

    def test_list_shows_api_tag_when_sdk_unavailable(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Given SDK unavailable, list shows [API] tags for mapped workflows."""
        from attune.cli_commands.workflow_commands import cmd_workflow_list

        args = Namespace(all=False)

        with patch("attune.workflows._is_sdk_available", return_value=False):
            result = cmd_workflow_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "[API]" in captured.out

    def test_list_show_all_has_more_entries(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given --all flag, more workflows are shown."""
        from attune.cli_commands.workflow_commands import cmd_workflow_list

        args_default = Namespace(all=False)
        cmd_workflow_list(args_default)
        default_out = capsys.readouterr().out

        args_all = Namespace(all=True)
        cmd_workflow_list(args_all)
        all_out = capsys.readouterr().out

        # Extract total count from "Total: N workflows"
        default_match = re.search(r"Total: (\d+)", default_out)
        all_match = re.search(r"Total: (\d+)", all_out)
        assert default_match is not None, "Total count not found in default output"
        assert all_match is not None, "Total count not found in --all output"
        default_count = int(default_match.group(1))
        all_count = int(all_match.group(1))
        assert all_count > default_count


# ---------------------------------------------------------------------------
# CLI: cmd_workflow_info smart routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdWorkflowInfo:
    """Test CLI info command uses smart routing."""

    def test_info_resolves_to_sdk_class(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given SDK available, info for a mapped workflow shows SDK class doc."""
        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = Namespace(name="security-audit")

        with patch("attune.workflows._is_sdk_available", return_value=True):
            result = cmd_workflow_info(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Agent SDK" in captured.out

    def test_info_unknown_workflow_returns_error(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given an unknown workflow name, info returns exit code 1."""
        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = Namespace(name="nonexistent-workflow")
        result = cmd_workflow_info(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "not found" in captured.out
