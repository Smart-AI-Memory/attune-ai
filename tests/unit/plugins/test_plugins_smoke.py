"""Smoke tests for plugins.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestImports:
    """Verify module can be imported."""

    def test_module_imports(self) -> None:
        """Test that the module imports without error."""
        import attune.plugins

        assert attune.plugins is not None

    def test_base_classes_import(self) -> None:
        """Test that base classes import."""
        from attune.plugins import (
            BasePlugin,
            BaseWorkflow,
            PluginError,
            PluginLoadError,
            PluginMetadata,
            PluginValidationError,
        )

        assert BasePlugin is not None
        assert BaseWorkflow is not None
        assert PluginError is not None
        assert PluginLoadError is not None
        assert PluginMetadata is not None
        assert PluginValidationError is not None

    def test_registry_imports(self) -> None:
        """Test that registry classes import."""
        from attune.plugins import PluginRegistry, clear_discovery_cache, get_global_registry

        assert PluginRegistry is not None
        assert clear_discovery_cache is not None
        assert get_global_registry is not None


@pytest.mark.unit
class TestInstantiation:
    """Verify main classes can be instantiated."""

    def test_plugin_registry_instantiates(self) -> None:
        """Test PluginRegistry creation."""
        from attune.plugins import PluginRegistry

        registry = PluginRegistry()
        assert registry is not None

    def test_plugin_metadata_creation(self) -> None:
        """Test PluginMetadata dataclass creation."""
        from attune.plugins import PluginMetadata

        meta = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            domain="testing",
            description="A test plugin",
            author="Test Author",
            license="MIT",
            requires_core_version="3.0.0",
        )
        assert meta.name == "test-plugin"
        assert meta.dependencies is None

    def test_plugin_error_hierarchy(self) -> None:
        """Test that plugin errors inherit correctly."""
        from attune.plugins import PluginError, PluginLoadError, PluginValidationError

        assert issubclass(PluginLoadError, PluginError)
        assert issubclass(PluginValidationError, PluginError)

    def test_get_global_registry(self) -> None:
        """Test get_global_registry returns a PluginRegistry."""
        from attune.plugins import PluginRegistry, get_global_registry

        registry = get_global_registry()
        assert isinstance(registry, PluginRegistry)
