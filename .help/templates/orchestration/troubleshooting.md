---
type: troubleshooting
feature: orchestration
depth: troubleshooting
generated_at: 2026-04-14T15:17:53.421930+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Troubleshoot orchestration

## Before you start

The orchestration system manages dynamic agent composition, execution strategies, and workflow coordination. Issues typically involve strategy selection, agent template registration, or workflow execution flow.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `ValueError: Unknown strategy` | Strategy name passed to `get_strategy()` and registered strategies |
| `ValueError: Unknown workflow` | Workflow ID passed to `get_workflow()` and registered workflows |
| Agents not executing in expected order | Strategy type (Sequential vs Parallel vs Conditional) and branch conditions |
| Missing tool access in agents | `ToolEnhancedStrategy` tool list and agent capabilities |
| Nested workflows failing | `max_depth` limits and `NestingContext` configuration |
| Strategy execution returns empty results | Agent template availability and context data structure |

## Step-by-step diagnosis

1. **Reproduce with minimal strategy setup.**
   Create a simple test case using the failing strategy with one or two agents. Remove complex conditions, nested workflows, and custom context data to isolate the core issue.

2. **Verify strategy and template registration.**
   Check that your strategy exists:
   ```python
   from attune.orchestration import get_strategy
   try:
       strategy = get_strategy("your_strategy_name")
       print(f"Strategy found: {type(strategy)}")
   except ValueError as e:
       print(f"Strategy error: {e}")
   ```

3. **Inspect agent template availability.**
   Confirm required templates are registered:
   ```python
   from attune.orchestration.agent_templates import get_all_templates, get_template
   templates = get_all_templates()
   print(f"Available templates: {[t.id for t in templates]}")
   ```

4. **Enable debug logging for execution flow.**
   Add logging to see strategy execution steps:
   ```python
   import logging
   logging.getLogger('attune.orchestration').setLevel(logging.DEBUG)
   ```

5. **Test execution strategies in order of complexity.**
   Start with `SequentialStrategy`, then try `ConditionalStrategy`, then nested strategies. This isolates whether the issue is in basic execution or advanced control flow.

## Common fixes

- **Register missing strategies or workflows.**
  ```python
  from attune.orchestration import register_strategy, register_workflow
  register_strategy("custom_name", YourStrategyClass)
  register_workflow(your_workflow_definition)
  ```

- **Fix strategy configuration errors.**
  - `DelegationChainStrategy`: Reduce `max_depth` if hitting recursion limits
  - `ConditionalStrategy`: Verify condition logic and branch definitions
  - `ToolEnhancedStrategy`: Ensure tools list matches agent requirements

- **Handle template registration timing.**
  Register custom templates before strategy execution:
  ```python
  from attune.orchestration.agent_templates import register_custom_template
  register_custom_template(your_agent_template)
  ```

- **Check context data structure.**
  Strategies expect specific context keys. Verify your context dictionary contains required data for the strategy type you're using.

- **Resolve nesting depth limits.**
  For `NestedStrategy` or `NestedSequentialStrategy`, increase `max_depth` or restructure workflows to reduce nesting levels.

## Source files

- `src/attune/orchestration/_strategies/` — Strategy implementations
- `src/attune/orchestration/agent_templates/` — Agent template registry
- `src/attune/coordination/` — Team coordination and conflict resolution

**Tags:** `orchestration`, `teams`
