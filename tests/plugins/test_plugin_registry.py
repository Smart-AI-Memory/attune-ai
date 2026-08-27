"""Tests for Plugin Registry

Tests the plugin auto-discovery and management system.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest

from attune.plugins.base import BasePlugin, BaseWorkflow, PluginValidationError
from attune.plugins.registry import PluginRegistry, get_global_registry


@dataclass
class MockPluginMetadata:
    """Mock plugin metadata for testing"""

    name: str = "test_plugin"
    domain: str = "testing"
    version: str = "1.0.0"
    description: str = "Test plugin"


class MockWorkflow(BaseWorkflow):
    """Mock wizard for testing"""

    def __init__(self, workflow_id: str):
        self.workflow_id = workflow_id
        self._name = f"Test Wizard {workflow_id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> int:
        return self._level

    def get_required_context(self) -> list[str]:
        """Return empty list for mock wizard"""
        return []

    async def analyze(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"predictions": [], "recommendations": [], "confidence": 0.9}


class MockPlugin(BasePlugin):
    """Mock plugin for testing"""

    def __init__(self, name: str = "test", domain: str = "testing", version: str = "1.0.0"):
        self._metadata = MockPluginMetadata(name=name, domain=domain, version=version)
        self._custom_workflows: dict[str, BaseWorkflow] = {}
        super().__init__()

    def get_metadata(self) -> MockPluginMetadata:
        return self._metadata

    def register_workflows(self) -> dict[str, BaseWorkflow]:
        """Return custom wizards added via add_workflow"""
        return self._custom_workflows

    def initialize(self) -> None:
        """Override to use custom wizards"""
        if self._initialized:
            return
        self._workflows = self._custom_workflows
        self._initialized = True

    def add_workflow(self, workflow_id: str, wizard: BaseWorkflow):
        """Add a wizard to this mock plugin"""
        self._custom_workflows[workflow_id] = wizard
        if self._initialized:
            self._workflows[workflow_id] = wizard

    def list_workflows(self) -> list[str]:
        return list(self._custom_workflows.keys())

    def get_workflow(self, workflow_id: str):
        return self._custom_workflows.get(workflow_id)

    def get_workflow_info(self, workflow_id: str) -> dict[str, Any]:
        wizard = self._custom_workflows.get(workflow_id)
        if wizard:
            return {
                "id": workflow_id,
                "name": wizard.name,
                "domain": self._metadata.domain,
            }
        return None


@patch("attune.plugins.registry._BUILTIN_PLUGINS", ())
class TestPluginRegistryBasics:
    """Test basic registry operations"""

    def test_registry_initialization(self):
        """Test registry can be created"""
        registry = PluginRegistry()
        assert registry is not None
        assert registry._plugins == {}
        assert registry._auto_discovered is False

    def test_register_plugin(self):
        """Test manual plugin registration"""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")

        registry.register_plugin("test", plugin)

        assert "test" in registry._plugins
        assert registry._plugins["test"] == plugin

    def test_register_plugin_without_name(self):
        """Test registering plugin with invalid metadata raises error"""
        registry = PluginRegistry()
        plugin = MockPlugin(name="", domain="software")  # Empty name

        with pytest.raises(PluginValidationError, match="missing 'name'"):
            registry.register_plugin("test", plugin)

    def test_register_plugin_without_domain(self):
        """Test registering plugin without domain raises error"""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="")  # Empty domain

        with pytest.raises(PluginValidationError, match="missing 'domain'"):
            registry.register_plugin("test", plugin)

    def test_get_plugin(self):
        """Test retrieving a registered plugin"""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")
        registry.register_plugin("test", plugin)

        retrieved = registry.get_plugin("test")

        assert retrieved == plugin
        assert retrieved._initialized is True  # Should be initialized on retrieval

    def test_get_nonexistent_plugin(self):
        """Test retrieving non-existent plugin returns None"""
        registry = PluginRegistry()

        result = registry.get_plugin("nonexistent")

        assert result is None

    def test_list_plugins(self):
        """Test listing all registered plugins"""
        registry = PluginRegistry()
        plugin1 = MockPlugin(name="plugin1", domain="software")
        plugin2 = MockPlugin(name="plugin2", domain="healthcare")

        registry.register_plugin("plugin1", plugin1)
        registry.register_plugin("plugin2", plugin2)

        plugins = registry.list_plugins()

        assert len(plugins) == 2
        assert "plugin1" in plugins
        assert "plugin2" in plugins


class TestPluginRegistryAutoDiscovery:
    """Test built-in plugin loading (the entry-point scan died in 16.0.0)."""

    @patch("attune.plugins.registry._BUILTIN_PLUGINS", ())
    def test_auto_discover_empty_table(self):
        """An empty builtin table loads nothing."""
        registry = PluginRegistry()
        registry.auto_discover()

        assert registry._auto_discovered is True
        assert len(registry._plugins) == 0

    @patch(
        "attune.plugins.registry._BUILTIN_PLUGINS",
        (("test_plugin", "_fake_builtin_plugin_mod", "MockPlugin"),),
    )
    def test_auto_discover_loads_builtin_table(self):
        """Table entries are imported and registered."""
        import sys
        import types

        mod = types.ModuleType("_fake_builtin_plugin_mod")
        mod.MockPlugin = MockPlugin
        with patch.dict(sys.modules, {"_fake_builtin_plugin_mod": mod}):
            registry = PluginRegistry()
            registry.auto_discover()

        assert registry._auto_discovered is True
        assert len(registry._plugins) == 1
        assert "test_plugin" in registry._plugins

    @patch(
        "attune.plugins.registry._BUILTIN_PLUGINS",
        (("broken_plugin", "_module_that_does_not_exist", "Nope"),),
    )
    def test_auto_discover_handles_load_failures(self):
        """A broken builtin logs and is skipped, never raises."""
        registry = PluginRegistry()
        registry.auto_discover()  # Should not raise exception

        assert registry._auto_discovered is True
        assert len(registry._plugins) == 0  # Broken plugin not added

    @patch("attune.plugins.registry._BUILTIN_PLUGINS", ())
    def test_auto_discover_only_runs_once(self):
        """A second auto_discover on the same registry is a no-op."""
        registry = PluginRegistry()
        registry.auto_discover()
        first = registry._auto_discovered
        registry.auto_discover()  # Call again

        assert first is True and registry._auto_discovered is True


@patch("attune.plugins.registry._BUILTIN_PLUGINS", ())
class TestPluginRegistryWizards:
    """Test wizard-related functionality"""

    def test_list_all_workflows(self):
        """Test listing all wizards from all plugins"""
        registry = PluginRegistry()

        plugin1 = MockPlugin(name="plugin1", domain="software")
        plugin1.add_workflow("wizard1", MockWorkflow("wizard1"))
        plugin1.add_workflow("wizard2", MockWorkflow("wizard2"))

        plugin2 = MockPlugin(name="plugin2", domain="healthcare")
        plugin2.add_workflow("wizard3", MockWorkflow("wizard3"))

        registry.register_plugin("plugin1", plugin1)
        registry.register_plugin("plugin2", plugin2)

        all_workflows = registry.list_all_workflows()

        assert len(all_workflows) == 2
        assert "plugin1" in all_workflows
        assert "plugin2" in all_workflows
        assert len(all_workflows["plugin1"]) == 2
        assert len(all_workflows["plugin2"]) == 1

    def test_get_workflow(self):
        """Test retrieving a specific wizard"""
        registry = PluginRegistry()

        plugin = MockPlugin(name="test", domain="software")
        wizard = MockWorkflow("test_wizard")
        plugin.add_workflow("test_wizard", wizard)

        registry.register_plugin("test", plugin)

        retrieved = registry.get_workflow("test", "test_wizard")

        assert retrieved == wizard

    def test_get_workflow_from_nonexistent_plugin(self):
        """Test getting wizard from non-existent plugin returns None"""
        registry = PluginRegistry()

        result = registry.get_workflow("nonexistent", "wizard")

        assert result is None

    def test_get_workflow_info(self):
        """Test retrieving wizard information"""
        registry = PluginRegistry()

        plugin = MockPlugin(name="test", domain="software")
        wizard = MockWorkflow("test_wizard")
        plugin.add_workflow("test_wizard", wizard)

        registry.register_plugin("test", plugin)

        info = registry.get_workflow_info("test", "test_wizard")

        assert info is not None
        assert info["id"] == "test_wizard"

    def test_find_workflows_by_domain(self):
        """Test finding wizards by domain"""
        registry = PluginRegistry()

        plugin1 = MockPlugin(name="plugin1", domain="software")
        plugin1.add_workflow("wizard1", MockWorkflow("wizard1"))

        plugin2 = MockPlugin(name="plugin2", domain="software")
        plugin2.add_workflow("wizard2", MockWorkflow("wizard2"))

        plugin3 = MockPlugin(name="plugin3", domain="healthcare")
        plugin3.add_workflow("wizard3", MockWorkflow("wizard3"))

        registry.register_plugin("plugin1", plugin1)
        registry.register_plugin("plugin2", plugin2)
        registry.register_plugin("plugin3", plugin3)

        software_workflows = registry.find_workflows_by_domain("software")

        assert len(software_workflows) == 2
        for wizard_info in software_workflows:
            assert wizard_info["domain"] == "software"
            assert "plugin" in wizard_info


@patch("attune.plugins.registry._BUILTIN_PLUGINS", ())
class TestPluginRegistryStatistics:
    """Test statistics functionality"""

    def test_get_statistics_empty_registry(self):
        """Test statistics for empty registry"""
        registry = PluginRegistry()

        stats = registry.get_statistics()

        assert stats["total_plugins"] == 0
        assert stats["total_workflows"] == 0

    def test_get_statistics_with_plugins(self):
        """Test statistics with registered plugins"""
        registry = PluginRegistry()

        plugin1 = MockPlugin(name="plugin1", domain="software", version="1.0.0")
        plugin1.add_workflow("wizard1", MockWorkflow("wizard1"))
        plugin1.add_workflow("wizard2", MockWorkflow("wizard2"))

        plugin2 = MockPlugin(name="plugin2", domain="healthcare", version="2.0.0")
        plugin2.add_workflow("wizard3", MockWorkflow("wizard3"))

        registry.register_plugin("plugin1", plugin1)
        registry.register_plugin("plugin2", plugin2)

        stats = registry.get_statistics()

        assert stats["total_plugins"] == 2
        assert stats["total_workflows"] == 3
        assert len(stats["plugins"]) == 2

        # Check plugin info
        plugin_names = [p["name"] for p in stats["plugins"]]
        assert "plugin1" in plugin_names
        assert "plugin2" in plugin_names


class TestGlobalRegistry:
    """Test global registry singleton"""

    def test_get_global_registry(self):
        """Test getting global registry instance"""
        registry1 = get_global_registry()
        registry2 = get_global_registry()

        # Should return same instance
        assert registry1 is registry2

    @patch("attune.plugins.registry._global_registry", None)
    def test_global_registry_auto_discovers(self):
        """Test global registry auto-discovers on first access"""
        with patch("attune.plugins.registry._BUILTIN_PLUGINS", ()):
            registry = get_global_registry()

            assert registry._auto_discovered is True


@patch("attune.plugins.registry._BUILTIN_PLUGINS", ())
class TestPluginRegistryEdgeCases:
    """Test edge cases and error conditions"""

    def test_register_plugin_with_get_metadata_error(self):
        """Test registering plugin that raises error in get_metadata"""
        registry = PluginRegistry()

        plugin = Mock()
        plugin.get_metadata.side_effect = Exception("Metadata error")

        with pytest.raises(PluginValidationError, match="Invalid plugin metadata"):
            registry.register_plugin("broken", plugin)

    def test_list_plugins_triggers_auto_discover(self):
        """Test that list_plugins triggers auto-discovery"""
        registry = PluginRegistry()
        assert registry._auto_discovered is False

        registry.list_plugins()

        assert registry._auto_discovered is True

    def test_get_plugin_triggers_auto_discover(self):
        """Test that get_plugin triggers auto-discovery"""
        registry = PluginRegistry()
        assert registry._auto_discovered is False

        registry.get_plugin("test")

        assert registry._auto_discovered is True

    def test_find_workflows_with_none_info(self):
        """Test finding wizards when get_workflow_info returns None"""
        registry = PluginRegistry()

        plugin = MockPlugin(name="test", domain="software")
        # Don't add any wizards, so get_workflow_info will return None
        plugin.add_workflow("invalid", MockWorkflow("invalid"))

        # Make get_workflow_info return None
        plugin.get_workflow_info = Mock(return_value=None)

        registry.register_plugin("test", plugin)

        # Should not crash, just return empty list
        results = registry.find_workflows_by_domain("software")
        assert results == []

    def test_get_workflow_info_from_nonexistent_plugin(self):
        """Test get_workflow_info from non-existent plugin returns None"""
        registry = PluginRegistry()

        result = registry.get_workflow_info("nonexistent", "wizard")

        assert result is None

    def test_list_all_workflows_triggers_auto_discover(self):
        """Test that list_all_workflows triggers auto-discovery"""
        registry = PluginRegistry()
        assert registry._auto_discovered is False

        registry.list_all_workflows()

        assert registry._auto_discovered is True

    def test_find_workflows_by_domain_triggers_auto_discover(self):
        """Test that find_workflows_by_domain triggers auto-discovery"""
        registry = PluginRegistry()
        assert registry._auto_discovered is False

        registry.find_workflows_by_domain("software")

        assert registry._auto_discovered is True

    def test_get_statistics_triggers_auto_discover(self):
        """Test that get_statistics triggers auto-discovery"""
        registry = PluginRegistry()
        assert registry._auto_discovered is False

        registry.get_statistics()

        assert registry._auto_discovered is True

    def test_get_plugin_skips_auto_discover_when_already_discovered(self):
        """Test get_plugin skips auto-discover when already run."""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")
        registry.register_plugin("test", plugin)
        registry.auto_discover()

        # Call get_plugin after auto_discover already ran
        retrieved = registry.get_plugin("test")
        assert retrieved == plugin

    def test_list_plugins_skips_auto_discover_when_already_discovered(self):
        """Test list_plugins skips auto-discover when already run."""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")
        registry.register_plugin("test", plugin)
        registry.auto_discover()

        plugins = registry.list_plugins()
        assert "test" in plugins

    def test_list_all_workflows_skips_auto_discover_when_already_discovered(self):
        """Test list_all_workflows skips auto-discover when already run."""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")
        plugin.add_workflow("w1", MockWorkflow("w1"))
        registry.register_plugin("test", plugin)
        registry.auto_discover()

        all_wf = registry.list_all_workflows()
        assert "test" in all_wf
        assert "w1" in all_wf["test"]

    def test_find_workflows_by_domain_skips_auto_discover_when_already_discovered(self):
        """Test find_workflows_by_domain skips auto-discover when already run."""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")
        plugin.add_workflow("w1", MockWorkflow("w1"))
        registry.register_plugin("test", plugin)
        registry.auto_discover()

        results = registry.find_workflows_by_domain("software")
        assert len(results) == 1

    def test_get_statistics_skips_auto_discover_when_already_discovered(self):
        """Test get_statistics skips auto-discover when already run."""
        registry = PluginRegistry()
        plugin = MockPlugin(name="test", domain="software")
        plugin.add_workflow("w1", MockWorkflow("w1"))
        registry.register_plugin("test", plugin)
        registry.auto_discover()

        stats = registry.get_statistics()
        assert stats["total_plugins"] == 1
        assert stats["total_workflows"] == 1

    def test_find_workflows_by_domain_with_none_info(self):
        """Test find_workflows_by_domain when get_workflow_info returns None."""
        registry = PluginRegistry()

        plugin = MockPlugin(name="test", domain="software")
        plugin.add_workflow("invalid", MockWorkflow("invalid"))
        plugin.get_workflow_info = Mock(return_value=None)

        registry.register_plugin("test", plugin)

        results = registry.find_workflows_by_domain("software")
        assert results == []
