---
feature: orchestration
depth: concept
generated_at: 2026-04-13T17:00:50.551522+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration

## How it works

Meta-orchestration system for dynamic agent composition with multiple execution strategies.

The main building blocks are:

- **`ToolEnhancedStrategy`** — Single agent with comprehensive tool access.
- **`PromptCachedSequentialStrategy`** — Sequential execution with shared cached context.
- **`DelegationChainStrategy`** — Hierarchical delegation with max depth enforcement.
- **`ExecutionStrategy`** — Base class for agent composition strategies.
- **`ConditionalStrategy`** — Conditional branching (if X then A else B).

Under the hood, this feature spans 40 source
files covering:

- Meta-orchestration system for dynamic agent composition.
- Conditional and nested execution strategies.
- Advanced execution strategy patterns (11-13).

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
