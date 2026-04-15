---
type: note
feature: orchestration
depth: note
generated_at: 2026-04-14T15:18:50.457216+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration system

## Context

The orchestration system enables dynamic composition of AI agents through execution strategies, workflow definitions, and agent templates. It handles everything from simple sequential execution to complex conditional branching and nested workflows.

## Architecture

The orchestration feature centers around the `ExecutionStrategy` base class, which defines how groups of agents work together. Concrete strategies implement specific composition patterns:

- **ToolEnhancedStrategy** — Runs a single agent with comprehensive tool access
- **SequentialStrategy** — Executes agents one after another, passing context forward
- **ParallelStrategy** — Runs multiple agents concurrently
- **ConditionalStrategy** — Branches execution based on runtime conditions
- **NestedStrategy** — Embeds complete workflows within other workflows

The system supports both simple strategies (single pattern execution) and advanced strategies that combine multiple patterns. For example, `DelegationChainStrategy` implements hierarchical delegation with depth limits to prevent infinite recursion.

## Registration and discovery

The orchestration system uses a registration pattern for both strategies and agent templates. You register strategies with `register_strategy()` and retrieve them with `get_strategy()`. Similarly, agent templates are registered and retrieved through functions like `get_template()` and `get_templates_by_capability()`.

This registration approach allows the system to dynamically compose teams at runtime based on available agents and their declared capabilities, rather than requiring hardcoded team configurations.

## Workflow nesting

The system supports nested workflows through `WorkflowDefinition` and `WorkflowReference` types. You can register complete workflows with `register_workflow()` and reference them from within other workflows. The `NestingContext` enforces depth limits to prevent infinite recursion in nested compositions.
