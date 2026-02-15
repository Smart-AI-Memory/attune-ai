"""Unit tests for WizardInternalWorkflow.

Tests cover:
- Initialization and class attributes
- run_stage raises NotImplementedError

Created: 2026-02-15
"""

import pytest

from attune.wizards.internal_workflow import WizardInternalWorkflow
from attune.workflows.compat import ModelTier


class TestWizardInternalWorkflow:
    """Test WizardInternalWorkflow."""

    def test_class_attributes(self):
        """Test class-level attributes."""
        assert WizardInternalWorkflow.name == "wizard-internal"
        assert WizardInternalWorkflow.stages == []
        assert WizardInternalWorkflow.tier_map == {}

    def test_init(self):
        """Test initialization succeeds."""
        workflow = WizardInternalWorkflow()
        assert workflow is not None

    def test_init_with_provider(self):
        """Test initialization with provider."""
        workflow = WizardInternalWorkflow(provider="anthropic")
        assert workflow is not None

    @pytest.mark.asyncio
    async def test_run_stage_raises(self):
        """Test run_stage always raises NotImplementedError."""
        workflow = WizardInternalWorkflow()

        with pytest.raises(NotImplementedError, match="Wizards do not use run_stage"):
            await workflow.run_stage("test", ModelTier.CAPABLE, {})
