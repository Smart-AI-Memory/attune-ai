---
type: architecture
name: hooks
tags: [hooks, events, automation, webhooks]
source: hooks
---

# Hooks architecture

## Purpose

The hooks subsystem intercepts Claude Code lifecycle events and dispatches configured actions — shell commands, webhooks, or Python callables — in response. It owns event matching, prioritized rule evaluation, execution (async and sync), and the execution log. It does **not** own the lifecycle events themselves (those come from the Claude Code host), nor does it own the business logic inside hook scripts; that lives in `scripts/`.

## Key classes

| Class | Responsibility | File |
|---|---|---|
| `HookEvent` | Enum of lifecycle event types that map to Claude Code hook points. | `hooks/config.py` |
| `HookType` | Enum of the action kinds a hook can perform (shell, webhook, Python callable, etc.). | `hooks/config.py` |
| `HookDefinition` | Declares a single hook action: its type, target, and parameters. | `hooks/config.py` |
| `HookMatcher` | Evaluates a context dict against a predicate to decide whether a rule applies. | `hooks/config.py` |
| `HookRule` | Pairs a `HookMatcher` with one or more `HookDefinition`s and a priority. | `hooks/config.py` |
| `HookConfig` | Holds the full set of `HookRule`s for a session; loads from and serializes to YAML. | `hooks/config.py` |
| `HookExecutor` | Runs a `HookDefinition` against a context dict and returns a result dict; async-native. | `hooks/executor.py` |
| `HookExecutorSync` | Synchronous wrapper around `HookExecutor` for call sites that cannot use `await`. | `hooks/executor.py` |
| `HookRegistry` | Owns registration, matching, dispatch, and the execution log; the single entry point for callers. | `hooks/registry.py` |

> **Design note:** `HookConfig` does three distinct things — acts as a data container, handles YAML serialization via `from_yaml`/`to_yaml`, and implements event-indexed lookup via `get_hooks_for_event`. If this class grows, splitting serialization into its own layer is the natural seam.

## Data flow

Hook firing follows this path through the subsystem:

```
Caller
  │
  ▼
HookRegistry.fire(event, context)
  │
  ├─► HookConfig.get_hooks_for_event(event)
  │       └─► returns list[HookRule] ordered by priority
  │
  ├─► HookMatcher.matches(context)   ← per rule; non-matching rules are dropped
  │
  ├─► HookExecutor.execute(hook, context)   ← per matched HookDefinition
  │       └─► returns dict[str, Any] result
  │
  ├─► execution log (internal)
  │
  └─► returns list[dict[str, Any]]   ← one entry per executed hook

Synchronous callers use HookRegistry.fire_sync(), which
delegates to HookExecutorSync rather than HookExecutor.
```

YAML configuration enters through `HookConfig.from_yaml()` and reaches `HookRegistry` via `HookRegistry.load_config()`. Programmatic registration bypasses YAML entirely through `HookRegistry.register()`.

## Design decisions

**Async executor with a synchronous wrapper, not two separate implementations.**
`HookExecutorSync` wraps `HookExecutor` rather than reimplementing execution. This keeps execution logic in one place while letting synchronous call sites (scripts that cannot use `async/await`) still dispatch hooks. The trade-off is a thin extra layer; the benefit is that bug fixes in `HookExecutor` apply to both paths automatically.

**Priority and matching are resolved in `HookRegistry`, not in `HookConfig`.**
`HookConfig.get_hooks_for_event` returns all rules for an event without filtering by context. `HookRegistry.get_matching_hooks` then applies `HookMatcher.matches` and priority ordering. This keeps `HookConfig` a pure data holder and concentrates dispatch policy in `HookRegistry`, where it can be tested independently of YAML loading.

**`HookRegistry.register()` returns a `handler_id` string.**
Programmatically registered handlers get an opaque ID that callers pass back to `unregister()`. This avoids requiring callers to hold a reference to the original callable just to remove it, which matters when lambdas or partials are registered.

## Extension points

- **Add a new event type:** Add a member to `HookEvent` in `hooks/config.py`. `HookConfig.get_hooks_for_event` and `HookRegistry.fire` both key off `HookEvent` values, so the new event is immediately dispatchable.
- **Add a new action type:** Add a member to `HookType` and handle it in `HookExecutor.execute`. No changes to `HookRegistry` or `HookConfig` are required.
- **Register a Python callable at runtime:** Call `HookRegistry.register(event, handler, description, matcher, priority)`. It returns a `handler_id` you can pass to `HookRegistry.unregister()` to remove it later.
- **Load hook rules from YAML:** Call `HookConfig.from_yaml(yaml_path)` to build a config object, then pass it to `HookRegistry.load_config(config)` or the `HookRegistry.__init__` constructor.
- **Add a custom matching predicate:** Subclass `HookMatcher` and override `matches(self, context: dict[str, Any]) -> bool`. Pass an instance to `HookConfig.add_hook` or `HookRegistry.register` via the `matcher` parameter.
- **Inspect execution history:** Call `HookRegistry.get_execution_log(limit, event_filter)` to retrieve past results, or `HookRegistry.get_stats()` for aggregate counts. Use `HookRegistry.clear_execution_log()` to reset between test runs.

For usage details, see the hooks reference documentation.
