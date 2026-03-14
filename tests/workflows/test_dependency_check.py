"""Tests for DependencyCheckWorkflow (SDK-native) — alternate test file.

Validates class attributes and construction.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestDependencyCheckWorkflow:
    """Test SDK-native DependencyCheckWorkflow."""

    def test_import_from_package(self):
        """Test workflow is importable from workflows package."""
        from attune.workflows import DependencyCheckWorkflow

        assert DependencyCheckWorkflow is not None

    def test_name(self):
        """Test workflow name attribute."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf.name == "dependency-check"

    def test_stages_single_agent(self):
        """Test workflow has single agent stage."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf.stages == ["agent-check"]

    def test_tier_map_capable(self):
        """Test tier map maps agent stage to CAPABLE."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf.tier_map["agent-check"] == ModelTier.CAPABLE

    def test_description_contains_agent_sdk(self):
        """Test description mentions Agent SDK."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert "Agent SDK" in wf.description

    def test_inherits_base_workflow(self):
        """Test workflow inherits from BaseWorkflow."""
        from attune.workflows.base import BaseWorkflow
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        assert issubclass(DependencyCheckWorkflow, BaseWorkflow)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
