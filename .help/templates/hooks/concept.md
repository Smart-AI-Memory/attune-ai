---
type: concept
feature: hooks
depth: concept
generated_at: 2026-05-04T02:43:00.657527+00:00
source_hash: ee7c91a1c6d86f5cfe8cb471894be8631647c9e853782d701bb219ccfe3deaf4
status: generated
---

# Hooks

## What

Hooks are event-driven automation that lets you run code at specific points in Attune AI's lifecycle. You can configure hooks to fire before tool execution, after session completion, or when specific conditions are met.

## Why

Hooks solve three integration challenges:

1. **Observability.** Monitor what Attune AI does without modifying core code. Log tool usage, track session patterns, or send metrics to external systems.
2. **Customization.** Inject custom logic at decision points. Filter tool results, modify context, or apply domain-specific rules before actions execute.
3. **Integration.** Connect Attune AI to external systems. Send webhooks to CI/CD pipelines, update project management tools, or trigger automated workflows.

## Core components

The hook system has five main pieces that work together:

- **`HookEvent`** — Lifecycle moments when hooks can fire (pre-tool, post-session, on-error)
- **`HookMatcher`** — Logic that decides whether a hook should run based on current context
- **`HookDefinition`** — What action to take when a hook fires (run script, call webhook, execute Python function)
- **`HookRule`** — A matcher paired with one or more actions, plus optional priority ordering
- **`HookRegistry`** — Central dispatcher that manages all hooks and executes them in sequence

## How hooks execute

When an event occurs, the registry finds matching hooks using this flow:

1. **Event triggers** — Something happens (tool starts, session ends, error occurs)
2. **Matcher evaluation** — Each hook's matcher checks the current context
3. **Priority sorting** — Matching hooks run in priority order (higher numbers first)
4. **Execution** — Actions run synchronously or asynchronously depending on configuration
5. **Result collection** — Return values are collected and logged for debugging

## Configuration options

You can define hooks in YAML configuration files or register them programmatically:

**YAML approach** — Static configuration loaded at startup:
```yaml
hooks:
  enabled: true
  log_executions: false
```

**Programmatic approach** — Dynamic registration with the HookRegistry:
```python
registry.register(
    event=HookEvent.PRE_TOOL,
    handler=my_function,
    matcher=custom_matcher,
    priority=100
)
```

## Integration interfaces

The hook system connects to the rest of Attune AI through these key methods:

- `HookRegistry.fire()` — Asynchronous hook execution from core system events
- `HookRegistry.fire_sync()` — Synchronous execution for blocking operations
- `HookConfig.get_hooks_for_event()` — Query which hooks apply to specific events
- `HookExecutor.execute()` — Low-level hook action execution with context injection
