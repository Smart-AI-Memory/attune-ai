---
feature: orchestration
depth: concept
generated_at: 2026-05-12T19:43:13.442907+00:00
source_hash: 2725f174f20d390207993b0b3706b8aaa174cbf7fbfc3fbe24bea851e95249d2
status: generated
---

# Orchestration

## How it works

Dynamic teams, workflow composition, and agent models.

The main building blocks are:

- **`ToolEnhancedStrategy`** — Single agent with comprehensive tool access.
- **`PromptCachedSequentialStrategy`** — Sequential execution with shared cached context.
- **`DelegationChainStrategy`** — Hierarchical delegation with max depth enforcement.
- **`ExecutionStrategy`** — Base class for agent composition strategies.
- **`ConditionalStrategy`** — Conditional branching (if X then A else B).

Under the hood, this feature spans 36 source
files covering:

- Execution strategies for agent composition patterns.
- Advanced execution strategy patterns (11-13).
- Base class for agent composition strategies.

## What connects to it

This feature relates to: orchestration, teams.

Other parts of the codebase interact with
orchestration through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ToolEnhancedStrategy` | Single agent with comprehensive tool access. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `PromptCachedSequentialStrategy` | Sequential execution with shared cached context. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `DelegationChainStrategy` | Hierarchical delegation with max depth enforcement. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `ExecutionStrategy` | Base class for agent composition strategies. | `src/attune/orchestration/_strategies/base.py` |
| `ConditionalStrategy` | Conditional branching (if X then A else B). | `src/attune/orchestration/_strategies/conditional_strategies.py` |
