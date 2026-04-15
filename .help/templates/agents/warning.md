---
type: warning
feature: agents
depth: warning
generated_at: 2026-04-14T15:09:03.396100+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agents cautions

## What to watch for

The agents module provides AI-powered release preparation with progressive tier escalation and parallel execution. Key risks involve cost escalation, state inconsistency, and adapter initialization failures.

## Risk areas

**Unexpected cost escalation in ReleaseAgent**
The `ReleaseAgent` automatically escalates from CHEAP to CAPABLE to PREMIUM tiers when confidence thresholds aren't met. Without monitoring, a single agent run can consume significantly more API credits than expected if the cheaper models struggle with your codebase's complexity.

**Redis state corruption during parallel execution**
`ReleasePrepTeam` runs multiple agents concurrently, all potentially writing to the same Redis state store. If two agents update state simultaneously, you may get incomplete results, duplicated work, or corrupted execution records that break recovery attempts.

**Lazy adapter imports masking dependency issues**
The framework adapters (`get_langchain_adapter()`, `get_langgraph_adapter()`, etc.) use lazy imports that only fail when first called. Your code may pass all static checks but crash at runtime when an agent tries to load a missing optional dependency like LangChain or AutoGen.

**Quality gate failures blocking releases incorrectly**
`ReleasePrepTeam` uses quality gates with default thresholds that may not fit your project. A critical gate can block an otherwise ready release if the threshold is misconfigured, while non-critical gates may pass releases that shouldn't ship.

## How to avoid problems

**Set cost limits before escalation**
Monitor the `total_cost` field in `ReleaseReadinessReport` and configure your AI provider's usage limits. Test with CHEAP tier agents first to understand baseline costs before enabling automatic escalation.

**Use separate Redis namespaces for parallel runs**
Initialize each agent with a unique `agent_id` and consider using Redis key prefixes to isolate state between concurrent executions. The `AgentStateStore` supports this pattern.

**Validate adapter dependencies early**
Call adapter functions during application startup rather than waiting for runtime. Add dependency checks to your CI pipeline to catch missing packages before deployment.

**Customize quality gates for your project**
Review default thresholds in `ReleasePrepTeam.__init__()` and adjust based on your project's maturity. Mark gates as non-critical (`critical: bool = False`) if they should warn but not block releases.

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
