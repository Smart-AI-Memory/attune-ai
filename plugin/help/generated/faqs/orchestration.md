---
name: orchestration
source: content/features/orchestration.md
tags:
- orchestration
- teams
type: faq
---

# Orchestration FAQ

## What does orchestration do that a single workflow doesn't?

A workflow is one analysis; orchestration coordinates **several** agents
into one pipeline. `MetaOrchestrator` analyzes the task (complexity,
domain, requirements), picks a `CompositionPattern`, a team of
`AgentTemplate`s is assembled, and an `ExecutionStrategy` runs them.

## How do I see the available agents?

`get_all_templates()` returns the registry's `AgentTemplate`s (each has
an `id`, `role`, `capabilities`, `tools`, `tier_preference`); fetch one
with `get_template(template_id)`. Filter with
`get_templates_by_capability(...)` or `get_templates_by_tier(...)`, and
add your own with `register_custom_template(...)`.

## Which execution strategies can `get_strategy` return?

Nine names construct with no arguments: `sequential`, `parallel`,
`debate`, `teaching`, `refinement`, `adaptive`, `tool_enhanced`,
`prompt_cached_sequential`, `delegation_chain`. The registry also holds
`conditional`, `multi_conditional`, `nested`, and `nested_sequential`,
but those require constructor arguments — fetching them bare via
`get_strategy` raises `TypeError`, so construct them directly. An
unknown name raises `ValueError`.

## Is orchestration synchronous or asynchronous?

Planning and assembly are synchronous — `MetaOrchestrator.analyze_task`
/ `create_execution_plan` / `compose_team`, the `DynamicTeamBuilder`
methods, and `WorkflowComposer.compose`. The actual run,
`ExecutionStrategy.execute(agents, context)`, is **async** and returns a
`StrategyResult`.

## How do I analyze a task before running it?

`MetaOrchestrator().analyze_task(description)` returns a
`TaskRequirements` with a `complexity` (`TaskComplexity`:
`SIMPLE`/`MODERATE`/`COMPLEX`) and a `domain` (`TaskDomain`).
`create_execution_plan(...)` turns requirements into an `ExecutionPlan`.

## Where is the source?

All orchestration source lives under `src/attune/orchestration/`.

**Tags:** `orchestration`, `teams`
