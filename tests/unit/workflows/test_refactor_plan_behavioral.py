"""Behavioral tests for RefactorPlanWorkflow (SDK-native).

Validates class attributes and construction behavior.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import BaseWorkflow, ModelTier


@pytest.mark.unit
class TestRefactorPlanBehavioral:
    """Behavioral tests for SDK-native RefactorPlanWorkflow."""

    def test_inherits_base_workflow(self):
        """Test workflow inherits from BaseWorkflow."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        assert issubclass(RefactorPlanWorkflow, BaseWorkflow)

    def test_name_attribute(self):
        """Test workflow name is set correctly."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.name == "refactor-plan"

    def test_stages_attribute(self):
        """Test workflow has single agent stage."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.stages == ["agent-plan"]

    def test_tier_map_attribute(self):
        """Test tier map maps agent stage to CAPABLE."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert wf.tier_map == {"agent-plan": ModelTier.CAPABLE}

    def test_description_mentions_agent_sdk(self):
        """Test description references Agent SDK."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert "Agent SDK" in wf.description

    def test_multiple_instances_independent(self):
        """Test multiple instances are independent."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf1 = RefactorPlanWorkflow()
        wf2 = RefactorPlanWorkflow()
        assert wf1 is not wf2
        assert wf1.name == wf2.name

    def test_has_execute_method(self):
        """Test workflow has execute method from BaseWorkflow."""
        from attune.workflows.refactor_plan import RefactorPlanWorkflow

        wf = RefactorPlanWorkflow()
        assert hasattr(wf, "execute")
        assert callable(wf.execute)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
