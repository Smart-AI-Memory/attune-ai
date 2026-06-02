---
type: tutorial
name: hooks
tags: [hooks, events, registry, executor, automation]
source: developer-guidance
---

# Tutorial: Hooks

You'll finish this tutorial with a running Python script that registers a custom handler, fires it against a lifecycle event, and prints an execution log — giving you a concrete mental model of how `HookRegistry`, `HookConfig`, and `HookExecutor` fit together.

## Prerequisites

- Python 3.10 or newer
- The `hooks` package installed in your environment
- Basic familiarity with Python callables and `dict`

## What you will build

A self-contained script that:

1. Creates a `HookConfig` and adds a hook for a lifecycle event
2. Loads that config into a `HookRegistry`
3. Registers an additional in-process Python handler
4. Fires the event synchronously and inspects the results
5. Prints a summary from `get_stats()`

When the script runs successfully you'll see the handler's output printed to the terminal alongside a stats summary — proof that the full dispatch cycle worked.

---

## Step 1 — Import the public API

The `hooks` package exposes everything you need from its top-level module. Import those names now so the rest of the tutorial stays focused on concepts, not paths.

```python
from hooks import HookConfig, HookDefinition, HookEvent, HookExecutor, HookRegistry
```

Confirm the import worked by running the file. You should see no output and no errors — a clean module load.

---

## Step 2 — Define a lifecycle event and a hook

`HookEvent` represents the Claude Code lifecycle points where hooks can fire. You pick one event, then describe what should happen when it fires by constructing a `HookDefinition`.

The definition is intentionally separate from the event — the same definition can be reused across multiple events, which is why `HookConfig.add_hook` accepts them as distinct arguments.

```python
# Choose the event you want to hook into.
# HookEvent is an enum; pick the value that matches your lifecycle point.
event = HookEvent.PRE_TOOL   # replace with the value appropriate for your project

# Describe the action to run when this event fires.
hook_def = HookDefinition(
    name="log_pre_tool",
    description="Prints a message before any tool runs",
)
```

You'll know this step is correct when Python constructs both objects without raising a `TypeError` or `ValueError`.

---

## Step 3 — Build a `HookConfig` and register the hook

`HookConfig` is the serialisable container for all your hook rules. You build one in memory here; later you'll see how to save and reload it from YAML.

Passing `priority=10` means this rule runs before lower-priority rules on the same event — a detail that matters once you have more than one handler.

```python
config = HookConfig()
config.add_hook(event=event, hook=hook_def, priority=10)

# Verify the rule was stored.
rules = config.get_hooks_for_event(event)
print(f"Rules registered for {event}: {len(rules)}")  # expect: 1
```

Run the script. The output should read `Rules registered for …: 1`.

---

## Step 4 — Persist and reload the config (optional but instructive)

`HookConfig.to_yaml` and `HookConfig.from_yaml` exist so your hook rules can live in version control alongside your project. Walking through a round-trip here shows you that the in-memory object and the file representation are equivalent.

```python
config.to_yaml("hooks_config.yaml")

reloaded = HookConfig.from_yaml("hooks_config.yaml")
reloaded_rules = reloaded.get_hooks_for_event(event)
print(f"Rules after reload: {len(reloaded_rules)}")  # expect: 1
```

After running, open `hooks_config.yaml` in your editor and confirm the rule you defined in Step 3 is present in the file.

---

## Step 5 — Create a registry and attach the config

`HookRegistry` is the dispatch engine. It consumes a `HookConfig` and adds runtime Python handlers on top. Loading the config here wires up the YAML-defined rules before you register any in-process callables.

```python
registry = HookRegistry()
registry.load_config(reloaded)  # or `config` if you skipped Step 4
```

No visible output here — the registry is now primed with your rule.

---

## Step 6 — Register an in-process Python handler

`HookRegistry.register` lets you attach a plain Python callable directly, without going through a `HookDefinition`. This is the path you'll use for lightweight handlers that don't need to be serialised.

The return value is a `handler_id` string you can use later to remove the handler with `unregister`.

```python
def my_handler(context: dict) -> dict:
    print(f"[my_handler] fired with context keys: {list(context.keys())}")
    return {"status": "ok", "handler": "my_handler"}

handler_id = registry.register(
    event=event,
    handler=my_handler,
    description="Tutorial demo handler",
    priority=5,
)
print(f"Registered handler id: {handler_id}")
```

Run the script. You should see the handler ID printed — something like `handler_<uuid>`.

---

## Step 7 — Fire the event and inspect results

`fire_sync` dispatches the event to every matching rule and handler in priority order and returns a list of result dicts — one per handler that ran. Using the synchronous variant here keeps the tutorial to a single execution model; `fire` works identically but is awaitable.

```python
context = {"tool_name": "bash", "session_id": "tutorial-001"}
results = registry.fire_sync(event=event, context=context)

for i, result in enumerate(results):
    print(f"Result {i}: {result}")
```

You should see `[my_handler] fired with context keys: ['tool_name', 'session_id']` printed by the handler, followed by the result dict on the next line.

---

## Step 8 — Read the execution log and stats

`get_execution_log` gives you a chronological record of every dispatch since the registry was created. `get_stats` gives you aggregate counts. Together they're how you confirm the system did what you expected — and the foundation for observability in production.

```python
log = registry.get_execution_log(limit=10, event_filter=event)
print(f"Log entries: {len(log)}")

stats = registry.get_stats()
print(f"Stats: {stats}")
```

You should see one log entry (from Step 7) and a stats dict that reflects at least one successful execution.

---

## Complete script

```python
from hooks import HookConfig, HookDefinition, HookEvent, HookExecutor, HookRegistry

# Steps 2–3: define and configure
event = HookEvent.PRE_TOOL
hook_def = HookDefinition(name="log_pre_tool", description="Prints a message before any tool runs")

config = HookConfig()
config.add_hook(event=event, hook=hook_def, priority=10)
print(f"Rules registered for {event}: {len(config.get_hooks_for_event(event))}")

# Step 4: round-trip through YAML
config.to_yaml("hooks_config.yaml")
reloaded = HookConfig.from_yaml("hooks_config.yaml")
print(f"Rules after reload: {len(reloaded.get_hooks_for_event(event))}")

# Steps 5–6: registry and in-process handler
registry = HookRegistry()
registry.load_config(reloaded)

def my_handler(context: dict) -> dict:
    print(f"[my_handler] fired with context keys: {list(context.keys())}")
    return {"status": "ok", "handler": "my_handler"}

handler_id = registry.register(event=event, handler=my_handler, description="Tutorial demo handler", priority=5)
print(f"Registered handler id: {handler_id}")

# Step 7: fire
context = {"tool_name": "bash", "session_id": "tutorial-001"}
results = registry.fire_sync(event=event, context=context)
for i, result in enumerate(results):
    print(f"Result {i}: {result}")

# Step 8: log and stats
log = registry.get_execution_log(limit=10, event_filter=event)
print(f"Log entries: {len(log)}")
print(f"Stats: {registry.get_stats()}")
```

---

## What you learned

- **Step 2** introduced `HookEvent` and `HookDefinition` — the two primitives that separate *when* a hook fires from *what* it does.
- **Step 3** showed how `HookConfig.add_hook` assembles rules with optional priority ordering, and how `get_hooks_for_event` lets you verify the result.
- **Step 4** demonstrated the YAML round-trip (`to_yaml` / `from_yaml`), so your hook configuration can live in version control.
- **Step 5–6** showed that `HookRegistry` is the live dispatch engine: it accepts a `HookConfig` for serialisable rules and `register` for in-process callables, returning a `handler_id` you can use to remove a handler later.
- **Step 7** proved the full dispatch cycle works: `fire_sync` called your handler in priority order and returned structured results.
- **Step 8** showed that `get_execution_log` and `get_stats` give you visibility into every dispatch — the observability layer you'll rely on when debugging hook behaviour in a real project.

## Next step

To go deeper on matchers and conditional dispatch — controlling which hooks fire based on runtime context — read the `HookMatcher` reference, which covers the `matches(context)` contract and how matchers compose with `HookConfig.add_hook`.

## Unresolved references

> Auto-generated by attune-author fact-check. Review and either
> fix the source code, fix this doc, or add an override.

| Location | Severity | Issue |
|---|---|---|
| Line 36 (code fence) | error | `from hooks import …` — module not importable |
| Line 53 (python fence) | error | Name "HookEvent" is not defined  [name-defined] |
| Line 56 (python fence) | error | Name "HookDefinition" is not defined  [name-defined] |
| Line 73 (python fence) | error | Name "HookConfig" is not defined  [name-defined] |
| Line 74 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 74 (python fence) | error | Name "hook_def" is not defined  [name-defined] |
| Line 77 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 78 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 90 (python fence) | error | Name "config" is not defined  [name-defined] |
| Line 92 (python fence) | error | Name "HookConfig" is not defined  [name-defined] |
| Line 93 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 106 (python fence) | error | Name "HookRegistry" is not defined  [name-defined] |
| Line 107 (python fence) | error | Name "reloaded" is not defined  [name-defined] |
| Line 121 (python fence) | error | Missing type parameters for generic type "dict"  [type-arg] |
| Line 125 (python fence) | error | Name "registry" is not defined  [name-defined] |
| Line 126 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 144 (python fence) | error | Name "registry" is not defined  [name-defined] |
| Line 144 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 159 (python fence) | error | Name "registry" is not defined  [name-defined] |
| Line 159 (python fence) | error | Name "event" is not defined  [name-defined] |
| Line 162 (python fence) | error | Name "registry" is not defined  [name-defined] |
| Line 192 (python fence) | error | Missing type parameters for generic type "dict"  [type-arg] |
