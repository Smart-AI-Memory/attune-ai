---
type: note
name: orchestration-note
feature: orchestration
depth: note
generated_at: 2026-05-16T06:14:24.036834+00:00
source_hash: ea07a9fe2c597e0620947bda28929f02936ea17148cbff01940256571429e078
status: generated
---

# Note: orchestration

## Context

The `src/attune/orchestration/` module covers three related concerns: dynamic agent team composition, execution strategy selection, and workflow nesting. These are the building blocks that meta-orchestration patterns (Sequential, Parallel, Debate, Teaching, Refinement, Adaptive) are built on top of.

## How the package surface is structured

The module exposes two complementary layers that are designed to compose with each other.

**Execution strategy classes** (defined under `_strategies/`) each extend `ExecutionStrategy` and implement a single `execute(agents, context) -> StrategyResult` signature:

| Class | Where | What it does |
|---|---|---|
| `ExecutionStrategy` | `_strategies/base.py` | Abstract base for all composition strategies |
| `ToolEnhancedStrategy` | `_strategies/advanced_strategies.py` | Runs a single agent with a full tool bundle |
| `PromptCachedSequentialStrategy` | `_strategies/advanced_strategies.py` | Sequential execution with a shared cached context (default TTL: 3600 s) |
| `DelegationChainStrategy` | `_strategies/advanced_strategies.py` | Hierarchical delegation with a configurable max depth (default: 3) |
| `ConditionalStrategy` | `_strategies/conditional_strategies.py` | Branches on a single condition (if/else) |
| `MultiConditionalStrategy` | `_strategies/conditional_strategies.py` | Branches on multiple conditions (switch/case) |
| `NestedStrategy` | `_strategies/nesting.py` | Executes a referenced workflow as a nested unit |
| `NestedSequentialStrategy` | `_strategies/nesting.py` | Sequential steps where each step can be an agent or a workflow reference |

**Registry functions** provide name-based lookup and registration so strategies and workflows can be composed without direct imports:

| Function | Source | What it does |
|---|---|---|
| `get_strategy(name)` | `_strategies/__init__.py` | Returns a strategy instance by name; raises `ValueError` for unknown names |
| `register_strategy(name, cls)` | `_strategies/__init__.py` | Adds a custom `ExecutionStrategy` subclass to the registry |
| `register_workflow(workflow)` | `_strategies/nesting.py` | Makes a `WorkflowDefinition` available for nested references |
| `get_workflow(workflow_id)` | `_strategies/nesting.py` | Retrieves a registered workflow; raises `ValueError` if not found |
| `get_template(template_id)` | `agent_templates/registry.py` | Retrieves an `AgentTemplate` by ID |
| `register_custom_template(template)` | `agent_templates/registry.py` | Adds a user-defined template at runtime |
| `unregister_template(template_id)` | `agent_templates/registry.py` | Removes a template; returns `False` if the ID is not found |

The pattern throughout is consistent: strategy classes hold execution logic, and the registry functions let `MetaOrchestrator` wire them together by name at runtime.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
