"""Smoke tests for quick validation of core functionality.

Run with: pytest -m smoke
These tests should complete in under 30 seconds and validate critical paths.
"""

import pytest

# Mark this file's tests as smoke tests
pytestmark = pytest.mark.smoke


class TestCoreImports:
    """Test that core modules can be imported."""

    def test_import_empathy_os(self):
        """Test main package import."""
        import attune

        assert attune is not None

    def test_import_workflows(self):
        """Test workflows import."""
        from attune import workflows

        assert workflows is not None

    def test_import_caching_mixin(self):
        """Test caching mixin import (no-op stub)."""
        from attune.workflows.caching import CachingMixin

        assert CachingMixin is not None

    def test_import_meta_workflows(self):
        """Test meta workflows import."""
        from attune import meta_workflows

        assert meta_workflows is not None

    def test_import_memory(self):
        """Test memory import."""
        from attune import memory

        assert memory is not None


class TestCoreClasses:
    """Test core class instantiation."""

    def test_workflow_base_import(self):
        """Test workflow base classes."""
        from attune.workflows.base import WorkflowResult

        # WorkflowResult has a different signature - just verify import
        assert WorkflowResult is not None

    def test_template_registry(self):
        """Test template registry loads built-in templates."""
        from attune.meta_workflows import TemplateRegistry

        registry = TemplateRegistry()
        templates = registry.list_templates()
        assert len(templates) >= 5  # Should have built-in templates

    def test_pattern_library(self):
        """Test pattern library instantiation."""
        from attune.pattern_library import PatternLibrary

        library = PatternLibrary()
        assert library is not None


class TestCLI:
    """Test CLI imports."""

    def test_cli_minimal_import(self):
        """Test CLI minimal module import."""
        from attune import cli_minimal

        assert cli_minimal is not None


class TestConfig:
    """Test configuration and security."""

    def test_validate_file_path(self):
        """Test path validation function exists."""
        from attune.security.path_validation import _validate_file_path

        # Function exists and works
        assert _validate_file_path is not None
        # Null bytes should be blocked
        with pytest.raises(ValueError, match="null"):
            _validate_file_path("test\x00file.txt")

    def test_config_dataclass(self):
        """Test config dataclass."""
        from attune.config import EmpathyConfig

        config = EmpathyConfig(user_id="test")
        assert config.user_id == "test"


class TestLLMToolkit:
    """Test LLM toolkit modules."""

    def test_hooks_import(self):
        """Test hooks module."""
        from attune.hooks import HookRegistry

        registry = HookRegistry()
        assert registry is not None

    def test_commands_import(self):
        """Test commands module."""
        from attune.commands import CommandRegistry

        CommandRegistry.reset_instance()
        registry = CommandRegistry.get_instance()
        assert registry is not None
        CommandRegistry.reset_instance()

    def test_learning_import(self):
        """Test learning module."""
        from attune.learning import PatternExtractor

        extractor = PatternExtractor()
        assert extractor is not None

    def test_context_import(self):
        """Test context module."""
        from attune.context import TokenBudgetAllocator

        # Should be able to import without error
        assert TokenBudgetAllocator is not None


class TestModelsAndCosts:
    """Test model registry and cost tracking."""

    def test_model_registry(self):
        """Test model registry has models defined."""
        from attune.models.registry import ModelRegistry

        registry = ModelRegistry()
        assert registry is not None

    def test_cost_tracker_import(self):
        """Test cost tracker."""
        from attune.cost_tracker import CostTracker

        tracker = CostTracker()
        assert tracker is not None

    def test_token_estimator(self):
        """Test token estimation."""
        from attune.models.token_estimator import estimate_tokens

        tokens = estimate_tokens("Hello, world!")
        assert tokens > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "smoke"])
