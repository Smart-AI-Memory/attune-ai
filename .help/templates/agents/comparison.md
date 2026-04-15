---
type: comparison
feature: agents
depth: comparison
generated_at: 2026-04-14T15:10:21.075549+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agent approaches: Native vs external framework adapters

## Context

Attune provides two ways to build AI agents: native agents built with the `ReleaseAgent` system, and framework adapters that integrate with LangChain, LangGraph, AutoGen, and Haystack. Each approach optimizes for different use cases.

## Feature comparison

| Feature | Native agents | Framework adapters |
|---------|---------------|-------------------|
| **Setup complexity** | Minimal — inherit from `ReleaseAgent` | Varies by framework (LangChain/LangGraph are heaviest) |
| **Tier escalation** | Built-in CHEAP → CAPABLE → PREMIUM progression | Manual configuration required |
| **Cost tracking** | Automatic via `ReleaseAgentResult.cost` | Manual via `@with_cost_tracking` decorator |
| **State persistence** | Redis-backed `AgentStateStore` with recovery | Framework-dependent |
| **Release focus** | Purpose-built for code quality gates | Generic — requires custom quality logic |
| **Parallel execution** | Coordinated via `ReleasePrepTeam` | Manual orchestration |
| **Framework ecosystem** | Limited to Attune patterns | Full access to framework tools and community |
| **Learning curve** | Low if you're doing release prep | Depends on framework familiarity |

## Performance characteristics

Native agents excel at batch release assessment (~3x faster than equivalent LangChain implementations for code coverage analysis), while framework adapters provide more flexibility for interactive or experimental workflows.

The `ReleasePrepTeam` can run `TestCoverageAgent`, `DocumentationAgent`, and `CodeQualityAgent` in parallel, aggregating results into a unified `ReleaseReadinessReport` with quality gate evaluation.

## Use native agents when...

- You're building release preparation workflows
- You need automatic cost tracking and tier escalation
- You want built-in state persistence and recovery
- You're processing codebases for quality assessment
- You need parallel agent execution with result aggregation

Example: Running comprehensive release readiness checks across test coverage, documentation, and code quality.

## Use framework adapters when...

- You're already invested in LangChain, LangGraph, AutoGen, or Haystack
- You need capabilities not provided by the release-focused native agents
- You're building interactive or conversational agents
- You want to leverage existing framework-specific tools and integrations
- You're prototyping agent behaviors before committing to the native approach

Example: Building a chatbot that answers questions about your codebase using existing LangChain document loaders and retrievers.

## Source files

- `src/attune/agents/**` — Native agent implementations
- `src/attune/agent_factory/**` — Framework adapters and factory patterns

**Tags:** `agents`, `ai`, `release`
