---
feature: orchestration
depth: concept
generated_at: 2026-04-06T04:34:15.551931+00:00
source_hash: 17a454ede63282929b4218973c064c597cdd92171aa4073eb371476a859ea7b4
status: generated
---

# Orchestration

## How it works

Dynamic agent composition patterns for multi-agent workflows and complex task execution.

The main building blocks are:

- **`ToolEnhancedStrategy`** — Provides a single agent with comprehensive tool access for enhanced capabilities.
- **`PromptCachedSequentialStrategy`** — Executes agents sequentially while maintaining shared cached context across the workflow.
- **`DelegationChainStrategy`** — Implements hierarchical task delegation with maximum depth enforcement to prevent infinite recursion.
- **`ExecutionStrategy`** — Serves as the base class that all agent composition strategies inherit from.
- **`ConditionalStrategy`** — Enables conditional branching logic where different agents execute based on runtime conditions.

Under the hood, this feature spans 82 source
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
| `ToolEnhancedStrategy` | Provides a single agent with comprehensive tool access for enhanced capabilities. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `PromptCachedSequentialStrategy` | Executes agents sequentially while maintaining shared cached context across the workflow. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `DelegationChainStrategy` | Implements hierarchical task delegation with maximum depth enforcement to prevent infinite recursion. | `src/attune/orchestration/_strategies/advanced_strategies.py` |
| `ExecutionStrategy` | Serves as the base class that all agent composition strategies inherit from. | `src/attune/orchestration/_strategies/base.py` |
| `ConditionalStrategy` | Enables conditional branching logic where different agents execute based on runtime conditions. | `src/attune/orchestration/_strategies/conditional_strategies.py` |
