"""Attune AI - Plugin Registry

Auto-discovery and management of domain plugins.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging
from importlib.metadata import entry_points

from .base import BasePlugin, BaseWorkflow, PluginValidationError

logger = logging.getLogger(__name__)

# Primary entry point group (v2.7+)
_ENTRY_POINT_GROUP = "attune.plugins"

# Legacy entry point groups for backward compatibility (removed in 15.0.0).
# Both spellings shipped in docs/templates at different times, so discovery
# must read both — until this fix "empathy_framework.plugins" was registered
# in pyproject but never read (#2238 phantom-read instance).
_LEGACY_ENTRY_POINT_GROUPS = (
    "attune_framework.plugins",
    "empathy_framework.plugins",
)

# Module-level discovery cache: avoids repeated importlib.metadata scans.
# Maps entry-point name -> loaded plugin class.  Populated on first
# auto_discover() and reused by subsequent PluginRegistry instances.
_discovery_cache: dict[str, type] | None = None


class PluginRegistry:
    """Central registry for managing domain plugins.

    Features:
    - Auto-discovery via entry points
    - Manual registration
    - Lazy initialization
    - Graceful degradation (missing plugins don't crash)
    - Discovery caching (avoids repeated entry_points scans)
    """

    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: dict[str, BasePlugin] = {}
        self._auto_discovered = False
        self.logger = logging.getLogger("attune.plugins.registry")

    def auto_discover(self) -> None:
        """Automatically discover plugins via entry points.

        Plugins register themselves in pyproject.toml:

        [project.entry-points."attune.plugins"]
        software = "attune_software.plugin:SoftwarePlugin"
        healthcare = "attune_healthcare.plugin:HealthcarePlugin"

        Also checks the legacy "attune_framework.plugins" and
        "empathy_framework.plugins" groups for backward compatibility
        (removed in 15.0.0).

        Discovery results are cached at module level so that repeated
        PluginRegistry instances (e.g. after global reset) skip the
        importlib.metadata scan.
        """
        global _discovery_cache

        if self._auto_discovered:
            return

        self.logger.info("Auto-discovering plugins...")

        # Build or reuse the discovery cache
        if _discovery_cache is None:
            _discovery_cache = {}
            for group in (_ENTRY_POINT_GROUP, *_LEGACY_ENTRY_POINT_GROUPS):
                discovered = entry_points(group=group)
                for ep in discovered:
                    if ep.name not in _discovery_cache:
                        try:
                            _discovery_cache[ep.name] = ep.load()
                        except Exception as e:  # noqa: BLE001
                            # INTENTIONAL: entry point load is best-effort
                            self.logger.warning(
                                f"Failed to load plugin '{ep.name}': {e}",
                                exc_info=True,
                            )

        # Instantiate and register from cache
        for name, plugin_class in _discovery_cache.items():
            if name in self._plugins:
                continue
            try:
                plugin_instance = plugin_class()
                self.register_plugin(name, plugin_instance)
                plugin_instance.on_activate()
                self.logger.info(f"Successfully loaded plugin: {name}")
            except Exception as e:  # noqa: BLE001
                # INTENTIONAL: graceful degradation, log but don't crash
                self.logger.warning(f"Failed to init plugin '{name}': {e}", exc_info=True)

        self._auto_discovered = True
        self.logger.info(f"Auto-discovery complete. {len(self._plugins)} plugins loaded.")

    def register_plugin(self, name: str, plugin: BasePlugin) -> None:
        """Manually register a plugin.

        Args:
            name: Plugin identifier (e.g., 'software', 'healthcare')
            plugin: Plugin instance

        Raises:
            PluginValidationError: If plugin is invalid

        """
        # Validate plugin
        try:
            metadata = plugin.get_metadata()
            if not metadata.name:
                raise PluginValidationError("Plugin metadata missing 'name'")
            if not metadata.domain:
                raise PluginValidationError("Plugin metadata missing 'domain'")
        except Exception as e:  # noqa: BLE001
            raise PluginValidationError(f"Invalid plugin metadata: {e}") from e

        # Register
        self._plugins[name] = plugin
        self.logger.info(
            f"Registered plugin '{name}' (domain: {metadata.domain}, version: {metadata.version})",
        )

    def get_plugin(self, name: str) -> BasePlugin | None:
        """Get a plugin by name.

        Args:
            name: Plugin identifier

        Returns:
            Plugin instance or None if not found

        """
        if not self._auto_discovered:
            self.auto_discover()

        plugin = self._plugins.get(name)
        if plugin and not plugin._initialized:
            plugin.initialize()

        return plugin

    def list_plugins(self) -> list[str]:
        """List all registered plugin names.

        Returns:
            List of plugin identifiers

        """
        if not self._auto_discovered:
            self.auto_discover()

        return list(self._plugins.keys())

    def list_all_workflows(self) -> dict[str, list[str]]:
        """List all workflows from all plugins.

        Returns:
            Dictionary mapping plugin_name -> list of workflow_ids

        """
        if not self._auto_discovered:
            self.auto_discover()

        result = {}
        for plugin_name, plugin in self._plugins.items():
            result[plugin_name] = plugin.list_workflows()

        return result

    def get_workflow(self, plugin_name: str, workflow_id: str) -> type[BaseWorkflow] | None:
        """Get a workflow from a specific plugin.

        Args:
            plugin_name: Plugin identifier
            workflow_id: Workflow identifier within plugin

        Returns:
            Workflow class or None if not found

        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            self.logger.warning(f"Plugin '{plugin_name}' not found")
            return None

        return plugin.get_workflow(workflow_id)

    def get_workflow_info(self, plugin_name: str, workflow_id: str) -> dict | None:
        """Get information about a workflow.

        Args:
            plugin_name: Plugin identifier
            workflow_id: Workflow identifier

        Returns:
            Dictionary with workflow metadata or None

        """
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            return None

        return plugin.get_workflow_info(workflow_id)

    def find_workflows_by_level(self, empathy_level: int) -> list[dict]:
        """Find all workflows operating at a specific empathy level.

        Args:
            empathy_level: Target empathy level (1-5)

        Returns:
            List of workflow info dictionaries

        """
        if not self._auto_discovered:
            self.auto_discover()

        results = []
        for plugin_name, plugin in self._plugins.items():
            for workflow_id in plugin.list_workflows():
                info = plugin.get_workflow_info(workflow_id)
                if info and info.get("empathy_level") == empathy_level:
                    info["plugin"] = plugin_name
                    results.append(info)

        return results

    def find_workflows_by_domain(self, domain: str) -> list[dict]:
        """Find all workflows for a specific domain.

        Args:
            domain: Domain identifier (e.g., 'software', 'healthcare')

        Returns:
            List of workflow info dictionaries

        """
        if not self._auto_discovered:
            self.auto_discover()

        results = []
        for plugin_name, plugin in self._plugins.items():
            metadata = plugin.get_metadata()
            if metadata.domain == domain:
                for workflow_id in plugin.list_workflows():
                    info = plugin.get_workflow_info(workflow_id)
                    if info:
                        info["plugin"] = plugin_name
                        results.append(info)

        return results

    def get_statistics(self) -> dict:
        """Get registry statistics.

        Returns:
            Dictionary with counts and metadata

        """
        if not self._auto_discovered:
            self.auto_discover()

        total_workflows = sum(len(plugin.list_workflows()) for plugin in self._plugins.values())

        # Count workflows by level
        workflows_by_level = {}
        for level in range(1, 6):
            workflows_by_level[f"level_{level}"] = len(self.find_workflows_by_level(level))

        return {
            "total_plugins": len(self._plugins),
            "total_workflows": total_workflows,
            "plugins": [
                {
                    "name": name,
                    "domain": plugin.get_metadata().domain,
                    "version": plugin.get_metadata().version,
                    "workflow_count": len(plugin.list_workflows()),
                }
                for name, plugin in self._plugins.items()
            ],
            "workflows_by_level": workflows_by_level,
        }


# Global registry instance
_global_registry: PluginRegistry | None = None


def get_global_registry() -> PluginRegistry:
    """Get the global plugin registry instance (singleton).

    Returns:
        Global PluginRegistry instance

    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
        _global_registry.auto_discover()
    return _global_registry


def clear_discovery_cache() -> None:
    """Clear the module-level discovery cache.

    Useful in tests or when entry points have changed at runtime
    (e.g. after installing a new plugin package).
    """
    global _discovery_cache, _global_registry
    _discovery_cache = None
    _global_registry = None
