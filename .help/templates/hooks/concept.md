---
type: concept
name: hooks-concept
feature: hooks
depth: concept
generated_at: 2026-06-02T10:56:02.683749+00:00
source_hash: 4690cd16c282bccaee1ffc3de0ea189b194fa0d71b87cec08e2f3675e136bbb9
status: generated
---

# Hooks

The hooks system lets you attach custom logic to Claude Code lifecycle events — running scripts, calling handlers, or enforcing rules automatically at defined points in a session.

## How the pieces fit together

A hook starts as a `HookDefinition` — the action to run — paired with an optional `HookMatcher` that decides whether the hook fires for a given context. Together they form a `HookRule`. Rules are grouped by `HookEvent` inside a `HookConfig`, which you can load from or save to a YAML file using `HookConfig.from_yaml()` and `HookConfig.to_yaml()`.

At runtime, `HookRegistry` is the central coordinator. You register handlers against specific events using `HookRegistry.register()`, which returns a handler ID you can later pass to `HookRegistry.unregister()` if you need to remove it. When an event fires, the registry calls `HookRegistry.get_matching_hooks()` to filter rules by context, then dispatches to `HookExecutor` (async) or `HookExecutorSync` for environments that require synchronous execution.

```
HookConfig (YAML or code)
    └── HookRule (per HookEvent)
            ├── HookMatcher  →  matches(context) → bool
            └── HookDefinition  →  the action

HookRegistry
    ├── load_config(HookConfig)   ← bulk load from YAML
    ├── register(event, handler)  ← programmatic registration
    ├── fire(event, context)      ← async dispatch
    └── fire_sync(event, context) ← sync dispatch
            └── HookExecutor / HookExecutorSync
```

## Event types and lifecycle

`HookEvent` values correspond directly to Claude Code lifecycle moments — for example, events that fire before or after a tool runs. Each `HookEvent` carries a `context` dictionary that `HookMatcher.matches()` inspects to decide whether a given rule applies. This lets you write targeted rules, such as running `scripts.security_guard` only when a bash command is about to execute, or triggering `scripts.pre_compact` only when context compaction begins.

## Built-in scripts as hook handlers

Several scripts in the codebase are designed to be registered as hook handlers:

| Script | Typical trigger |
|---|---|
| `scripts.security_guard.main` | Pre-tool event for bash or file operations |
| `scripts.pre_compact.run_pre_compact` | Before context compaction |
| `scripts.evaluate_session.run_evaluate_session` | End-of-session evaluation |
| `scripts.suggest_compact.main` | Periodic compaction prompts |
| `scripts.telemetry_hook.record_telemetry` | Any event where usage data is needed |
| `scripts.worktree_path_guard.main` | File path validation events |

You supply these as Python callables when constructing `HookExecutor(python_handlers={...})`.

## Priority and matching

When multiple rules match the same event, `HookRegistry` respects the `priority` value set during `add_hook()` or `register()`. Higher-priority rules run first. If no `HookMatcher` is provided, the rule matches every context for that event.

## Observability

`HookRegistry` keeps an execution log you can query with `get_execution_log(limit, event_filter)` and aggregate metrics with `get_stats()`. Call `clear_execution_log()` to reset it between test runs or sessions. Logging is controlled by the `hooks.log_executions` flag in the project configuration YAML.

## When hooks matter

Use the hook system when you need to:

- **Enforce invariants automatically** — for example, blocking dangerous bash commands via `security_guard` without requiring manual review on every tool call.
- **React to session lifecycle events** — capturing learning summaries or compaction state at the right moment rather than polling.
- **Compose conditional behavior** — using `HookMatcher` to apply different logic depending on what the context contains, without branching inside your main code.
