---
name: hooks
source: content/features/hooks.md
tags:
- hooks
- webhooks
- events
- automation
type: faq
---

# Hooks FAQ

## What are hooks?

Hooks let you run custom logic at specific points in the Claude Code lifecycle. You define a `HookDefinition`, attach it to a `HookEvent` via a `HookRegistry` or `HookConfig`, and the system calls it whenever that event fires.

## When would I use hooks instead of calling my code directly?

Use hooks when you need your code to run automatically in response to lifecycle events — for example, recording telemetry after a tool runs, enforcing security rules before a bash command executes, or triggering a compaction summary before context is cleared. If you just need to call a function at a known point in your own code, hooks add unnecessary indirection.

## What's the difference between `HookExecutor` and `HookExecutorSync`?

`HookExecutor` runs hook actions and returns results asynchronously. `HookExecutorSync` is a synchronous wrapper around the same logic — use it when you're calling from a context that can't await, such as a CLI entry point or a synchronous event loop. Both accept a `python_handlers` dict that maps handler names to callables.

## How do I register a hook at runtime?

Call `HookRegistry.register(event, handler, ...)`. It returns a `handler_id` string you can pass to `HookRegistry.unregister(handler_id)` later if you need to remove it.

## How should a Python handler be written?

The registry calls handlers with the fired context **unpacked as keyword arguments** — write `def handler(**context): ...`, not `def handler(context): ...`. A positional `context` parameter raises `TypeError: got an unexpected keyword argument`. Read individual values inside with `context.get("tool_name")`, etc.

## How do I load hooks from a config file?

Use `HookConfig.from_yaml(yaml_path)` to load a config, then pass it to `HookRegistry.load_config(config)`. To save the current config back to disk, call `HookConfig.to_yaml(yaml_path)`.

## How do I fire a hook?

Call `HookRegistry.fire(event, context)` for async dispatch or `HookRegistry.fire_sync(event, context)` for synchronous dispatch. Both return a list of result dicts, one per executed hook.

## How do I check which hooks will run for a given event?

Call `HookRegistry.get_matching_hooks(event, context)`. It returns a list of `(HookRule, HookDefinition)` tuples — the same set the registry would execute if you called `fire`.

## What controls whether a hook fires for a particular context?

A `HookMatcher`. When you register a hook, you can supply a `HookMatcher` whose `matches(context)` method returns `True` or `False`. Hooks without a matcher fire on every matching event. Priority (an integer you set on `add_hook` or `register`) controls the order when multiple hooks match.

## How do I see what has already run?

Call `HookRegistry.get_execution_log(limit, event_filter)` to retrieve recent execution records. Use `HookRegistry.get_stats()` for aggregate counts, and `HookRegistry.clear_execution_log()` to reset the log.

## Where are the source files?

- `src/attune/hooks/**`

**Tags:** `hooks`, `webhooks`, `events`, `automation`
