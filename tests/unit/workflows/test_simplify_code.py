"""Tests for SimplifyCodeWorkflow (SDK-native).

Validates class attributes, construction, and re-exports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestSimplifyCodeWorkflowAttributes:
    """Test SDK-native class attributes on SimplifyCodeWorkflow."""

    def test_import(self):
        """Test workflow is importable."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        assert SimplifyCodeWorkflow is not None

    def test_name(self):
        """Test workflow name."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow()
        assert wf.name == "simplify-code"

    def test_stages(self):
        """Test single agent stage."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow()
        assert wf.stages == ["agent-simplify"]

    def test_tier_map(self):
        """Test tier map uses CAPABLE for agent stage."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow()
        assert wf.tier_map == {"agent-simplify": ModelTier.CAPABLE}

    def test_description_mentions_agent_sdk(self):
        """Test description references Agent SDK."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow()
        assert "Agent SDK" in wf.description

    def test_constructor_accepts_kwargs(self):
        """Test constructor passes kwargs to BaseWorkflow."""
        from attune.workflows.simplify_code import SimplifyCodeWorkflow

        wf = SimplifyCodeWorkflow()
        assert wf is not None


@pytest.mark.unit
class TestSimplifyCodeReExports:
    """Test public re-exports from simplify_code module."""

    def test_simplify_focus_areas_exported(self):
        """Test SIMPLIFY_FOCUS_AREAS is importable."""
        from attune.workflows.simplify_code import SIMPLIFY_FOCUS_AREAS

        assert isinstance(SIMPLIFY_FOCUS_AREAS, list | tuple | dict)

    def test_simplify_categories_exported(self):
        """Test SIMPLIFY_CATEGORIES is importable."""
        from attune.workflows.simplify_code import SIMPLIFY_CATEGORIES

        assert isinstance(SIMPLIFY_CATEGORIES, list | tuple | dict | set | frozenset)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
