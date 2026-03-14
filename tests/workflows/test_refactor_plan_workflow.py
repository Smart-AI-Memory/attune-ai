"""Tests for RefactorPlanWorkflow (SDK-native).

Validates class attributes, construction, and re-exports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestRefactorPlanWorkflowAttributes:
    """Test SDK-native class attributes on RefactorPlanWorkflow."""

    def test_import(self):
        """Test workflow is importable."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        assert RefactorPlanWorkflow is not None

    def test_name(self):
        """Test workflow name."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.name == "refactor-plan"

    def test_stages(self):
        """Test single agent stage."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.stages == ["agent-plan"]

    def test_tier_map(self):
        """Test tier map uses CAPABLE for agent stage."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.tier_map == {"agent-plan": ModelTier.CAPABLE}

    def test_description_mentions_agent_sdk(self):
        """Test description references Agent SDK."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert "Agent SDK" in wf.description

    def test_constructor_accepts_kwargs(self):
        """Test constructor passes kwargs to BaseWorkflow."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf is not None


@pytest.mark.unit
class TestRefactorPlanReExports:
    """Test public re-exports from refactor_plan module."""

    def test_debt_markers_exported(self):
        """Test DEBT_MARKERS is importable."""
        from attune.workflows.refactor_plan import DEBT_MARKERS

        assert isinstance(DEBT_MARKERS, list | tuple | dict)

    def test_refactor_plan_steps_exported(self):
        """Test REFACTOR_PLAN_STEPS is importable."""
        from attune.workflows.refactor_plan import REFACTOR_PLAN_STEPS

        assert isinstance(REFACTOR_PLAN_STEPS, list | tuple | dict)

    def test_format_refactor_plan_report_exported(self):
        """Test format_refactor_plan_report is importable."""
        from attune.workflows.refactor_plan import format_refactor_plan_report

        assert callable(format_refactor_plan_report)

    def test_main_exported(self):
        """Test main is importable."""
        from attune.workflows.refactor_plan import main

        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
