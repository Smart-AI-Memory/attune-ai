---
type: concept
name: orchestration-concept
feature: orchestration
depth: concept
generated_at: 2026-05-16T06:14:24.004585+00:00
source_hash: ea07a9fe2c597e0620947bda28929f02936ea17148cbff01940256571429e078
status: generated
---

# Orchestration

Orchestration is the system that selects an execution strategy, assembles the right agents, and routes data between them so that complex multi-step tasks run as a single coordinated pipeline.

## Mental model

Every orchestrated task moves through three layers:

1. **Strategy selection** — `MetaOrchestrator` examines the task's complexity, domain, and requirements, then picks a composition pattern (Sequential, Parallel, Debate, Teaching, Refinement, or Adaptive). You can also call `get_strategy(name)` directly to bypass automatic selection.
2. **Agent assembly** — The registry supplies `AgentTemplate` instances matched by capability or tier. Dynamic teams can be built at runtime via `DynamicTeamBuilder` and stored in `TeamStore`.
3. **Execution** — The chosen `ExecutionStrategy` subclass calls `execute(agents, context)`, enforces any quality gates or depth limits, and returns a `StrategyResult` that downstream stages or callers consume.

This separation means you can swap strategies — for example, replacing `SequentialStrategy` with `ParallelStrategy` — without changing the agents or the code that reads the result.

## Execution strategies

Each strategy implements `ExecutionStrategy.execute(agents, context) -> StrategyResult`. The strategies available out of the box are:

| Strategy | What it does |
|---|---|
| `SequentialStrategy` | Runs agents one after another, passing output forward |
| `ParallelStrategy` | Runs agents concurrently and merges results |
| `DebateStrategy` | Agents argue positions; a judge resolves conflicts |
| `TeachingStrategy` | A lead agent instructs subordinate agents |
| `RefinementStrategy` | Each agent iteratively improves the previous output |
| `AdaptiveStrategy` | Switches sub-strategy at runtime based on intermediate results |
| `ToolEnhancedStrategy` | Single agent with access to the full tool set |
| `PromptCachedSequentialStrategy` | Sequential execution with a shared cached context (default TTL: 3600 s) |
| `DelegationChainStrategy` | Hierarchical delegation enforcing a configurable `max_depth` (default: 3) |
| `ConditionalStrategy` | Branches execution: if *condition* then *A* else *B* |
| `MultiConditionalStrategy` | Switch/case branching across multiple conditions with an optional default |
| `NestedStrategy` | Embeds a registered `WorkflowDefinition` as a single step |
| `NestedSequentialStrategy` | Sequential steps where any step can be an agent or a nested workflow |

Use `register_strategy(name, strategy_class)` to add your own implementation to the registry.

## Workflow composition

Workflows are named, reusable pipelines registered with `register_workflow(workflow)` and retrieved by ID with `get_workflow(workflow_id)`. `NestedStrategy` and `NestedSequentialStrategy` reference them by `WorkflowReference`, which lets one workflow embed another up to a configurable nesting depth.

A concrete example from the meta-orchestration patterns: a Secure Release pipeline uses `SequentialStrategy` to chain `security_audit → dependency_check → release_prep`, where each stage is itself a registered workflow.

## Agent registry

The registry decouples strategy logic from agent definitions:

- `get_template(template_id)` — retrieve one template by ID
- `get_templates_by_capability(capability)` — find agents that expose a specific capability
- `get_templates_by_tier(tier)` — find agents preferring a resource tier
- `register_custom_template(template)` — add a user-defined agent at runtime
- `unregister_template(template_id)` — remove a template; returns `False` if the ID is not found

## Key interfaces

Other parts of the codebase interact with orchestration through these entry points:

| Interface | Purpose | Source |
|---|---|---|
| `ExecutionStrategy` | Base class every strategy extends | `_strategies/base.py` |
| `ToolEnhancedStrategy` | Single-agent execution with full tool access | `_strategies/advanced_strategies.py` |
| `PromptCachedSequentialStrategy` | Sequential execution with shared prompt cache | `_strategies/advanced_strategies.py` |
| `DelegationChainStrategy` | Hierarchical delegation with depth enforcement | `_strategies/advanced_strategies.py` |
| `ConditionalStrategy` | If/else branching between workflow branches | `_strategies/conditional_strategies.py` |
| `MultiConditionalStrategy` | Switch/case branching with optional default | `_strategies/conditional_strategies.py` |
| `NestedStrategy` | Embed a registered workflow as a single step | `_strategies/conditional_strategies.py` |
