---
type: task
feature: orchestration
depth: task
generated_at: 2026-04-14T15:16:22.135027+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Work with orchestration

Use orchestration when you need to compose dynamic agent teams, execute complex workflows with conditional logic, or implement hierarchical delegation patterns.

## Prerequisites

- Access to the project source code
- Familiarity with the files under `src/attune/orchestration/`

## Identify your orchestration pattern

1. **Determine your execution strategy.**
   Choose the strategy that matches your workflow pattern:
   - `ToolEnhancedStrategy` — Single agent with comprehensive tool access
   - `PromptCachedSequentialStrategy` — Sequential execution with shared cached context
   - `DelegationChainStrategy` — Hierarchical delegation with depth limits
   - `ConditionalStrategy` — If-then-else branching logic
   - `MultiConditionalStrategy` — Switch-case pattern with multiple conditions
   - `NestedStrategy` — Workflow composition with sub-workflows
   - `NestedSequentialStrategy` — Sequential steps with nested workflow support

2. **Review strategy requirements.**
   Check the strategy's initialization parameters and execution context needs.
   For example, `DelegationChainStrategy` requires a `max_depth` parameter, while
   `ConditionalStrategy` needs condition and branch definitions.

## Configure execution strategy

1. **Register your strategy (if custom).**
   ```python
   from attune.orchestration import register_strategy
   register_strategy("my_strategy", MyCustomStrategy)
   ```

2. **Retrieve and configure the strategy.**
   ```python
   from attune.orchestration import get_strategy
   strategy = get_strategy("delegation_chain")
   ```

3. **Set up agent templates.**
   Register templates for your agents using the template registry:
   ```python
   from attune.orchestration import register_custom_template
   register_custom_template(my_agent_template)
   ```

## Execute your workflow

1. **Prepare execution context.**
   Create a context dictionary with the data your agents need:
   ```python
   context = {
       "task_data": your_data,
       "user_input": user_request,
       "session_id": session_identifier
   }
   ```

2. **Execute the strategy.**
   ```python
   result = strategy.execute(agents, context)
   ```

3. **Handle the result.**
   Check the `StrategyResult` for success status, output data, and any errors.

## Verify execution

Your orchestration works correctly when:
- The strategy executes without raising exceptions
- The `StrategyResult.success` field returns `True`
- The output contains expected data from your agents
- For nested workflows, sub-workflow results appear in the context

## Key files

- `src/attune/orchestration/_strategies/` — Execution strategy implementations
- `src/attune/orchestration/agent_templates/registry.py` — Agent template management
- `src/attune/coordination/` — Team coordination and conflict resolution
