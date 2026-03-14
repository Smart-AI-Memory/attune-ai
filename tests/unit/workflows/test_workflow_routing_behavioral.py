"""Behavioral tests for workflow smart routing and SDK variant resolution.

Tests the get_workflow() smart routing, list_workflows() deduplication,
and CLI command integration. SDK is now a core dependency. All workflow
pairs have been merged into single SDK-native implementations (v4.2.0).

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import re
from argparse import Namespace
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from attune.models import ModelTier
from attune.workflows import (
    _SDK_NATIVE_WORKFLOWS,
    _SDK_REVERSE_MAP,
    _SDK_WORKFLOW_MAP,
    get_workflow,
    is_using_api_fallback,
    list_workflows,
)
from attune.workflows.data_classes import CostReport, WorkflowResult, WorkflowStage

# ---------------------------------------------------------------------------
# _SDK_WORKFLOW_MAP / _SDK_REVERSE_MAP constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSDKWorkflowMapConstants:
    """Test the mapping constants are correctly defined."""

    def test_sdk_workflow_map_is_empty(self) -> None:
        """Given the map, all pairs have been merged — map is empty."""
        assert len(_SDK_WORKFLOW_MAP) == 0

    def test_sdk_reverse_map_is_empty(self) -> None:
        """Given the reverse map, it is also empty after all merges."""
        assert len(_SDK_REVERSE_MAP) == 0

    def test_all_workflows_merged_not_in_sdk_workflow_map(self) -> None:
        """Given the map, all formerly-mapped workflows are NOT in it."""
        for name in (
            "code-review",
            "security-audit",
            "bug-predict",
            "perf-audit",
            "test-gen",
            "doc-audit",
            "doc-gen",
            "release-prep",
            "test-audit",
            "refactor-plan",
            "simplify-code",
            "dependency-check",
            "research-synthesis",
        ):
            assert name not in _SDK_WORKFLOW_MAP


# ---------------------------------------------------------------------------
# _SDK_NATIVE_WORKFLOWS set
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSDKNativeWorkflows:
    """Test the _SDK_NATIVE_WORKFLOWS set for merged workflows."""

    def test_merged_workflows_are_sdk_native(self) -> None:
        """Given the set, all merged workflows are listed as SDK-native."""
        for name in (
            "code-review",
            "security-audit",
            "bug-predict",
            "perf-audit",
            "test-gen",
            "doc-audit",
            "doc-gen",
            "release-prep",
            "test-audit",
            "refactor-plan",
            "simplify-code",
            "dependency-check",
            "research-synthesis",
        ):
            assert name in _SDK_NATIVE_WORKFLOWS

    def test_sdk_native_workflows_not_in_routing_map(self) -> None:
        """Given SDK-native workflows, none are in _SDK_WORKFLOW_MAP."""
        for name in _SDK_NATIVE_WORKFLOWS:
            assert (
                name not in _SDK_WORKFLOW_MAP
            ), f"{name} is in both _SDK_NATIVE_WORKFLOWS and _SDK_WORKFLOW_MAP"


# ---------------------------------------------------------------------------
# get_workflow() smart routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetWorkflowSmartRouting:
    """Test get_workflow() routing."""

    def test_sdk_native_workflow_returns_directly(self) -> None:
        """Given an SDK-native workflow, returns it directly."""
        cls = get_workflow("test-audit")
        assert cls.__name__ == "TestAuditWorkflow"

    def test_native_workflow_returns_directly(self) -> None:
        """Given a native workflow with no SDK variant, returns it directly."""
        cls = get_workflow("secure-release")
        assert cls.__name__ == "SecureReleasePipeline"

    def test_unknown_workflow_raises_key_error(self) -> None:
        """Given an unknown name, raises KeyError with available names."""
        with pytest.raises(KeyError, match="Unknown workflow"):
            get_workflow("nonexistent-workflow")

    def test_all_sdk_native_workflows_resolve(self) -> None:
        """Given all 13 SDK-native workflows, each resolves to its class."""
        for name in _SDK_NATIVE_WORKFLOWS:
            cls = get_workflow(name)
            assert cls is not None, f"{name} failed to resolve"

    def test_merged_workflows_return_sdk_native_class(self) -> None:
        """Given merged workflows, each returns its SDK-native class directly."""
        expected = {
            "code-review": "CodeReviewWorkflow",
            "security-audit": "SecurityAuditWorkflow",
            "bug-predict": "BugPredictionWorkflow",
            "perf-audit": "PerformanceAuditWorkflow",
            "test-gen": "TestGenerationWorkflow",
            "doc-audit": "DocAuditWorkflow",
            "doc-gen": "DocumentGenerationWorkflow",
            "release-prep": "ReleasePrepTeamWorkflow",
            "test-audit": "TestAuditWorkflow",
            "refactor-plan": "RefactorPlanWorkflow",
            "simplify-code": "SimplifyCodeWorkflow",
            "dependency-check": "DependencyCheckWorkflow",
            "research-synthesis": "ResearchSynthesisWorkflow",
        }
        for name, class_name in expected.items():
            cls = get_workflow(name)
            assert cls.__name__ == class_name


# ---------------------------------------------------------------------------
# is_using_api_fallback()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIsUsingApiFallback:
    """Test is_using_api_fallback() always returns False (SDK is core dep)."""

    def test_returns_false_for_mapped_workflow(self) -> None:
        """Given a mapped workflow, returns False (SDK always available)."""
        assert is_using_api_fallback("security-audit") is False

    def test_returns_false_for_native_workflow(self) -> None:
        """Given a native workflow with no SDK variant, returns False."""
        assert is_using_api_fallback("secure-release") is False

    def test_returns_false_for_unknown_workflow(self) -> None:
        """Given an unknown workflow name, returns False."""
        assert is_using_api_fallback("nonexistent") is False

    def test_returns_false_for_explicit_sdk_name(self) -> None:
        """Given an explicit '-sdk' name, returns False."""
        assert is_using_api_fallback("security-audit-sdk") is False


# ---------------------------------------------------------------------------
# list_workflows() deduplication
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestListWorkflowsDeduplication:
    """Test list_workflows() hides SDK duplicates."""

    def test_no_sdk_suffixed_duplicates_in_default_listing(self) -> None:
        """Given default listing, _SDK_REVERSE_MAP is empty so no duplicates to hide."""
        assert len(_SDK_REVERSE_MAP) == 0

    def test_all_sdk_native_workflows_visible(self) -> None:
        """Given default listing, all SDK-native workflows are visible."""
        workflows = list_workflows()
        names = {wf["name"] for wf in workflows}
        for name in _SDK_NATIVE_WORKFLOWS:
            assert name in names, f"Merged workflow '{name}' is missing"

    def test_show_all_same_as_default_when_no_sdk_variants(self) -> None:
        """Given no SDK variant entries, show_all equals default."""
        default = list_workflows()
        full = list_workflows(show_all=True)
        # With _SDK_REVERSE_MAP empty, the only difference is
        # standalone SDK workflows (deep-review-sdk, health-check-sdk)
        # which are not hidden anyway.
        assert len(full) >= len(default)

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

    def test_merged_sdk_native_workflows_tagged_sdk(self) -> None:
        """Given merged SDK-native workflows, they have engine='sdk'."""
        workflows = list_workflows()
        by_name = {wf["name"]: wf for wf in workflows}
        for name in _SDK_NATIVE_WORKFLOWS:
            assert by_name[name]["engine"] == "sdk", f"{name} should be tagged 'sdk'"

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
class TestCmdWorkflowRunNoFallbackWarning:
    """Test CLI no longer prints API fallback warnings (SDK is core dep)."""

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

    def test_no_api_fallback_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given any workflow, no API fallback warning is printed."""
        from attune.cli_commands.workflow_commands import cmd_workflow_run

        with patch("attune.workflows.get_workflow", return_value=self._mock_workflow_cls()):
            cmd_workflow_run(self._make_run_args("security-audit"))

        captured = capsys.readouterr()
        assert "Using API version" not in captured.out
        assert "pip install claude-agent-sdk" not in captured.out


# ---------------------------------------------------------------------------
# CLI: cmd_workflow_list
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdWorkflowList:
    """Test CLI list command uses deduplicated output."""

    def test_list_shows_sdk_tag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given mapped workflows, list shows [SDK] tags."""
        from attune.cli_commands.workflow_commands import cmd_workflow_list

        args = Namespace(all=False)
        result = cmd_workflow_list(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "[SDK]" in captured.out

    def test_list_show_all_has_at_least_as_many_entries(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Given --all flag, at least as many workflows are shown."""
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
        assert all_count >= default_count


# ---------------------------------------------------------------------------
# CLI: cmd_workflow_info smart routing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCmdWorkflowInfo:
    """Test CLI info command uses smart routing."""

    def test_info_resolves_to_sdk_native_class(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given an SDK-native workflow, info shows SDK in description."""
        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = Namespace(name="test-audit")
        result = cmd_workflow_info(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Agent SDK" in captured.out

    def test_info_merged_workflow_shows_sdk(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Given a merged SDK-native workflow, info shows SDK in description."""
        from attune.cli_commands.workflow_commands import cmd_workflow_info

        args = Namespace(name="security-audit")
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
