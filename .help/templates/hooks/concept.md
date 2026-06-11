---
type: concept
name: hooks-concept
feature: hooks
depth: concept
generated_at: 2026-06-11T04:49:42.136978+00:00
source_hash: c616d1d3b693f3ea1e8811ca9fcf005cdcb50eb831d6a67ee7f5dd74236f44dd
status: generated
scaffold_hash: 5f756279fb78a65834c6236804bbd23166bbbb2aec951ee6f6347f0419c40255
---

# Hooks

The hooks system lets you attach actions to Claude Code lifecycle events so Attune AI can automatically run logic—security checks, telemetry, session evaluation, and compaction—at precise moments during an agent session.

## Mental model

Hooks work as a three-layer pipeline:

1. **Declaration** — A `HookDefinition` describes what action to run; a `HookMatcher` decides when to run it by evaluating `matches(context)` against the current runtime context dict. Pairing them produces a `HookRule`.
2. **Configuration** — A `HookConfig` groups rules by `HookEvent`. Build one programmatically with `add_hook()`, or load one from a YAML file with `HookConfig.from_yaml()`. The `priority` parameter on `add_hook()` controls the order in which rules fire within the same event.
3. **Dispatch** — `HookRegistry` is the runtime hub. Call `fire(event, context)` or `fire_sync(event, context)`, and the registry evaluates each `HookMatcher` against the context dict, passes matched `HookDefinition`s to `HookExecutor`, and accumulates results in an execution log.

The context dict flows through every layer — from the `HookMatcher.matches()` check to the `HookExecutor.execute()` return value — so hooks have access to the same runtime information at every stage.

## Event lifecycle

`HookEvent` values correspond to Claude Code lifecycle points. Because hooks fire at these specific moments, you can run security validation before a tool executes or trigger session evaluation after it completes, without modifying agent core code.

## Configuration layer

| Class | Role |
|-------|------|
| `HookEvent` | Identifies the lifecycle point where a rule applies |
| `HookType` | Specifies the kind of action a `HookDefinition` performs |
| `HookDefinition` | Describes a single action to execute |
| `HookMatcher` | Evaluates `matches(context)` to decide whether a rule fires |
| `HookRule` | Pairs a `HookMatcher` with one or more `HookDefinition`s |
| `HookConfig` | Holds all rules; serializes to and from YAML |

`HookConfig.from_yaml(yaml_path)` reads a hook configuration file and returns a ready-to-use `HookConfig`. `to_yaml(yaml_path)` writes the current configuration back to disk. `get_hooks_for_event(event)` returns the list of `HookRule`s registered for a given event.

## Registry and dispatch

`HookRegistry` is the object you interact with at runtime.

- **Loading from config**: Pass a `HookConfig` to `HookRegistry(config)` at construction, or call `load_config(config)` to swap configuration later.
- **Registering Python handlers directly**: `register(event, handler, description, matcher, priority)` wraps a callable in a rule and returns a `handler_id` string. Pass that string to `unregister(handler_id)` to remove the handler.
- **Firing events**: `fire(event, context)` is asynchronous; `fire_sync(event, context)` is synchronous. Both return a list of result dicts—one per matched hook.
- **Inspecting results**: `get_execution_log(limit, event_filter)` returns recent execution records. `get_stats()` returns aggregate counters across all events. `clear_execution_log()` resets the log.

## Execution

`HookExecutor` runs a `HookDefinition` against a context dict and returns a result dict. Construct it with a `python_handlers` mapping to let the executor resolve handler names to Python callables—the same mapping that `HookRegistry` uses when you call `register()`. `HookExecutorSync` provides the same interface for synchronous call sites.

## Built-in scripts

The `scripts` package ships Python callables designed for use as hook handlers. You can register them with `HookRegistry.register()` or reference them from a YAML configuration:

| Handler | Purpose |
|---------|---------|
| `run_evaluate_session` | Evaluates a completed session for learning potential |
| `run_pre_compact` | Generates a compaction summary before context is compressed |
| `suggest_compact` | Recommends compaction when token usage crosses a threshold |
| `check_init` / `handle_init_response` | Detects whether Attune AI is initialized and prompts the user |
| `validate_bash_command` / `validate_file_path` | Blocks unsafe shell commands and file paths |
| `record_telemetry` | Records session telemetry |
| `apply_learned_patterns` | Generates context injection from learned patterns |

Every script in this package guards against double-execution using `is_sdk_subprocess()`. When that function returns `True`, `exit_if_sdk_subprocess()` exits silently—preventing a hook from running a second time inside an SDK-spawned `claude` subprocess.

## Integration surface

The public API exported from `hooks.__init__` is `HookConfig`, `HookDefinition`, `HookEvent`, `HookExecutor`, and `HookRegistry`. Everything else—`HookType`, `HookMatcher`, `HookRule`, the executor internals—is consumed internally by those five classes.

At the project level, the `hooks` section of the Attune AI YAML configuration controls whether the system is active (`enabled: true`) and whether individual executions are logged to disk (`log_executions`). `HookConfig.from_yaml()` reads this section when loading the project file.
