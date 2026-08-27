# Upgrading to 16.0.0

16.0.0 is the destructive half of the harness-lite architecture
ruling (`docs/specs/release-16-manifest/`): it deletes dead
framework-era modules, executes every deprecation the 15.x line
warned about, and collapses the ceremony entry-point seams. **If you
use attune-ai through the CLI, the plugin, or the MCP tools, you
upgrade with no code changes.** The removals bite only Python code
that imported the deleted modules or registered entry points. The
constructive half — the new extension system — ships in 16.x; nothing
in this release adds a new way to extend attune.

## Do you need to change anything?

Run this against your codebase:

```bash
grep -rnE "from attune\.(discovery|templates|template_engine|template_defs_\w+|pattern_cache|cache_stats|cache_monitor|vscode_bridge|coordination|persistence|state_manager|redis_memory\w*) import|attune\.config import.*(AgentWorkflowConfig|WorkflowMode)|WorkflowConfig" . --include='*.py'
```

No hits → you are done. Hits → the table below.

## Removed modules

| Removed | Replacement |
|---|---|
| `attune.discovery` | none (dead progressive-discovery engine; its tips live in the generated help) |
| `attune.pattern_cache`, `attune.cache_stats`, `attune.cache_monitor` | none (dead cache-monitor cluster) |
| `attune.vscode_bridge` | none (Empathy-era extension bridge) |
| `attune.template_engine`, `attune.template_defs_basic`, `attune.template_defs_web`, `attune.templates` | none (`cmd_new` was never wired to the CLI) |
| `attune.coordination` | removed in 6.8.0; the shim is now gone too |
| `attune.redis_memory`, `attune.redis_memory_storage`, `attune.redis_memory_coordination`, `attune.redis_memory_patterns` | `attune_redis.AMSMemoryBackend` (bundled in the wheel) — see [redis-plugin-migration.md](redis-plugin-migration.md). *Note: earlier docstrings said these were "retained with no planned removal"; the 16.0.0 architecture ruling superseded that.* |
| `attune.persistence` (facade) | `attune.pattern_persistence.PatternPersistence`, `attune.metrics_collector.MetricsCollector` — both still exported from `attune` top level |
| `attune.state_manager` (`StateManager`) | none (deprecated since 9.0.0) |

## Removed aliases (each warned through 15.x naming this release)

| Old name | Use instead |
|---|---|
| `attune.config.AgentWorkflowConfig` | none — it was an unconsumed twin; `attune.workflows.config.WorkflowConfig` is the live workflows type |
| `attune.config.WorkflowMode` | none (only consumer was the twin) |
| `attune.config.sections.WorkflowConfig` | `attune.config.sections.WorkflowsConfig` |
| `attune.agent_factory.WorkflowConfig` (and `.base.WorkflowConfig`) | `attune.agent_factory.AgentGraphConfig` |

## Collapsed entry-point groups

The `attune.plugins` and `attune.wizards` entry-point groups are no
longer read; the dead `attune.workflows` reading path is deleted. The
bundled plugins and built-in wizards load directly. If you registered
an external wizard or plugin via these groups, that path is gone —
the 16.x extension system is the successor.

Because an unread entry point fails by *silent non-loading* (nothing
in your own code errors), attune detects this at startup: if any
installed package other than attune-ai still declares entries in
these groups, the first plugin/wizard registry load logs one warning
per package, naming it and pointing here. The scan runs once per
process and is fail-open — a metadata error never affects startup.
Until you migrate, Python wizard classes can be re-registered at
runtime with `attune.wizards.registry.register_wizard()`, and plugin
instances with `PluginRegistry.register_plugin()`.

Two things still work unchanged:

- **`attune.memory_backends`** — the one entry-point seam kept
  (custom memory backends keep working as before).
- **YAML wizards** in `.attune/wizards/*.yaml` — the config-driven
  wizard path is data, not a Python seam, and is untouched.

The `BasePlugin` / `register_mcp_tools()` class contract is also
unchanged.
