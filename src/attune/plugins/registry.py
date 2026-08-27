"""Attune AI - Plugin Registry

Auto-discovery and management of domain plugins.

Copyright 2025 Smart AI Memory, LLC
Licensed under the Apache License, Version 2.0
"""

import logging

from .base import BasePlugin, BaseWorkflow, PluginValidationError

logger = logging.getLogger(__name__)

# The bundled plugins, loaded directly. The "attune.plugins" entry-point
# group was removed in 16.0.0 (release-16-manifest D1: both registered
# plugins ship in the wheel, so the discovery indirection had exactly one
# configuration). Third-party extension returns via the ruled extension
# system; the BasePlugin contract is unchanged.
_BUILTIN_PLUGINS: tuple[tuple[str, str, str], ...] = (
    ("software", "attune_software.plugin", "SoftwarePlugin"),
    ("redis", "attune_redis.plugin", "RedisPlugin"),
)

# Module-level discovery cache: maps plugin name -> loaded plugin class.
# Populated on first auto_discover() and reused by subsequent
# PluginRegistry instances.
_discovery_cache: dict[str, type] | None = None


class PluginRegistry:
    """Central registry for managing domain plugins.

    Features:
    - Built-in plugin loading (direct imports; no entry-point scan)
    - Manual registration
    - Lazy initialization
    - Graceful degradation (missing plugins don't crash)
    - Discovery caching (avoids repeated plugin imports)
    """

    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: dict[str, BasePlugin] = {}
        self._auto_discovered = False
        self.logger = logging.getLogger("attune.plugins.registry")

    def auto_discover(self) -> None:
        """Load the built-in plugins via direct imports.

        The plugin set is the static ``_BUILTIN_PLUGINS`` table — both
        plugins ship in the attune-ai wheel, so there is nothing to
        scan. Loading stays best-effort (a broken plugin logs and is
        skipped, never crashes), and results are cached at module level
        so repeated PluginRegistry instances skip the imports.
        """
        global _discovery_cache

        if self._auto_discovered:
            return

        # One-time advisory scan for external dists still registering
        # the entry-point groups 16.0.0 collapsed (silent non-loading).
        from .stale_entry_points import warn_stale_entry_points

        warn_stale_entry_points()

        self.logger.info("Loading built-in plugins...")

        # Build or reuse the discovery cache
        if _discovery_cache is None:
            import importlib

            _discovery_cache = {}
            for name, module_path, class_name in _BUILTIN_PLUGINS:
                try:
                    module = importlib.import_module(module_path)
                    _discovery_cache[name] = getattr(module, class_name)
                except Exception as e:  # noqa: BLE001
                    # INTENTIONAL: built-in plugin load is best-effort
                    self.logger.warning(
                        f"Failed to load plugin '{name}': {e}",
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
        self.logger.info(f"Built-in plugin loading complete. {len(self._plugins)} plugins loaded.")

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

    Useful in tests or when plugin modules have changed at runtime
    (e.g. after installing a new plugin package).
    """
    global _discovery_cache, _global_registry
    _discovery_cache = None
    _global_registry = None
