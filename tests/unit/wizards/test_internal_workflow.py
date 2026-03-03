"""Unit tests for attune.wizards.internal_workflow module.

Tests cover:
- Class attributes (name, description, stages, tier_map)
- Initialization with no args, with provider, with kwargs
- run_stage always raises NotImplementedError

Copyright 2026 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import pytest

from attune.wizards.internal_workflow import WizardInternalWorkflow
from attune.workflows.compat import ModelTier


@pytest.mark.unit
class TestWizardInternalWorkflowClassAttributes:
    """Tests for WizardInternalWorkflow class-level attributes."""

    def test_name_attribute(self) -> None:
        """Test the class-level name attribute is correct."""
        assert WizardInternalWorkflow.name == "wizard-internal"

    def test_description_attribute(self) -> None:
        """Test the class-level description attribute is set."""
        assert (
            WizardInternalWorkflow.description == "Internal workflow bridge for wizard LLM access"
        )

    def test_stages_attribute_is_empty_list(self) -> None:
        """Test the class-level stages attribute is an empty list."""
        assert WizardInternalWorkflow.stages == []

    def test_tier_map_attribute_is_empty_dict(self) -> None:
        """Test the class-level tier_map attribute is an empty dict."""
        assert WizardInternalWorkflow.tier_map == {}


@pytest.mark.unit
class TestWizardInternalWorkflowInit:
    """Tests for WizardInternalWorkflow initialization."""

    def test_init_no_args_succeeds(self) -> None:
        """Test that WizardInternalWorkflow instantiates with no arguments."""
        workflow = WizardInternalWorkflow()
        assert workflow is not None

    def test_init_with_provider_string_succeeds(self) -> None:
        """Test that provider argument is accepted."""
        workflow = WizardInternalWorkflow(provider="anthropic")
        assert workflow is not None

    def test_init_with_none_provider_succeeds(self) -> None:
        """Test that provider=None is accepted."""
        workflow = WizardInternalWorkflow(provider=None)
        assert workflow is not None

    def test_init_inherits_from_base_workflow(self) -> None:
        """Test that WizardInternalWorkflow is a BaseWorkflow subclass."""
        from attune.workflows.base import BaseWorkflow

        workflow = WizardInternalWorkflow()
        assert isinstance(workflow, BaseWorkflow)

    def test_instance_name_matches_class_attribute(self) -> None:
        """Test that instance name matches class-level name."""
        workflow = WizardInternalWorkflow()
        assert workflow.name == "wizard-internal"

    def test_instance_stages_matches_class_attribute(self) -> None:
        """Test that instance stages matches class-level stages."""
        workflow = WizardInternalWorkflow()
        assert workflow.stages == []

    def test_instance_tier_map_matches_class_attribute(self) -> None:
        """Test that instance tier_map matches class-level tier_map."""
        workflow = WizardInternalWorkflow()
        assert workflow.tier_map == {}


@pytest.mark.unit
class TestWizardInternalWorkflowRunStage:
    """Tests for WizardInternalWorkflow.run_stage method."""

    async def test_run_stage_raises_not_implemented_error(self) -> None:
        """Test that run_stage raises NotImplementedError."""
        workflow = WizardInternalWorkflow()
        with pytest.raises(NotImplementedError, match="Wizards do not use run_stage"):
            await workflow.run_stage("any-stage", ModelTier.CAPABLE, {})

    async def test_run_stage_raises_for_cheap_tier(self) -> None:
        """Test run_stage raises for CHEAP tier."""
        workflow = WizardInternalWorkflow()
        with pytest.raises(NotImplementedError):
            await workflow.run_stage("stage", ModelTier.CHEAP, {"data": "x"})

    async def test_run_stage_raises_for_premium_tier(self) -> None:
        """Test run_stage raises for PREMIUM tier."""
        workflow = WizardInternalWorkflow()
        with pytest.raises(NotImplementedError):
            await workflow.run_stage("stage", ModelTier.PREMIUM, None)

    async def test_run_stage_error_message_exact(self) -> None:
        """Test run_stage error message is exactly as specified."""
        workflow = WizardInternalWorkflow()
        with pytest.raises(NotImplementedError) as exc_info:
            await workflow.run_stage("whatever", ModelTier.CAPABLE, {})
        assert str(exc_info.value) == "Wizards do not use run_stage"
