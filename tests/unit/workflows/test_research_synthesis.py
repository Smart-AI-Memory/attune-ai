"""Tests for ResearchSynthesisWorkflow (SDK-native).

Validates class attributes, construction, and re-exports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestResearchSynthesisWorkflowAttributes:
    """Test SDK-native class attributes on ResearchSynthesisWorkflow."""

    def test_import(self):
        """Test workflow is importable."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        assert ResearchSynthesisWorkflow is not None

    def test_name(self):
        """Test workflow name."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        wf = ResearchSynthesisWorkflow()
        assert wf.name == "research-synthesis"

    def test_stages(self):
        """Test single agent stage."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        wf = ResearchSynthesisWorkflow()
        assert wf.stages == ["agent-synthesis"]

    def test_tier_map(self):
        """Test tier map uses CAPABLE for agent stage."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        wf = ResearchSynthesisWorkflow()
        assert wf.tier_map == {"agent-synthesis": ModelTier.CAPABLE}

    def test_description_mentions_agent_sdk(self):
        """Test description references Agent SDK."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        wf = ResearchSynthesisWorkflow()
        assert "Agent SDK" in wf.description

    def test_constructor_accepts_kwargs(self):
        """Test constructor passes kwargs to BaseWorkflow."""
        from attune.workflows.research_synthesis import ResearchSynthesisWorkflow

        wf = ResearchSynthesisWorkflow()
        assert wf is not None


@pytest.mark.unit
class TestResearchSynthesisReExports:
    """Test public re-exports from research_synthesis module."""

    def test_summarize_step_exported(self):
        """Test SUMMARIZE_STEP is importable."""
        from attune.workflows.research_synthesis import SUMMARIZE_STEP

        assert SUMMARIZE_STEP is not None

    def test_analyze_step_exported(self):
        """Test ANALYZE_STEP is importable."""
        from attune.workflows.research_synthesis import ANALYZE_STEP

        assert ANALYZE_STEP is not None

    def test_synthesize_step_exported(self):
        """Test SYNTHESIZE_STEP is importable."""
        from attune.workflows.research_synthesis import SYNTHESIZE_STEP

        assert SYNTHESIZE_STEP is not None

    def test_synthesize_step_capable_exported(self):
        """Test SYNTHESIZE_STEP_CAPABLE is importable."""
        from attune.workflows.research_synthesis import SYNTHESIZE_STEP_CAPABLE

        assert SYNTHESIZE_STEP_CAPABLE is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
