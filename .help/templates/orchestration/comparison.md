---
type: comparison
feature: orchestration
depth: comparison
generated_at: 2026-04-14T15:19:00.027172+00:00
source_hash: 91df7dc60aee10d161a92b560bea2ad2eff169c3358bca0dbb7cdbb283fc9705
status: generated
---

# Orchestration strategies comparison

## Context

The orchestration system provides multiple execution strategies for composing and coordinating agent teams. Each strategy handles different patterns of agent interaction, from simple sequential execution to complex hierarchical delegation and conditional branching.

## Strategy comparison

| Strategy | Best for | Execution pattern | Key limitation |
|----------|----------|------------------|----------------|
| **ToolEnhancedStrategy** | Single agent with comprehensive tool access | One agent + all available tools | No multi-agent coordination |
| **PromptCachedSequentialStrategy** | Sequential tasks with shared context | Linear chain with cached results (1 hour TTL) | No parallelization or branching |
| **DelegationChainStrategy** | Hierarchical task breakdown | Tree-like delegation (max 3 levels deep) | Fixed depth limit |
| **ConditionalStrategy** | Simple if/then logic | Binary branching based on conditions | Only two branches supported |
| **MultiConditionalStrategy** | Complex decision trees | Switch/case pattern with multiple branches | All conditions evaluated sequentially |
| **NestedStrategy** | Workflow composition | Embeds complete workflows within workflows | Recursive depth limited by `max_depth` |
| **NestedSequentialStrategy** | Mixed agent/workflow sequences | Linear execution mixing agents and nested workflows | No parallel execution within steps |

## Performance characteristics

**PromptCachedSequentialStrategy** is ~3x faster for repeated operations due to context caching, but the 1-hour TTL means cold starts for long-running workflows.

**ToolEnhancedStrategy** has the lowest coordination overhead since it uses a single agent, but cannot leverage specialized agent capabilities.

**DelegationChainStrategy** scales well for complex tasks but hits depth limits at 3 levels, making it unsuitable for deeply nested problem decomposition.

## Use X when...

**Use ToolEnhancedStrategy when** you have a single, capable agent that can handle the entire task with comprehensive tool access.

**Use PromptCachedSequentialStrategy when** you need sequential processing with expensive context computation that benefits from caching between runs.

**Use DelegationChainStrategy when** your task naturally decomposes into a hierarchy no more than 3 levels deep and you want automatic load distribution.

**Use ConditionalStrategy when** you have simple binary decision logic that determines which agent or workflow branch to execute.

**Use MultiConditionalStrategy when** you need complex routing logic with multiple possible execution paths based on context evaluation.

**Use NestedStrategy when** you want to embed complete, reusable workflows within larger compositions.

**Use NestedSequentialStrategy when** you need to mix individual agents and complete workflows in a linear sequence.

For most applications, start with **PromptCachedSequentialStrategy** — it handles the common case of sequential agent coordination with good caching behavior. Upgrade to conditional or nested strategies only when you need explicit branching or workflow composition.

## Source files

- `src/attune/orchestration/**`
- `src/attune/coordination/**`

**Tags:** `orchestration`, `teams`
