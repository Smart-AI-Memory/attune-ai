---
type: warning
name: orchestration-warning
feature: orchestration
depth: warning
generated_at: 2026-05-16T06:14:24.025029+00:00
source_hash: ea07a9fe2c597e0620947bda28929f02936ea17148cbff01940256571429e078
status: generated
---

# Orchestration cautions

## What to watch for

The orchestration module composes `BaseWorkflow` instances using named strategies, a shared workflow registry, and a template registry. Mistakes in any of these three areas tend to surface late — often only when a pipeline runs under production conditions — because each component works correctly in isolation but interacts unexpectedly at composition time.

## Risk areas

### `get_strategy()` raises on unregistered names at call time, not at definition time

`get_strategy(strategy_name)` raises `ValueError: 'Unknown strategy: {...}. Available: {...}'` if the name has not been registered. Because strategy selection often happens inside a pipeline definition rather than at import time, this error appears only when the pipeline executes. Register all custom strategies with `register_strategy()` before any pipeline that depends on them runs — not after.

### `DelegationChainStrategy` silently caps delegation depth

`DelegationChainStrategy` defaults to `max_depth=3`. If your agent graph requires deeper hierarchical delegation, tasks at depth 4 and beyond are cut off without an exception. Pass an explicit `max_depth` when constructing the strategy whenever your delegation graph exceeds three levels.

### `PromptCachedSequentialStrategy` serves stale context after `cache_ttl` expires

The default `cache_ttl` is 3600 seconds. A cached context that was valid at pipeline start may have expired by the time a later sequential stage reads it. In long-running pipelines or CI environments where the same cached context object is reused across runs, verify that `cache_ttl` matches your actual pipeline duration.

### `NestedStrategy` and `NestedSequentialStrategy` hit depth limits across composition layers

Both classes accept a `max_depth` parameter (defaulting to `NestingContext.DEFAULT_MAX_DEPTH`). When you nest a workflow that itself contains nested steps — common in multi-pass patterns like Deep Review — the combined depth of all layers counts toward this limit. Plan your nesting depth explicitly; reaching the limit raises an error mid-execution rather than at registration time.

### Workflow registry and template registry are global, mutable state

`register_workflow()`, `register_strategy()`, and `register_custom_template()` all modify module-level registries. In tests that share a process, one test's registration persists into the next. Use `unregister_template()` (returns `False` if the template ID is not found) to clean up in teardown. For workflow and strategy registries, structure tests so each one registers only what it needs and runs in isolation.

### `get_workflow()` and `get_template()` fail silently or loudly depending on the call site

`get_workflow(workflow_id)` raises `ValueError` for unknown IDs; `get_template(template_id)` returns `None`. Code that passes a `get_template()` result directly into a strategy without a `None` check will fail later with a less informative error. Check the return value of `get_template()` before use.

## How to avoid problems

1. **Register before you compose.** Call `register_strategy()`, `register_workflow()`, and `register_custom_template()` at application startup, before any pipeline definition references them. Deferred registration causes `ValueError` at execution time, not at startup.

2. **Set depth limits explicitly.** Whenever you use `DelegationChainStrategy`, `NestedStrategy`, or `NestedSequentialStrategy`, pass `max_depth` as a named argument so the limit is visible at the call site rather than inherited from a default you may not remember.

3. **Isolate registry state in tests.** Because all registries are global, run orchestration tests with `pytest -k "orchestration"` in a subprocess or use explicit teardown (`unregister_template()`, or re-initialize the registry) to prevent cross-test contamination that passes locally but fails in CI.

4. **Guard `get_template()` return values.** Treat `None` returns as a hard error in your code rather than propagating them into strategy constructors, where the failure message will not mention the missing template ID.

5. **Depend only on the public API.** Names beginning with `_` — including internal registry helpers — can change without notice between releases. The stable surface is the set of names exported in each module's `__all__`.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
