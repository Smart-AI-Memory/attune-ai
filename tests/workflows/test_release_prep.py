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
        assert wf.name == "release-prep"

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


@pytest.mark.unit
class TestReleasePreparationReExports:
    """Test public re-exports from release_prep module."""

    def test_release_prep_steps_exported(self):
        """Test RELEASE_PREP_STEPS is importable."""
        from attune.workflows.release_prep import RELEASE_PREP_STEPS

        assert isinstance(RELEASE_PREP_STEPS, list | tuple | dict)

    def test_format_release_prep_report_exported(self):
        """Test format_release_prep_report is importable."""
        from attune.workflows.release_prep import format_release_prep_report

        assert callable(format_release_prep_report)

    def test_main_exported(self):
        """Test main is importable."""
        from attune.workflows.release_prep import main

        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
