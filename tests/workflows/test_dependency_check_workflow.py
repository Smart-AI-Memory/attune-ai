"""Tests for DependencyCheckWorkflow (SDK-native).

Validates class attributes, construction, and re-exports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestDependencyCheckWorkflowAttributes:
    """Test SDK-native class attributes on DependencyCheckWorkflow."""

    def test_import(self):
        """Test workflow is importable."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        assert DependencyCheckWorkflow is not None

    def test_name(self):
        """Test workflow name."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf.name == "dependency-check"

    def test_stages(self):
        """Test single agent stage."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf.stages == ["agent-check"]

    def test_tier_map(self):
        """Test tier map uses CAPABLE for agent stage."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf.tier_map == {"agent-check": ModelTier.CAPABLE}

    def test_description_mentions_agent_sdk(self):
        """Test description references Agent SDK."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert "Agent SDK" in wf.description

    def test_constructor_accepts_kwargs(self):
        """Test constructor passes kwargs to BaseWorkflow."""
        from attune.workflows.dependency_check import DependencyCheckWorkflow

        wf = DependencyCheckWorkflow()
        assert wf is not None


@pytest.mark.unit
class TestDependencyCheckReExports:
    """Test public re-exports from dependency_check module."""

    def test_dependency_check_steps_exported(self):
        """Test DEPENDENCY_CHECK_STEPS is importable."""
        from attune.workflows.dependency_check import DEPENDENCY_CHECK_STEPS

        assert isinstance(DEPENDENCY_CHECK_STEPS, list | tuple | dict)

    def test_format_dependency_check_report_exported(self):
        """Test format_dependency_check_report is importable."""
        from attune.workflows.dependency_check import format_dependency_check_report

        assert callable(format_dependency_check_report)

    def test_main_exported(self):
        """Test main is importable."""
        from attune.workflows.dependency_check import main

        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
