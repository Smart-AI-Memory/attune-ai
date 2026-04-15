---
type: concept
feature: orchestration
depth: concept
generated_at: 2026-04-14T15:16:10.557691+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration

Orchestration is the system that coordinates how multiple AI agents work together by defining execution strategies and managing their composition patterns.

## Core execution strategies

The orchestration system provides several built-in strategies for coordinating agent interactions:

**Sequential strategies** execute agents one after another:
- `PromptCachedSequentialStrategy` passes cached context between agents to avoid recomputing shared information
- `NestedSequentialStrategy` allows workflows to contain other workflows as steps

**Conditional strategies** route work based on runtime conditions:
- `ConditionalStrategy` implements if-then-else branching logic
- `MultiConditionalStrategy` handles switch-case patterns with multiple conditions

**Enhanced execution patterns** provide specialized coordination:
- `ToolEnhancedStrategy` gives a single agent comprehensive access to all available tools
- `DelegationChainStrategy` creates hierarchical delegation with configurable depth limits to prevent infinite recursion

## Strategy composition model

All execution strategies inherit from `ExecutionStrategy` and implement the same interface:
- Accept a list of `AgentTemplate` instances and a shared context dictionary
- Return a `StrategyResult` containing the execution outcome
- Handle agent coordination according to their specific pattern

You register strategies by name using `register_strategy()` and retrieve them with `get_strategy()`. This allows workflows to reference strategies dynamically without hard-coding dependencies.

## Nested workflow support

The orchestration system supports nested workflows through `WorkflowReference` objects. When a step in one workflow references another workflow, the `NestedStrategy` manages the execution depth and context passing between workflow layers. The `NestingContext` enforces maximum depth limits to prevent stack overflow from circular references.

## Template and workflow registry

The orchestration system maintains registries for reusable components:
- Agent templates are stored and retrieved by ID, capability, or tier preference
- Workflows can be registered and referenced by other workflows
- Custom templates can be added at runtime for dynamic composition
