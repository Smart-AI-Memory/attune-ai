---
type: faq
feature: orchestration
depth: faq
generated_at: 2026-04-14T15:18:12.780943+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration FAQ

## What is orchestration?

The orchestration system manages how multiple agents work together to complete complex tasks. It provides strategies for coordinating agent execution, from simple sequential workflows to sophisticated delegation chains and conditional branching.

## When should I use orchestration?

Use orchestration when you need multiple agents to collaborate on a task. This includes scenarios like breaking down complex problems across specialized agents, implementing approval workflows, or creating dynamic teams that adapt based on task requirements.

## What execution strategies are available?

You can choose from several built-in strategies:

- **ToolEnhancedStrategy**: Single agent with comprehensive tool access
- **PromptCachedSequentialStrategy**: Sequential execution with shared cached context
- **DelegationChainStrategy**: Hierarchical delegation with depth limits
- **ConditionalStrategy**: If-then-else branching logic
- **MultiConditionalStrategy**: Switch-case pattern for multiple conditions
- **NestedStrategy**: Execute workflows within workflows

## How do I get started with orchestration?

Start with `get_strategy()` to retrieve a pre-built execution strategy by name. For custom workflows, use `register_workflow()` to define reusable agent compositions. If you need dynamic agent selection, explore the template registry functions like `get_templates_by_capability()`.

## Can I create custom execution strategies?

Yes. Extend the `ExecutionStrategy` base class and implement the `execute()` method. Then register your custom strategy with `register_strategy()` to make it available throughout your application.

## How does nested execution work?

Nested strategies let you embed workflows within other workflows using `NestedStrategy` or `NestedSequentialStrategy`. Set `max_depth` to prevent infinite recursion. Each nested workflow receives context from its parent and can modify it for subsequent steps.

## How do I debug orchestration issues?

Run `pytest -k "orchestration" -v` to verify the system works correctly. For runtime issues, add debug logging around strategy execution points. Check that your agents are properly registered and that workflow references point to existing definitions.

## Where are the source files?

- `src/attune/orchestration/**` - Core orchestration system
- `src/attune/coordination/**` - Agent coordination utilities
