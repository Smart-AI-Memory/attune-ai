"""Smoke tests for attune.plugins module."""


class TestPluginsImports:
    """Verify the plugins package exports are importable."""

    def test_import_package(self):
        """Test that the plugins package imports cleanly."""
        from attune.plugins import (
            BasePlugin,
            PluginRegistry,
        )

        assert BasePlugin is not None
        assert PluginRegistry is not None

    def test_plugin_metadata_dataclass(self):
        """Test PluginMetadata instantiation."""
        from attune.plugins.base import PluginMetadata

        meta = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            domain="software",
            description="A test plugin",
            author="test",
            license="MIT",
            requires_core_version="3.0.0",
        )
        assert meta.name == "test-plugin"
        assert meta.dependencies is None

    def test_plugin_registry_instantiation(self):
        """Test PluginRegistry can be created."""
        from attune.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        assert registry._plugins == {}
        assert registry._auto_discovered is False

    def test_clear_discovery_cache(self):
        """Test clear_discovery_cache is callable."""
        from attune.plugins.registry import clear_discovery_cache

        # Should not raise
        clear_discovery_cache()

    def test_plugin_error_hierarchy(self):
        """Test that plugin errors are proper exceptions."""
        from attune.plugins.base import (
            PluginError,
            PluginLoadError,
            PluginValidationError,
        )

        assert issubclass(PluginLoadError, PluginError)
        assert issubclass(PluginValidationError, PluginError)
