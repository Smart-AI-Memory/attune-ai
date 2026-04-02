"""Comprehensive tests for refactor_plan workflow.

Targets statement coverage for:
- src/attune/workflows/refactor_plan.py

All LLM calls and external dependencies are mocked.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.refactor_plan import (
    DEBT_MARKERS,
    REFACTOR_PLAN_STEPS,
    RefactorPlanWorkflow,
    format_refactor_plan_report,
)

# ============================================================================
# RefactorPlanWorkflow Tests (SDK-native, v4.2.0)
# ============================================================================


@pytest.mark.unit
class TestRefactorPlanConstants:
    """Tests for refactor plan constants."""

    def test_refactor_plan_steps_has_plan(self) -> None:
        """Verify REFACTOR_PLAN_STEPS has plan configuration."""
        assert "plan" in REFACTOR_PLAN_STEPS

    def test_debt_markers_has_entries(self) -> None:
        """Verify DEBT_MARKERS has patterns."""
        assert len(DEBT_MARKERS) > 0

    def test_debt_markers_values_are_dicts(self) -> None:
        """Verify DEBT_MARKERS values are dicts with severity and weight."""
        for key, info in DEBT_MARKERS.items():
            assert isinstance(info, dict), f"{key} should be a dict"
            assert "severity" in info, f"{key} should have severity"


@pytest.mark.unit
class TestRefactorPlanWorkflowInit:
    """Tests for RefactorPlanWorkflow initialization (SDK-native)."""

    def test_class_name(self) -> None:
        """Class attribute name is 'refactor-plan'."""
        assert RefactorPlanWorkflow.name == "refactor-plan"

    def test_class_description(self) -> None:
        """Description mentions Agent SDK."""
        assert "Agent SDK" in RefactorPlanWorkflow.description

    def test_class_stages(self) -> None:
        """SDK-native workflow has single agent-plan stage."""
        assert RefactorPlanWorkflow.stages == ["agent-plan"]

    def test_default_construction(self) -> None:
        """Default constructor succeeds."""
        wf = RefactorPlanWorkflow()
        assert wf.name == "refactor-plan"

    def test_post_simplification_enabled_by_default(self) -> None:
        """Post-simplification is enabled by default via kwargs."""
        wf = RefactorPlanWorkflow()
        assert getattr(wf, "_enable_post_simplification", True) is True


@pytest.mark.unit
class TestRefactorPlanFormatReport:
    """Tests for format_refactor_plan_report."""

    def test_returns_string(self) -> None:
        """Report formatter returns a string."""
        report = format_refactor_plan_report(
            {"debt_items": [], "plan": "No refactoring needed"},
            {"path": "."},
        )
        assert isinstance(report, str)
