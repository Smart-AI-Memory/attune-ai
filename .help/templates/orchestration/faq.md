---
type: faq
name: orchestration-faq
feature: orchestration
depth: faq
generated_at: 2026-05-16T06:14:24.029814+00:00
source_hash: ea07a9fe2c597e0620947bda28929f02936ea17148cbff01940256571429e078
status: generated
---

# Orchestration FAQ

## What is orchestration?

Orchestration is the meta-orchestration system that composes `BaseWorkflow` instances into multi-agent pipelines using execution strategies. It covers dynamic team building, workflow composition, and agent template management.

## When should I use orchestration instead of calling a workflow directly?

Use orchestration when you need two or more workflows to run together — for example, chaining a security audit into a release prep, or running code review and bug prediction in parallel. If you only need a single workflow, call it directly.

## What composition patterns are available?

Six patterns: **Sequential**, **Parallel**, **Debate**, **Teaching**, **Refinement**, and **Adaptive**. You can also use the conditional variants (`ConditionalStrategy`, `MultiConditionalStrategy`) for if/else branching, and `NestedStrategy` or `NestedSequentialStrategy` when you need workflows nested inside other workflows.

## How do I get a strategy instance?

Call `get_strategy(strategy_name)`. It returns the corresponding `ExecutionStrategy` instance, or raises `ValueError` listing the available strategies if the name isn't recognized.

## How do I add a custom strategy?

Call `register_strategy(name, strategy_class)` with your `ExecutionStrategy` subclass. After registration, `get_strategy(name)` will return an instance of your class.

## How do I use nested workflows?

Register the workflow first with `register_workflow(workflow)`, then reference it by ID inside a `NestedStrategy` or `NestedSequentialStrategy`. Both accept a `max_depth` argument to prevent unbounded recursion.

## What happens if I pass an unknown strategy or workflow name?

- `get_strategy()` raises `ValueError: 'Unknown strategy: {...}. Available: {...}'`
- `get_workflow()` raises `ValueError: 'Unknown workflow: {...}. Available: {...}'`

The error message includes the list of registered names, so you can see exactly what's available.

## How do I find agent templates for a given capability or tier?

Use `get_templates_by_capability(capability)` or `get_templates_by_tier(tier)`. To register your own template at runtime, call `register_custom_template(template)`. To remove one, call `unregister_template(template_id)` — it returns `False` if the ID wasn't found.

## How do I debug an orchestration pipeline that isn't working?

Run `pytest -k "orchestration" -v` first. If the tests pass but your pipeline still fails, add `logger.debug` calls around the `execute()` call on your strategy and re-run with logging enabled. Check that every workflow referenced by ID has been registered with `register_workflow()` before execution starts.

## Where is the source code?

- `src/attune/orchestration/` — meta-orchestration system, execution strategies, and agent templates
- `src/attune/coordination/` — supporting coordination logic

**Tags:** `orchestration`, `teams`
