---
type: error
feature: orchestration
depth: error
generated_at: 2026-04-14T15:17:23.213307+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration errors

Failures in agent composition strategies, workflow execution, and template management.

## Common error signatures

- `ValueError: Unknown strategy: {...}. Available: {...}` — Strategy name not found in registry
- `ValueError: Unknown workflow: {...}. Available: {...}` — Workflow ID not found in registry
- `TypeError` — Invalid agent list or context passed to strategy execution
- `RecursionError` — Nesting depth exceeded in delegation chains or nested workflows
- `AttributeError` — Missing required fields in context or malformed strategy configuration

## Where errors originate

- **Strategy lookup** — `get_strategy()` when requesting unregistered strategy names
- **Workflow resolution** — `get_workflow()` when nested strategies reference unknown workflow IDs
- **Template retrieval** — `get_template()` when agent composition requires missing templates
- **Strategy execution** — All strategy `execute()` methods when processing invalid agent lists or context
- **Registration conflicts** — `register_strategy()` and `register_workflow()` when names collide or types mismatch

## How to diagnose

1. **Verify strategy and workflow names**. Check that all strategy names passed to `get_strategy()` match registered entries. Use the "Available" list in ValueError messages to see what's actually registered.

2. **Validate agent and context structures**. Strategy execution fails when agents list contains non-AgentTemplate objects or when required context keys are missing. Check that your agent list and context dictionary match the strategy's expectations.

3. **Check nesting depth limits**. DelegationChainStrategy and NestedStrategy enforce maximum depth limits (default 3). If you're hitting RecursionError, verify your delegation chains and nested workflows don't exceed configured limits.

4. **Trace workflow references**. Nested strategies depend on workflows being registered before execution. Ensure `register_workflow()` calls happen before strategies that reference those workflow IDs.

5. **Examine strategy initialization parameters**. Each strategy class has specific initialization requirements — tools for ToolEnhancedStrategy, conditions for ConditionalStrategy, steps for NestedSequentialStrategy. Mismatched parameters cause TypeError during strategy creation.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
