---
description: Attune AI Plugin System — workflow- and MCP-centric extension model built on `BasePlugin`. Covers the plugin contract, registry, lifecycle, and the `register_mcp_tools()` hook used to extend the MCP server.
---

# Attune AI Plugin System

The plugin system lets external packages extend Attune with new workflows
and new MCP tools without modifying the core. It is built around a single
abstract class — `BasePlugin` — discovered through Python entry points and
managed by a process-wide registry.

This document describes the actual surface in `src/attune/plugins/`.
Every concrete claim below is verified against source in
`src/attune/plugins/`.

## Architecture overview

There are three moving parts:

1. **`BasePlugin`** (`src/attune/plugins/base.py`) — abstract base class.
   Each plugin subclasses it, declares metadata, and registers workflows
   and/or MCP tools.
2. **`PluginRegistry`** (`src/attune/plugins/registry.py`) — singleton
   that discovers installed plugins via the `attune.plugins` entry-point
   group, instantiates them, and routes lookups by plugin name and
   workflow id.
3. **`EmpathyMCPServer`** (`src/attune/mcp/server.py`) — during
   construction it iterates the registry and calls each plugin's
   `register_mcp_tools(self)` so plugins can contribute MCP tools to the
   live server.

Workflows in this context are subclasses of the plugin-system
`BaseWorkflow` (in `src/attune/plugins/base.py`), not the larger
multi-model-pipeline `BaseWorkflow` in `src/attune/workflows/base.py`.
The two share a name but are independent classes.

## Public exports

`attune.plugins` re-exports:

- `BasePlugin`
- `BaseWorkflow`
- `PluginMetadata`
- `PluginRegistry`
- `PluginError`, `PluginLoadError`, `PluginValidationError`
- `get_global_registry`
- `clear_discovery_cache`

## The `BasePlugin` contract

`BasePlugin` is an `ABC` with two abstract methods that every subclass
must implement, plus several optional hooks the framework will call if
overridden.

### Required (abstract) methods

| Method | Returns | Purpose |
|--------|---------|---------|
| `get_metadata()` | `PluginMetadata` | Static metadata about the plugin |
| `register_workflows()` | `dict[str, type[BaseWorkflow]]` | Map workflow id → workflow class |

`PluginMetadata` is a dataclass with fields:

- `name: str`
- `version: str`
- `domain: str`
- `description: str`
- `author: str`
- `license: str`
- `requires_core_version: str`
- `dependencies: list[str] | None = None`

Both `name` and `domain` are validated by the registry on registration —
empty values raise `PluginValidationError`.

### Optional hooks

The base class provides default no-op implementations for these; override
to extend behaviour:

| Method | When called | Purpose |
|--------|-------------|---------|
| `register_patterns()` | Not called by core today | Optional pattern library contributions (default `{}`) |
| `initialize()` | First time a workflow is requested (or explicitly) | Lazy setup; default invokes `register_workflows()` and caches the result |
| `on_activate()` | After the plugin is registered and `initialize()` succeeds | Post-registration setup (e.g. service connections) |
| `register_mcp_tools(server)` | During `EmpathyMCPServer.__init__` for each loaded plugin | Add tool definitions to the live MCP server |
| `get_cli_commands()` | Not invoked from core today | Optional CLI subcommand descriptors (default `[]`) |

### Read-side helpers (provided)

`BasePlugin` also provides concrete helpers that subclasses generally do
not override:

- `get_workflow(workflow_id)` — returns the registered workflow class or
  `None`; triggers `initialize()` on first call.
- `list_workflows()` — returns the registered workflow ids.
- `get_workflow_info(workflow_id)` — instantiates the workflow class
  briefly to surface `name`, `domain`, `empathy_level`, `category`, and
  `required_context`.

## `register_mcp_tools(server)` — the MCP extension hook

This is the seam plugins use to add MCP tools to the running server.

- **Signature**: `register_mcp_tools(self, server: Any) -> None`
- **Default**: no-op.
- **Caller**: `EmpathyMCPServer._register_plugin_tools()` iterates
  `get_global_registry().list_plugins()` and calls
  `plugin.register_mcp_tools(self)` if the attribute exists.
- **When**: synchronously inside `EmpathyMCPServer.__init__`, after the
  built-in tool/resource/prompt registries are populated.
- **`server` argument**: the live `EmpathyMCPServer` instance. The
  base class type-annotates it as `Any` and documents it as
  `EmpathyMCPServer`.
- **Failure mode**: the caller wraps each call in `try/except` and logs a
  warning on failure — plugins that raise will not crash MCP startup.

## Plugin lifecycle

1. **Discovery.** `PluginRegistry.auto_discover()` scans the
   `attune.plugins` entry-point group (and the legacy
   `attune_framework.plugins` group, kept for backward compatibility and
   slated for removal in v3.0.0). Discovery results are cached in a
   module-level `_discovery_cache` so subsequent registries reuse them.
2. **Instantiation.** For each discovered entry point, the registry
   calls the class constructor. Failures are logged but do not abort
   discovery (graceful degradation).
3. **Validation.** `register_plugin()` calls `get_metadata()` and
   verifies that `name` and `domain` are non-empty.
4. **Activation.** The registry calls `plugin.on_activate()` after
   successful registration.
5. **Lazy initialize.** The first call to `get_plugin()`, `get_workflow()`,
   `list_workflows()`, or `get_workflow_info()` triggers `initialize()`,
   which runs `register_workflows()` once and caches the result in
   `self._workflows`. A `_initialized` flag prevents re-running.
6. **MCP wiring.** When `EmpathyMCPServer` is constructed it calls
   `register_mcp_tools(self)` on every registered plugin.

There is no formal teardown hook. `clear_discovery_cache()` resets both
the module-level discovery cache and the global registry singleton —
intended for tests or post-install reloads, not normal shutdown.

## The plugin-side `BaseWorkflow` contract

The `BaseWorkflow` returned from `register_workflows()` is the abstract
class defined in `src/attune/plugins/base.py` (not the pipeline class in
`src/attune/workflows/base.py`).

It is an `ABC` initialised with `(name, domain, empathy_level, category=None)`
and requires subclasses to implement:

- `async analyze(context: dict[str, Any]) -> dict[str, Any]` — main entry
  point. Expected return keys include `issues`, `predictions`,
  `recommendations`, `patterns`, `confidence`, `workflow`,
  `empathy_level`, `timestamp` (per the docstring contract).
- `get_required_context() -> list[str]` — declares the context keys
  `analyze()` requires.

Helpers provided: `validate_context()`, `get_empathy_level()`,
`contribute_patterns()`.

Plugins are not required to ship workflows. `register_workflows()` may
return `{}` — see the reference plugin below.

## The `PluginRegistry`

Singleton-style registry. Public surface used by callers:

- `get_global_registry()` — module-level accessor; lazily constructs the
  registry and runs `auto_discover()` exactly once.
- `register_plugin(name, plugin)` — manual registration (validates
  metadata).
- `get_plugin(name) -> BasePlugin | None`
- `list_plugins() -> list[str]`
- `list_all_workflows() -> dict[str, list[str]]`
- `get_workflow(plugin_name, workflow_id)`
- `get_workflow_info(plugin_name, workflow_id)`
- `find_workflows_by_level(empathy_level)`
- `find_workflows_by_domain(domain)`
- `get_statistics()` — counts of plugins and workflows, plus a per-level
  breakdown for levels 1–5.
- `clear_discovery_cache()` — resets both the discovery cache and the
  global registry instance.

Auto-discovery is best-effort: an entry point that fails to load logs a
warning and is skipped.

## Reference plugin: `attune_redis.RedisPlugin`

The repository ships one in-tree reference plugin —
[`attune_redis/plugin.py`](../../attune_redis/plugin.py) — which is the
clearest worked example of the contract.

Key shape:

```python
from attune.plugins import BasePlugin, BaseWorkflow, PluginMetadata


class RedisPlugin(BasePlugin):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Attune Redis",
            version="0.1.0",
            domain="redis",
            description="Redis Agent Memory Server integration. ...",
            author="Smart AI Memory, LLC",
            license="Apache-2.0",
            requires_core_version="3.5.0",
            dependencies=[
                "agent-memory-client>=0.14.0",
                "redis>=5.0.0",
            ],
        )

    def register_workflows(self) -> dict[str, type[BaseWorkflow]]:
        return {}  # Workflows added in a later phase

    def register_mcp_tools(self, server: object) -> None:
        try:
            from attune_redis.mcp_tools import register_tools
            register_tools(server)
        except ImportError:
            logger.debug("attune-redis: MCP tools not registered (missing deps)")
        except Exception as e:  # noqa: BLE001
            logger.warning("attune-redis: MCP tool registration failed: %s", e)

    def on_activate(self) -> None:
        try:
            import agent_memory_client  # noqa: F401
        except ImportError:
            logger.warning(
                "attune-redis: agent-memory-client not installed. "
                "Install with: pip install attune-ai
            )
```

And the entry point in `attune_redis/pyproject.toml`:

```toml
[project.entry-points."attune.plugins"]
redis = "attune_redis.plugin:RedisPlugin"
```

Notable features illustrated:

- `register_workflows()` returning `{}` is valid.
- `register_mcp_tools()` delegates to a separate module and tolerates
  missing optional dependencies via `ImportError` handling.
- `on_activate()` validates optional dependencies and emits a user-facing
  install hint if they are missing.

## Authoring a plugin (minimal)

1. **Subclass `BasePlugin`** in your package:

   ```python
   from attune.plugins import BasePlugin, BaseWorkflow, PluginMetadata


   class MyPlugin(BasePlugin):
       def get_metadata(self) -> PluginMetadata:
           return PluginMetadata(
               name="My Plugin",
               version="0.1.0",
               domain="my_domain",
               description="What this plugin does.",
               author="You",
               license="Apache-2.0",
               requires_core_version="3.5.0",
           )

       def register_workflows(self) -> dict[str, type[BaseWorkflow]]:
           return {}
   ```

2. **(Optional) override `register_mcp_tools(server)`** if you have MCP
   tools to add. The `server` argument is the live `EmpathyMCPServer`.

3. **Declare the entry point** in your `pyproject.toml`:

   ```toml
   [project.entry-points."attune.plugins"]
   my_domain = "my_package.plugin:MyPlugin"
   ```

4. **Install your package** in the same environment as `attune-ai`.
   `get_global_registry()` will discover it on next process start.

5. **Verify discovery**:

   ```python
   from attune.plugins import get_global_registry

   registry = get_global_registry()
   assert "my_domain" in registry.list_plugins()
   ```

## Error types

Defined in `src/attune/plugins/base.py`:

- `PluginError` — base class for plugin-related errors.
- `PluginLoadError` — raised when a plugin fails to load.
- `PluginValidationError` — raised when a plugin fails validation
  (e.g. missing `name` or `domain` in metadata).

## Out of scope for this document

These are intentionally not covered here — they live in their own docs
or are not part of the plugin-system surface:

- The `BaseWorkflow` in `src/attune/workflows/base.py` (the multi-model
  pipeline base used by built-in workflows like `code-review`,
  `security-audit`, `bug-predict`). It is unrelated to the
  plugin-system `BaseWorkflow` despite the shared name.
- Specific MCP tool definitions and the broader MCP server protocol.
- CLI command discovery details — `get_cli_commands()` is part of the
  plugin contract but is not invoked by the core today.
