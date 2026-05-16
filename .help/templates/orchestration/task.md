---
type: task
name: orchestration-task
feature: orchestration
depth: task
generated_at: 2026-05-16T06:14:24.010384+00:00
source_hash: ea07a9fe2c597e0620947bda28929f02936ea17148cbff01940256571429e078
status: generated
---

# Work with orchestration

Use orchestration when you need to compose dynamic agent teams, wire up execution strategies, and manage workflow and template registries.

## Prerequisites

- Access to the project source code under `src/attune/orchestration/`
- Familiarity with the `ExecutionStrategy` base class and the `AgentTemplate` data model

## Steps

1. **Identify the entry point for your goal.**
   Match your goal to the function that owns that responsibility:

   | Goal | Function | Location |
   |---|---|---|
   | Retrieve a strategy by name | `get_strategy()` | `src/attune/orchestration/_strategies/__init__.py` |
   | Register a new strategy class | `register_strategy()` | `src/attune/orchestration/_strategies/__init__.py` |
   | Register a workflow for nested references | `register_workflow()` | `src/attune/orchestration/_strategies/nesting.py` |
   | Retrieve a registered workflow by ID | `get_workflow()` | `src/attune/orchestration/_strategies/nesting.py` |
   | Retrieve an agent template by ID | `get_template()` | `src/attune/orchestration/agent_templates/registry.py` |
   | List all registered templates | `get_all_templates()` | `src/attune/orchestration/agent_templates/registry.py` |
   | Filter templates by capability | `get_templates_by_capability()` | `src/attune/orchestration/agent_templates/registry.py` |
   | Filter templates by tier | `get_templates_by_tier()` | `src/attune/orchestration/agent_templates/registry.py` |

2. **Read the function's signature and docstring.**
   Confirm the parameter types, return type, and any exceptions the function raises. For example, `get_strategy()` raises `ValueError` with the message `'Unknown strategy: {...}. Available: {...}'` when the name is not registered, and `get_workflow()` raises a similar `ValueError` for unknown workflow IDs.

3. **Make your change in the target function.**
   Apply the naming conventions, error-handling style, and logging patterns already present in that file. If you are registering a new strategy, pass a `name` string and a class that subclasses `ExecutionStrategy`. If you are registering a workflow, pass a `WorkflowDefinition` instance.

4. **Run the targeted test suite.**
   Execute `pytest -k "orchestration"` to catch regressions before they affect other developers.

## Key files

- `src/attune/orchestration/_strategies/__init__.py` — strategy registry and `get_strategy` / `register_strategy`
- `src/attune/orchestration/_strategies/nesting.py` — workflow registry and nested execution strategies
- `src/attune/orchestration/agent_templates/registry.py` — agent template registry
- `src/attune/coordination/` — coordination layer that consumes orchestration strategies

## Verify success

After running `pytest -k "orchestration"`, all tests pass with no failures or errors. If you registered a new strategy, call `get_strategy("<your_strategy_name>")` in a Python REPL and confirm it returns an instance of your class without raising `ValueError`. If you registered a workflow, call `get_workflow("<your_workflow_id>")` and confirm it returns your `WorkflowDefinition`.
