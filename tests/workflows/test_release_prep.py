"""Tests for ReleasePreparationWorkflow (SDK-native).

Validates class attributes, construction, and re-exports.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.workflows.base import ModelTier


@pytest.mark.unit
class TestReleasePreparationWorkflowAttributes:
    """Test SDK-native class attributes on ReleasePreparationWorkflow."""

    def test_import(self):
        """Test workflow is importable."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        assert ReleasePreparationWorkflow is not None

    def test_name(self):
        """Test workflow name."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert wf.name == "release-notes"

    def test_stages(self):
        """Test single agent stage."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert wf.stages == ["agent-prep"]

    def test_tier_map(self):
        """Test tier map uses CAPABLE for agent stage."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert wf.tier_map == {"agent-prep": ModelTier.CAPABLE}

    def test_description_mentions_agent_sdk(self):
        """Test description references Agent SDK."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert "Agent SDK" in wf.description

    def test_constructor_accepts_kwargs(self):
        """Test constructor passes kwargs to BaseWorkflow."""
        from attune.workflows.release_prep import ReleasePreparationWorkflow

        wf = ReleasePreparationWorkflow()
        assert wf is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
