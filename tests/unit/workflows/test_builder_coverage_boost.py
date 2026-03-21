"""Comprehensive coverage tests for Workflow Builder module.

Tests WorkflowBuilder fluent API for complex workflow construction.

Copyright 2025 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from unittest.mock import MagicMock

import pytest

import attune.workflows.builder as builder_module

WorkflowBuilder = builder_module.WorkflowBuilder
workflow_builder = builder_module.workflow_builder


# Mock workflow class for testing
class MockWorkflow:
    """Mock workflow for testing builder."""

    def __init__(self, **kwargs):
        """Store all kwargs for verification."""
        self.kwargs = kwargs


@pytest.mark.unit
class TestWorkflowBuilderInit:
    """Test WorkflowBuilder initialization."""

    def test_workflow_builder_initialization(self):
        """Test creating WorkflowBuilder with workflow class."""
        builder = WorkflowBuilder(MockWorkflow)

        assert builder.workflow_class == MockWorkflow
        assert builder._config is None
        assert builder._executor is None
        assert builder._provider is None
        assert builder._cache is None
        assert builder._enable_cache is True
        assert builder._telemetry_backend is None
        assert builder._enable_telemetry is True
        assert builder._progress_callback is None
        assert builder._tier_tracker is None
        assert builder._routing_strategy is None

    def test_workflow_builder_stores_class_reference(self):
        """Test that builder stores workflow class reference."""

        class CustomWorkflow:
            def __init__(self):
                pass

        builder = WorkflowBuilder(CustomWorkflow)
        assert builder.workflow_class is CustomWorkflow


@pytest.mark.unit
class TestWorkflowBuilderWithMethods:
    """Test WorkflowBuilder with_* configuration methods."""

    def test_with_config_sets_config(self):
        """Test with_config() sets configuration."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_config = MagicMock()

        result = builder.with_config(mock_config)

        assert builder._config is mock_config
        assert result is builder  # Returns self for chaining

    def test_with_executor_sets_executor(self):
        """Test with_executor() sets executor."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_executor = MagicMock()

        result = builder.with_executor(mock_executor)

        assert builder._executor is mock_executor
        assert result is builder

    def test_with_provider_sets_provider(self):
        """Test with_provider() sets provider."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_provider = MagicMock()

        result = builder.with_provider(mock_provider)

        assert builder._provider is mock_provider
        assert result is builder

    def test_with_cache_is_noop(self):
        """Test with_cache() is a no-op (Anthropic handles caching)."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_cache = MagicMock()

        result = builder.with_cache(mock_cache)

        # with_cache is a no-op — returns self for chaining
        assert result is builder

    def test_with_cache_enabled_true(self):
        """Test with_cache_enabled(True)."""
        builder = WorkflowBuilder(MockWorkflow)

        result = builder.with_cache_enabled(True)

        assert builder._enable_cache is True
        assert result is builder

    def test_with_cache_enabled_false(self):
        """Test with_cache_enabled(False)."""
        builder = WorkflowBuilder(MockWorkflow)

        result = builder.with_cache_enabled(False)

        assert builder._enable_cache is False
        assert result is builder

    def test_with_telemetry_sets_backend(self):
        """Test with_telemetry() sets telemetry backend."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_telemetry = MagicMock()

        result = builder.with_telemetry(mock_telemetry)

        assert builder._telemetry_backend is mock_telemetry
        assert result is builder

    def test_with_telemetry_enabled_true(self):
        """Test with_telemetry_enabled(True)."""
        builder = WorkflowBuilder(MockWorkflow)

        result = builder.with_telemetry_enabled(True)

        assert builder._enable_telemetry is True
        assert result is builder

    def test_with_telemetry_enabled_false(self):
        """Test with_telemetry_enabled(False)."""
        builder = WorkflowBuilder(MockWorkflow)

        result = builder.with_telemetry_enabled(False)

        assert builder._enable_telemetry is False
        assert result is builder

    def test_with_progress_callback_sets_callback(self):
        """Test with_progress_callback() sets callback."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_callback = MagicMock()

        result = builder.with_progress_callback(mock_callback)

        assert builder._progress_callback is mock_callback
        assert result is builder

    def test_with_progress_callback_accepts_callable(self):
        """Test with_progress_callback() accepts plain callable."""
        builder = WorkflowBuilder(MockWorkflow)

        def my_callback(stage: str, current: int, total: int):
            pass

        result = builder.with_progress_callback(my_callback)

        assert builder._progress_callback is my_callback
        assert result is builder

    def test_with_tier_tracker_sets_tracker(self):
        """Test with_tier_tracker() sets tier tracker."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_tracker = MagicMock()

        result = builder.with_tier_tracker(mock_tracker)

        assert builder._tier_tracker is mock_tracker
        assert result is builder

    def test_with_routing_sets_strategy(self):
        """Test with_routing() sets routing strategy."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_strategy = MagicMock()

        result = builder.with_routing(mock_strategy)

        assert builder._routing_strategy is mock_strategy
        assert result is builder


@pytest.mark.unit
class TestWorkflowBuilderBuild:
    """Test WorkflowBuilder build() method."""

    def test_build_with_no_configuration(self):
        """Test build() with default configuration."""
        builder = WorkflowBuilder(MockWorkflow)

        workflow = builder.build()

        # Verify defaults are applied
        assert isinstance(workflow, MockWorkflow)
        assert workflow.kwargs["enable_cache"] is True
        assert workflow.kwargs["enable_telemetry"] is True
        assert "config" not in workflow.kwargs
        assert "executor" not in workflow.kwargs

    def test_build_with_config(self):
        """Test build() includes config when set."""
        mock_config = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_config(mock_config)

        workflow = builder.build()

        assert workflow.kwargs["config"] is mock_config

    def test_build_with_executor(self):
        """Test build() includes executor when set."""
        mock_executor = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_executor(mock_executor)

        workflow = builder.build()

        assert workflow.kwargs["executor"] is mock_executor

    def test_build_with_provider(self):
        """Test build() includes provider when set."""
        mock_provider = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_provider(mock_provider)

        workflow = builder.build()

        assert workflow.kwargs["provider"] is mock_provider

    def test_build_with_cache_noop(self):
        """Test build() ignores cache (Anthropic handles caching)."""
        mock_cache = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_cache(mock_cache)

        workflow = builder.build()

        # Cache is no longer passed through — Anthropic handles it server-side
        assert "cache" not in workflow.kwargs or workflow.kwargs.get("cache") is None

    def test_build_with_cache_disabled(self):
        """Test build() respects cache_enabled flag."""
        builder = WorkflowBuilder(MockWorkflow).with_cache_enabled(False)

        workflow = builder.build()

        assert workflow.kwargs["enable_cache"] is False

    def test_build_with_telemetry_backend(self):
        """Test build() includes telemetry backend when set."""
        mock_telemetry = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_telemetry(mock_telemetry)

        workflow = builder.build()

        assert workflow.kwargs["telemetry_backend"] is mock_telemetry

    def test_build_with_telemetry_disabled(self):
        """Test build() respects telemetry_enabled flag."""
        builder = WorkflowBuilder(MockWorkflow).with_telemetry_enabled(False)

        workflow = builder.build()

        assert workflow.kwargs["enable_telemetry"] is False

    def test_build_with_progress_callback(self):
        """Test build() includes progress callback when set."""
        mock_callback = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_progress_callback(mock_callback)

        workflow = builder.build()

        assert workflow.kwargs["progress_callback"] is mock_callback

    def test_build_with_tier_tracker(self):
        """Test build() includes tier tracker when set."""
        mock_tracker = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_tier_tracker(mock_tracker)

        workflow = builder.build()

        assert workflow.kwargs["tier_tracker"] is mock_tracker

    def test_build_with_routing_strategy(self):
        """Test build() includes routing strategy when set."""
        mock_strategy = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_routing(mock_strategy)

        workflow = builder.build()

        assert workflow.kwargs["routing_strategy"] is mock_strategy

    def test_build_with_all_parameters(self):
        """Test build() with all parameters configured."""
        mock_config = MagicMock()
        mock_executor = MagicMock()
        mock_provider = MagicMock()
        mock_cache = MagicMock()
        mock_telemetry = MagicMock()
        mock_callback = MagicMock()
        mock_tracker = MagicMock()
        mock_strategy = MagicMock()

        builder = (
            WorkflowBuilder(MockWorkflow)
            .with_config(mock_config)
            .with_executor(mock_executor)
            .with_provider(mock_provider)
            .with_cache(mock_cache)
            .with_cache_enabled(False)
            .with_telemetry(mock_telemetry)
            .with_telemetry_enabled(False)
            .with_progress_callback(mock_callback)
            .with_tier_tracker(mock_tracker)
            .with_routing(mock_strategy)
        )

        workflow = builder.build()

        # Verify all parameters were passed
        assert workflow.kwargs["config"] is mock_config
        assert workflow.kwargs["executor"] is mock_executor
        assert workflow.kwargs["provider"] is mock_provider
        # cache is no longer passed — Anthropic handles it server-side
        assert workflow.kwargs["enable_cache"] is False
        assert workflow.kwargs["telemetry_backend"] is mock_telemetry
        assert workflow.kwargs["enable_telemetry"] is False
        assert workflow.kwargs["progress_callback"] is mock_callback
        assert workflow.kwargs["tier_tracker"] is mock_tracker
        assert workflow.kwargs["routing_strategy"] is mock_strategy


@pytest.mark.unit
class TestWorkflowBuilderChaining:
    """Test WorkflowBuilder method chaining."""

    def test_method_chaining_returns_self(self):
        """Test that all with_* methods return self for chaining."""
        builder = WorkflowBuilder(MockWorkflow)
        mock_obj = MagicMock()

        # Test each method returns builder
        assert builder.with_config(mock_obj) is builder
        assert builder.with_executor(mock_obj) is builder
        assert builder.with_provider(mock_obj) is builder
        assert builder.with_cache(mock_obj) is builder
        assert builder.with_cache_enabled(True) is builder
        assert builder.with_telemetry(mock_obj) is builder
        assert builder.with_telemetry_enabled(True) is builder
        assert builder.with_progress_callback(mock_obj) is builder
        assert builder.with_tier_tracker(mock_obj) is builder
        assert builder.with_routing(mock_obj) is builder

    def test_fluent_api_chaining(self):
        """Test fluent API with chained method calls."""
        mock_config = MagicMock()
        mock_cache = MagicMock()

        workflow = (
            WorkflowBuilder(MockWorkflow)
            .with_config(mock_config)
            .with_cache(mock_cache)
            .with_cache_enabled(True)
            .with_telemetry_enabled(False)
            .build()
        )

        assert workflow.kwargs["config"] is mock_config
        # cache is no longer passed — Anthropic handles it server-side
        assert workflow.kwargs["enable_cache"] is True
        assert workflow.kwargs["enable_telemetry"] is False

    def test_order_independent_chaining(self):
        """Test that configuration order doesn't matter."""
        mock_config = MagicMock()

        # Order 1
        workflow1 = (
            WorkflowBuilder(MockWorkflow).with_cache_enabled(False).with_config(mock_config).build()
        )

        # Order 2 (reversed)
        workflow2 = (
            WorkflowBuilder(MockWorkflow).with_config(mock_config).with_cache_enabled(False).build()
        )

        # Both should have same configuration
        assert workflow1.kwargs["config"] is mock_config
        assert workflow2.kwargs["config"] is mock_config
        assert workflow1.kwargs["enable_cache"] is False
        assert workflow2.kwargs["enable_cache"] is False


@pytest.mark.unit
class TestWorkflowBuilderFactory:
    """Test workflow_builder() factory function."""

    def test_workflow_builder_factory_returns_builder(self):
        """Test workflow_builder() creates WorkflowBuilder."""
        builder = workflow_builder(MockWorkflow)

        assert isinstance(builder, WorkflowBuilder)
        assert builder.workflow_class == MockWorkflow

    def test_workflow_builder_factory_is_chainable(self):
        """Test workflow_builder() result is chainable."""
        mock_config = MagicMock()

        workflow = workflow_builder(MockWorkflow).with_config(mock_config).build()

        assert isinstance(workflow, MockWorkflow)
        assert workflow.kwargs["config"] is mock_config

    def test_workflow_builder_factory_equivalent_to_constructor(self):
        """Test factory produces same result as constructor."""
        mock_config = MagicMock()

        # Using constructor
        workflow1 = WorkflowBuilder(MockWorkflow).with_config(mock_config).build()

        # Using factory
        workflow2 = workflow_builder(MockWorkflow).with_config(mock_config).build()

        # Both should have same configuration
        assert workflow1.kwargs == workflow2.kwargs


@pytest.mark.unit
class TestWorkflowBuilderEdgeCases:
    """Test edge cases and error conditions."""

    def test_build_can_be_called_multiple_times(self):
        """Test that build() can be called multiple times."""
        mock_config = MagicMock()
        builder = WorkflowBuilder(MockWorkflow).with_config(mock_config)

        workflow1 = builder.build()
        workflow2 = builder.build()

        # Both should be valid instances
        assert isinstance(workflow1, MockWorkflow)
        assert isinstance(workflow2, MockWorkflow)
        assert workflow1 is not workflow2  # Different instances

    def test_overwriting_configuration(self):
        """Test that later configuration overwrites earlier."""
        mock_config1 = MagicMock()
        mock_config2 = MagicMock()

        builder = (
            WorkflowBuilder(MockWorkflow)
            .with_config(mock_config1)
            .with_config(mock_config2)  # Overwrites first
        )

        workflow = builder.build()

        assert workflow.kwargs["config"] is mock_config2
        assert workflow.kwargs["config"] is not mock_config1

    def test_toggling_boolean_flags(self):
        """Test toggling cache and telemetry flags."""
        builder = (
            WorkflowBuilder(MockWorkflow)
            .with_cache_enabled(False)
            .with_cache_enabled(True)  # Toggle back
            .with_telemetry_enabled(False)
            .with_telemetry_enabled(True)  # Toggle back
        )

        workflow = builder.build()

        assert workflow.kwargs["enable_cache"] is True
        assert workflow.kwargs["enable_telemetry"] is True

    def test_none_values_not_included_in_kwargs(self):
        """Test that None optional values are not included in kwargs."""
        builder = WorkflowBuilder(MockWorkflow)
        # Don't set any optional parameters

        workflow = builder.build()

        # Only boolean flags should be present
        assert "config" not in workflow.kwargs
        assert "executor" not in workflow.kwargs
        assert "provider" not in workflow.kwargs
        assert "cache" not in workflow.kwargs
        assert "telemetry_backend" not in workflow.kwargs
        assert "progress_callback" not in workflow.kwargs
        assert "tier_tracker" not in workflow.kwargs
        assert "routing_strategy" not in workflow.kwargs

        # Boolean flags always present
        assert "enable_cache" in workflow.kwargs
        assert "enable_telemetry" in workflow.kwargs


@pytest.mark.unit
class TestWorkflowBuilderIntegration:
    """Integration tests for WorkflowBuilder."""

    def test_realistic_workflow_configuration(self):
        """Test realistic workflow configuration scenario."""

        class MyWorkflow:
            """Realistic workflow class."""

            def __init__(
                self,
                config=None,
                executor=None,
                enable_cache=True,
                enable_telemetry=True,
                progress_callback=None,
            ):
                self.config = config
                self.executor = executor
                self.enable_cache = enable_cache
                self.enable_telemetry = enable_telemetry
                self.progress_callback = progress_callback

        mock_config = MagicMock()
        mock_executor = MagicMock()

        def my_progress_callback(stage: str, current: int, total: int):
            print(f"{stage}: {current}/{total}")

        # Build workflow with realistic configuration
        workflow = (
            WorkflowBuilder(MyWorkflow)
            .with_config(mock_config)
            .with_executor(mock_executor)
            .with_cache_enabled(True)
            .with_telemetry_enabled(False)
            .with_progress_callback(my_progress_callback)
            .build()
        )

        # Verify configuration was applied
        assert workflow.config is mock_config
        assert workflow.executor is mock_executor
        assert workflow.enable_cache is True
        assert workflow.enable_telemetry is False
        assert workflow.progress_callback is my_progress_callback

    def test_minimal_configuration(self):
        """Test minimal configuration with just workflow class."""

        class MinimalWorkflow:
            def __init__(self, enable_cache=True, enable_telemetry=True):
                self.enable_cache = enable_cache
                self.enable_telemetry = enable_telemetry

        workflow = WorkflowBuilder(MinimalWorkflow).build()

        assert workflow.enable_cache is True
        assert workflow.enable_telemetry is True

    def test_complex_multi_step_configuration(self):
        """Test complex configuration built in multiple steps."""
        mock_config = MagicMock()
        mock_executor = MagicMock()
        mock_cache = MagicMock()

        # Step 1: Create builder
        builder = WorkflowBuilder(MockWorkflow)

        # Step 2: Configure in stages
        builder = builder.with_config(mock_config)
        builder = builder.with_executor(mock_executor)

        # Step 3: Add caching
        builder = builder.with_cache(mock_cache).with_cache_enabled(True)

        # Step 4: Disable telemetry
        builder = builder.with_telemetry_enabled(False)

        # Step 5: Build
        workflow = builder.build()

        # Verify all configuration was preserved
        assert workflow.kwargs["config"] is mock_config
        assert workflow.kwargs["executor"] is mock_executor
        # cache is no longer passed — Anthropic handles it server-side
        assert workflow.kwargs["enable_cache"] is True
        assert workflow.kwargs["enable_telemetry"] is False
