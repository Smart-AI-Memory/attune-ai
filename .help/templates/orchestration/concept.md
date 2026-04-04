---
feature: orchestration
depth: concept
generated_at: 2026-04-04T02:25:50.561050+00:00
source_hash: 17a454ede63282929b4218973c064c597cdd92171aa4073eb371476a859ea7b4
status: generated
---

# Orchestration

## What

Dynamic teams, workflow composition, and agent models

## Why

This feature provides orchestration functionality for the project.

## How

Key components:

- `ToolEnhancedStrategy` — Single agent with comprehensive tool access.

- `PromptCachedSequentialStrategy` — Sequential execution with shared cached context.

- `DelegationChainStrategy` — Hierarchical delegation with max depth enforcement.

- `ExecutionStrategy` — Base class for agent composition strategies.

- `ConditionalStrategy` — Conditional branching (if X then A else B).
