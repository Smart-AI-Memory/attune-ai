"""Unit tests for workflow step configuration module.

This test suite provides comprehensive coverage for the workflow step configuration
system that enables declarative multi-model pipeline definition with tier routing
and resilience policies.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock, patch

import pytest

from attune.models import ModelTier
from attune.workflows.step_config import (
    WorkflowStepConfig,
    steps_from_tier_map,
    validate_step_config,
)


@pytest.mark.unit
class TestWorkflowStepConfigCreation:
    """Test suite for WorkflowStepConfig creation."""

    def test_create_step_config_with_required_fields(self):
        """Test creating step config with only required fields."""
        step = WorkflowStepConfig(
            name="triage",
            task_type="classify",
        )

        assert step.name == "triage"
        assert step.task_type == "classify"
        assert step.tier_hint is None
        assert step.provider_hint is None
        assert step.fallback_policy is None
        assert step.retry_policy is None
        assert step.timeout_seconds is None
        assert step.max_tokens is None
        assert step.description == ""
        assert step.metadata == {}


@pytest.mark.unit
class TestEffectiveTier:
    """Test suite for effective_tier property."""

    @patch("attune.workflows.step_config.get_tier_for_task")
    def test_effective_tier_uses_tier_hint_when_specified(self, mock_get_tier_for_task):
        """Test that effective_tier uses tier_hint when specified."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            tier_hint="premium",
        )

        assert step.effective_tier == "premium"
        # Should not call get_tier_for_task when tier_hint is set
        mock_get_tier_for_task.assert_not_called()

    @patch("attune.workflows.step_config.get_tier_for_task")
    def test_effective_tier_derives_from_task_type_when_no_hint(self, mock_get_tier_for_task):
        """Test that effective_tier derives from task_type when no tier_hint."""
        mock_tier = MagicMock()
        mock_tier.value = "capable"
        mock_get_tier_for_task.return_value = mock_tier

        step = WorkflowStepConfig(
            name="test",
            task_type="fix_bug",
        )

        assert step.effective_tier == "capable"
        mock_get_tier_for_task.assert_called_once_with("fix_bug")

    @patch("attune.workflows.step_config.get_tier_for_task")
    def test_effective_tier_enum_returns_model_tier(self, mock_get_tier_for_task):
        """Test that effective_tier_enum returns ModelTier enum."""
        mock_tier = MagicMock()
        mock_tier.value = "cheap"
        mock_get_tier_for_task.return_value = mock_tier

        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
        )

        result = step.effective_tier_enum
        assert isinstance(result, ModelTier)
        assert result == ModelTier.CHEAP


@pytest.mark.unit
class TestWithOverrides:
    """Test suite for with_overrides method."""

    def test_with_overrides_creates_new_instance(self):
        """Test that with_overrides creates a new instance."""
        original = WorkflowStepConfig(
            name="test",
            task_type="classify",
            tier_hint="cheap",
        )

        modified = original.with_overrides(tier_hint="premium")

        assert modified is not original
        assert modified.tier_hint == "premium"
        assert original.tier_hint == "cheap"

    def test_with_overrides_updates_tier_hint(self):
        """Test that with_overrides can update tier_hint."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            tier_hint="cheap",
        )

        modified = step.with_overrides(tier_hint="capable")
        assert modified.tier_hint == "capable"

    def test_with_overrides_updates_provider_hint(self):
        """Test that with_overrides can update provider_hint."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
        )

        modified = step.with_overrides(provider_hint="openai")
        assert modified.provider_hint == "openai"

    def test_with_overrides_updates_timeout(self):
        """Test that with_overrides can update timeout_seconds."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            timeout_seconds=60,
        )

        modified = step.with_overrides(timeout_seconds=120)
        assert modified.timeout_seconds == 120

    def test_with_overrides_preserves_unspecified_fields(self):
        """Test that with_overrides preserves fields not overridden."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            tier_hint="cheap",
            timeout_seconds=60,
            description="Test step",
        )

        modified = step.with_overrides(tier_hint="capable")

        assert modified.name == "test"
        assert modified.task_type == "classify"
        assert modified.timeout_seconds == 60
        assert modified.description == "Test step"

    def test_with_overrides_copies_metadata(self):
        """Test that with_overrides copies metadata dict."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            metadata={"key": "value"},
        )

        modified = step.with_overrides(tier_hint="capable")

        # Should be a copy, not the same dict
        assert modified.metadata == {"key": "value"}
        assert modified.metadata is not step.metadata


@pytest.mark.unit
class TestToDict:
    """Test suite for to_dict method."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all relevant fields."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            tier_hint="cheap",
            provider_hint="anthropic",
            timeout_seconds=60,
            max_tokens=2048,
            description="Test step",
            metadata={"key": "value"},
        )

        result = step.to_dict()

        assert result["name"] == "test"
        assert result["task_type"] == "classify"
        assert result["tier_hint"] == "cheap"
        assert result["provider_hint"] == "anthropic"
        assert result["timeout_seconds"] == 60
        assert result["max_tokens"] == 2048
        assert result["description"] == "Test step"
        assert result["metadata"] == {"key": "value"}

    @patch("attune.workflows.step_config.get_tier_for_task")
    def test_to_dict_includes_effective_tier(self, mock_get_tier_for_task):
        """Test that to_dict includes effective_tier."""
        mock_tier = MagicMock()
        mock_tier.value = "capable"
        mock_get_tier_for_task.return_value = mock_tier

        step = WorkflowStepConfig(
            name="test",
            task_type="fix_bug",
        )

        result = step.to_dict()
        assert "effective_tier" in result
        assert result["effective_tier"] == "capable"

    def test_to_dict_handles_none_policies(self):
        """Test that to_dict correctly reports missing policies."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
        )

        result = step.to_dict()
        assert result["has_fallback_policy"] is False
        assert result["has_retry_policy"] is False


@pytest.mark.unit
class TestFromDict:
    """Test suite for from_dict classmethod."""

    def test_from_dict_creates_step_config(self):
        """Test that from_dict creates WorkflowStepConfig."""
        data = {
            "name": "test",
            "task_type": "classify",
            "tier_hint": "cheap",
            "provider_hint": "anthropic",
            "timeout_seconds": 60,
            "max_tokens": 2048,
            "description": "Test step",
            "metadata": {"key": "value"},
        }

        step = WorkflowStepConfig.from_dict(data)

        assert step.name == "test"
        assert step.task_type == "classify"
        assert step.tier_hint == "cheap"
        assert step.provider_hint == "anthropic"
        assert step.timeout_seconds == 60
        assert step.max_tokens == 2048
        assert step.description == "Test step"
        assert step.metadata == {"key": "value"}

    def test_from_dict_handles_missing_optional_fields(self):
        """Test that from_dict handles missing optional fields."""
        data = {
            "name": "test",
            "task_type": "classify",
        }

        step = WorkflowStepConfig.from_dict(data)

        assert step.name == "test"
        assert step.task_type == "classify"
        assert step.tier_hint is None
        assert step.provider_hint is None
        assert step.description == ""
        assert step.metadata == {}

    def test_from_dict_does_not_restore_policies(self):
        """Test that from_dict does not restore policy objects."""
        data = {
            "name": "test",
            "task_type": "classify",
            "has_fallback_policy": True,  # Not used
            "has_retry_policy": True,  # Not used
        }

        step = WorkflowStepConfig.from_dict(data)

        # Policies should not be restored from dict
        assert step.fallback_policy is None
        assert step.retry_policy is None


@pytest.mark.unit
class TestValidateStepConfig:
    """Test suite for validate_step_config function."""

    def test_validate_step_config_passes_for_valid_config(self):
        """Test that validation passes for valid configuration."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
        )

        errors = validate_step_config(step)
        assert errors == []

    def test_validate_step_config_fails_for_empty_name(self):
        """Test that validation fails for empty name."""
        step = WorkflowStepConfig(
            name="",
            task_type="classify",
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("name is required" in err for err in errors)

    def test_validate_step_config_fails_for_empty_task_type(self):
        """Test that validation fails for empty task_type."""
        step = WorkflowStepConfig(
            name="test",
            task_type="",
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("task_type is required" in err for err in errors)

    def test_validate_step_config_fails_for_invalid_tier_hint(self):
        """Test that validation fails for invalid tier_hint."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            tier_hint="invalid_tier",
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("Invalid tier_hint" in err for err in errors)

    def test_validate_step_config_accepts_valid_tier_hints(self):
        """Test that validation accepts all valid tier hints."""
        valid_tiers = ["cheap", "capable", "premium"]

        for tier in valid_tiers:
            step = WorkflowStepConfig(
                name="test",
                task_type="classify",
                tier_hint=tier,
            )
            errors = validate_step_config(step)
            assert errors == [], f"Tier {tier} should be valid"

    def test_validate_step_config_fails_for_invalid_provider_hint(self):
        """Test that validation fails for invalid provider_hint."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            provider_hint="invalid_provider",
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("Invalid provider_hint" in err for err in errors)

    def test_validate_step_config_accepts_valid_provider_hints(self):
        """Test that validation accepts valid provider hints."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            provider_hint="anthropic",
        )
        errors = validate_step_config(step)
        assert errors == [], "Provider anthropic should be valid"

    def test_validate_step_config_fails_for_negative_timeout(self):
        """Test that validation fails for negative timeout_seconds."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            timeout_seconds=-10,
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("timeout_seconds must be positive" in err for err in errors)

    def test_validate_step_config_fails_for_zero_timeout(self):
        """Test that validation fails for zero timeout_seconds."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            timeout_seconds=0,
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("timeout_seconds must be positive" in err for err in errors)

    def test_validate_step_config_fails_for_negative_max_tokens(self):
        """Test that validation fails for negative max_tokens."""
        step = WorkflowStepConfig(
            name="test",
            task_type="classify",
            max_tokens=-100,
        )

        errors = validate_step_config(step)
        assert len(errors) > 0
        assert any("max_tokens must be positive" in err for err in errors)

    def test_validate_step_config_returns_multiple_errors(self):
        """Test that validation returns all errors, not just first one."""
        step = WorkflowStepConfig(
            name="",
            task_type="",
            tier_hint="invalid",
            timeout_seconds=-10,
        )

        errors = validate_step_config(step)

        # Should have multiple errors
        assert len(errors) >= 4


@pytest.mark.unit
class TestStepsFromTierMap:
    """Test suite for steps_from_tier_map function."""

    def test_steps_from_tier_map_creates_step_configs(self):
        """Test that steps_from_tier_map creates WorkflowStepConfig list."""
        stages = ["triage", "analysis", "synthesis"]
        tier_map = {"triage": "cheap", "analysis": "capable", "synthesis": "premium"}

        steps = steps_from_tier_map(stages, tier_map)

        assert len(steps) == 3
        assert all(isinstance(step, WorkflowStepConfig) for step in steps)

    def test_steps_from_tier_map_uses_tier_map_values(self):
        """Test that steps_from_tier_map uses tiers from tier_map."""
        stages = ["triage", "analysis"]
        tier_map = {"triage": "cheap", "analysis": "capable"}

        steps = steps_from_tier_map(stages, tier_map)

        assert steps[0].name == "triage"
        assert steps[0].tier_hint == "cheap"
        assert steps[1].name == "analysis"
        assert steps[1].tier_hint == "capable"

    def test_steps_from_tier_map_uses_default_for_missing_tier(self):
        """Test that steps_from_tier_map uses 'capable' for missing tier."""
        stages = ["triage", "missing"]
        tier_map = {"triage": "cheap"}

        steps = steps_from_tier_map(stages, tier_map)

        assert steps[1].name == "missing"
        assert steps[1].tier_hint == "capable"

    def test_steps_from_tier_map_uses_task_type_default(self):
        """Test that steps_from_tier_map uses task_type_default."""
        stages = ["test"]
        tier_map = {}

        steps = steps_from_tier_map(stages, tier_map, task_type_default="classify")

        assert steps[0].task_type == "classify"

    def test_steps_from_tier_map_handles_enum_tier_values(self):
        """Test that steps_from_tier_map handles ModelTier enum values."""
        stages = ["test"]
        mock_tier = MagicMock()
        mock_tier.value = "premium"
        tier_map = {"test": mock_tier}

        steps = steps_from_tier_map(stages, tier_map)

        assert steps[0].tier_hint == "premium"

    def test_steps_from_tier_map_handles_empty_stages(self):
        """Test that steps_from_tier_map handles empty stages list."""
        stages = []
        tier_map = {}

        steps = steps_from_tier_map(stages, tier_map)

        assert steps == []
