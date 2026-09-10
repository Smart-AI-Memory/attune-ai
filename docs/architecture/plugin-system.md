---
description: Attune AI Plugin System — workflow- and MCP-centric extension model built on `BasePlugin`. Covers the plugin contract, registry, lifecycle, and the `register_mcp_tools()` hook used to extend the MCP server.
---

# Attune AI Plugin System

The plugin system manages bundled software and Redis workflows and MCP
tools through `BasePlugin` and a process-wide registry. Since 16.0.0,
auto-discovery imports those bundled plugins directly; third-party
`attune.plugins` entry points are no longer loaded. Application code can
still register a plugin explicitly in its own registry.

## Architecture overview

There are three moving parts:

1. **`BasePlugin`** (`src/attune/plugins/base.py`) — abstract base class.
   Each plugin subclasses it, declares metadata, and registers workflows
   and/or MCP tools.
2. **`PluginRegistry`** (`src/attune/plugins/registry.py`) — singleton
   that imports bundled plugins, instantiates them, and routes lookups
   by plugin name and workflow id.
3. **`AttuneMCPServer`** (`src/attune/mcp/server.py`) — during
   construction it iterates the registry and calls each plugin's
   `register_mcp_tools(self)` so plugins can contribute MCP tools to the
   live server.

Registered engine workflows subclass `attune.workflows.base.BaseWorkflow`.
The separate `attune.plugins.BaseWorkflow` analyzer is deprecated.

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
| `register_mcp_tools(server)` | During `AttuneMCPServer.__init__` for each loaded plugin | Add tool definitions to the live MCP server |
| `get_cli_commands()` | Not invoked from core today | Optional CLI subcommand descriptors (default `[]`) |

### Read-side helpers (provided)

`BasePlugin` also provides concrete helpers that subclasses generally do
not override:

- `get_workflow(workflow_id)` — returns the registered workflow class or
  `None`; triggers `initialize()` on first call.
- `list_workflows()` — returns the registered workflow ids.
- `get_workflow_info(workflow_id)` — reads engine class metadata without
  constructing it, using the plugin domain and defaulting `category` to
  `None` and `required_context` to `[]`. Legacy analyzers retain instance
  metadata extraction.

## `register_mcp_tools(server)` — the MCP extension hook

This is the seam plugins use to add MCP tools to the running server.

- **Signature**: `register_mcp_tools(self, server: Any) -> None`
- **Default**: no-op.
- **Caller**: `AttuneMCPServer._register_plugin_tools()` iterates
  `get_global_registry().list_plugins()` and calls
  `plugin.register_mcp_tools(self)` if the attribute exists.
- **When**: synchronously inside `AttuneMCPServer.__init__`, after the
  built-in tool/resource/prompt registries are populated.
- **`server` argument**: the live `AttuneMCPServer` instance. The
  base class type-annotates it as `Any` and documents it as
  `AttuneMCPServer`.
- **Failure mode**: the caller wraps each call in `try/except` and logs a
  warning on failure — plugins that raise will not crash MCP startup.

## Plugin lifecycle

1. **Discovery.** `PluginRegistry.auto_discover()` imports the static
   `_BUILTIN_PLUGINS` table. Results are cached in `_discovery_cache`.
2. **Instantiation.** The registry calls each bundled class constructor.
   Failures are logged and skipped.
3. **Validation.** `register_plugin()` calls `get_metadata()` and
   verifies that `name` and `domain` are non-empty.
4. **Activation.** The registry calls `plugin.on_activate()` after
   successful registration.
5. **Lazy initialize.** The first call to `get_plugin()`, `get_workflow()`,
   `list_workflows()`, or `get_workflow_info()` triggers `initialize()`,
   which runs `register_workflows()` once and caches the result in
   `self._workflows`. A `_initialized` flag prevents re-running.
6. **MCP wiring.** When `AttuneMCPServer` is constructed it calls
   `register_mcp_tools(self)` on every registered plugin.

There is no formal teardown hook. `clear_discovery_cache()` resets both
the module-level discovery cache and the global registry singleton —
intended for tests or post-install reloads, not normal shutdown.

## Registered workflow contract

New registered workflows subclass `attune.workflows.base.BaseWorkflow`.
Its public entry point is `execute()`; subclasses define stages, tier
mappings, and stage handlers as described in that class's docstring.

The separate `attune.plugins.BaseWorkflow` class is a deprecated analyzer
base. It emits `DeprecationWarning` when constructed. Existing analyzers
retain `analyze()`, `get_required_context()`, `validate_context()`, and
`contribute_patterns()`, but the engine never calls `analyze()`. Keep
plugin-internal analyzers under your own plugin's control, or migrate
executable workflows to the engine base. Renaming `analyze()` alone is
not a migration to the staged execution contract.

Registration still accepts legacy analyzers for compatibility. New plugin
types should use the engine class. Plugins without workflows return `{}`.

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

Auto-discovery is best-effort: a bundled plugin that fails to load logs
a warning and is skipped.

## Reference plugin: `attune_redis.RedisPlugin`

One of the bundled plugins is
[`attune_redis/plugin.py`](../../attune_redis/plugin.py) — which is the
clearest worked example of the contract.

Key shape:

```python
from attune.plugins import BasePlugin, PluginMetadata
from attune.workflows.base import BaseWorkflow


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
                "Install with: pip install attune-ai"
            )
```

The core registry loads this bundled class directly from its static table.

Notable features illustrated:

- `register_workflows()` returning `{}` is valid.
- `register_mcp_tools()` delegates to a separate module and tolerates
  missing optional dependencies via `ImportError` handling.
- `on_activate()` validates optional dependencies and emits a user-facing
  install hint if they are missing.

## Authoring a plugin (minimal)

1. **Subclass `BasePlugin`** in your package:

   ```python
   from attune.plugins import BasePlugin, PluginMetadata
   from attune.workflows.base import BaseWorkflow


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
   tools to add. The `server` argument is the live `AttuneMCPServer`.

3. **Register explicitly in application code.** Entry-point declarations
   do not cause loading in 16.x. This example creates a local registry;
   it does not install the plugin into another running process:

   ```python
   from attune.plugins import PluginRegistry

   registry = PluginRegistry()
   registry.register_plugin("my_domain", MyPlugin())
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
  pipeline base used by built-in and new registered workflows). Its
  stage implementation details are outside this plugin guide.
- Specific MCP tool definitions and the broader MCP server protocol.
- CLI command discovery details — `get_cli_commands()` is part of the
  plugin contract but is not invoked by the core today.
