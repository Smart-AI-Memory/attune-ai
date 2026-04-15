---
type: tip
feature: orchestration
depth: tip
generated_at: 2026-04-14T15:18:39.749906+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Tip: working effectively with orchestration

## Choose the right execution strategy for your workflow pattern

Start with `SequentialStrategy` for simple pipelines, then upgrade to specialized strategies when you need specific behaviors. Sequential execution handles most cases and provides clear error boundaries.

**Why:** Each strategy class optimizes for different composition patterns — `ToolEnhancedStrategy` for tool-heavy workflows, `DelegationChainStrategy` for hierarchical tasks, `ConditionalStrategy` for branching logic. Picking the wrong one early means retrofitting later.

**The tradeoff:** Specialized strategies add complexity but unlock powerful patterns like prompt caching (`PromptCachedSequentialStrategy`) and nested workflows (`NestedSequentialStrategy`).

## Register strategies and templates before using them

Call `register_strategy()` and `register_custom_template()` during initialization, not on-demand during execution. The registry functions expect resources to exist when workflows run.

**Why:** Runtime registration during strategy execution can cause race conditions in parallel workflows and makes debugging much harder when templates are missing.

## Use workflow references for reusable composition patterns

Define complex agent sequences as `WorkflowDefinition` objects and reference them with `WorkflowReference` instead of duplicating agent lists across strategies.

**Why:** Nested workflows let you build libraries of proven patterns while keeping individual strategies focused on their specific execution logic.
