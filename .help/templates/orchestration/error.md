---
type: error
name: orchestration-error
feature: orchestration
depth: error
generated_at: 2026-06-22T10:11:35.814147+00:00
source_hash: 1d31bb00ab6284a8ff06a91f07123af0d56d15af02f09b6311f660814398d142
status: generated
---

# Orchestration errors

## Common error signatures

Most orchestration failures are `ValueError` exceptions raised when a strategy name, workflow ID, or agent template cannot be resolved in the registry:

- `ValueError: Unknown strategy: {name}. Available: {...}` — raised by `get_strategy()` when the requested strategy name is not registered.
- `ValueError: Unknown workflow: {id}. Available: {...}` — raised by `get_workflow()` when a `WorkflowReference` points to a workflow ID that was never passed to `register_workflow()`.
- `DelegationChainStrategy` silently enforces a `max_depth` (default: `3`); pipelines that exceed this depth are cut off rather than raising immediately, which can surface as incomplete results rather than an exception.
- `NestedStrategy` and `NestedSequentialStrategy` share the same `NestingContext.DEFAULT_MAX_DEPTH` limit — exceeding it while composing workflows-within-workflows produces errors that name the offending `WorkflowReference`.

## Where errors originate

The following functions are the direct raise sites. Errors returned from `execute()` on any strategy class typically trace back to one of these resolution steps:

- `get_strategy(strategy_name)` — looks up a registered `ExecutionStrategy` subclass by name; raises `ValueError` for unknown names.
- `register_strategy(name, strategy_class)` — registers a custom strategy; incorrect `strategy_class` types cause failures at the next `get_strategy()` call.
- `register_workflow(workflow)` — adds a `WorkflowDefinition` to `WORKFLOW_REGISTRY`; skipping this step before referencing the workflow causes `get_workflow()` to raise.
- `get_workflow(workflow_id)` — resolves a workflow by ID for use in `NestedStrategy` or `NestedSequentialStrategy`; raises `ValueError` if the ID is absent from the registry.
- `get_template(template_id)` — retrieves an `AgentTemplate` from the template registry; returns `None` rather than raising, so a missing template can produce subtle downstream failures in strategy execution.

## How to diagnose

1. **Read the `ValueError` message.** Both `get_strategy()` and `get_workflow()` include the full list of available names in the exception message. Compare that list against the name or ID you passed in — a typo or missing registration step is the most common cause.

2. **Check registration order.** `NestedStrategy` and `NestedSequentialStrategy` resolve `WorkflowReference` objects at execution time, not at construction time. If `register_workflow()` was not called before `execute()` runs, `get_workflow()` raises even though the strategy object was created without error.

3. **Confirm `get_template()` returned a value, not `None`.** Unlike the strategy and workflow lookups, `get_template()` returns `None` for an unknown `template_id` instead of raising. If an agent step produces no output, verify the template ID with `get_all_templates()` and re-register with `register_custom_template()` if it is missing.

4. **Verify `max_depth` for nested and delegation patterns.** `DelegationChainStrategy` defaults to `max_depth=3` and `NestedStrategy` defaults to `NestingContext.DEFAULT_MAX_DEPTH`. If your pipeline is deeper than these limits, pass an explicit `max_depth` at construction time.

5. **Identify the composition pattern in use.** The six patterns — Sequential, Parallel, Debate, Teaching, Refinement, and Adaptive — have different execution paths. Knowing which pattern your `MetaOrchestrator` selected narrows which strategy's `execute()` method to inspect.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
