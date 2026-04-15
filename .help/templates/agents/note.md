---
type: note
feature: agents
depth: note
generated_at: 2026-04-14T15:10:09.166748+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Note: agents

## Context

The agents module implements an AI-powered release preparation system that automates code quality assessment and release readiness validation.

## Agent architecture

The system uses a progressive tier escalation strategy where agents start with cheaper models (CHEAP tier) and escalate to more expensive, capable models (CAPABLE -> PREMIUM) when needed. This approach balances cost efficiency with accuracy for complex analysis tasks.

### Release preparation agents

The `ReleasePrepTeam` coordinates specialized agents that run in parallel:

- **TestCoverageAgent** — Executes `pytest --cov` and parses coverage reports
- **DocumentationAgent** — Validates docstring coverage, README currency, and CHANGELOG presence
- **CodeQualityAgent** — Runs `ruff` linting and checks type hints and complexity metrics

Each agent inherits from `ReleaseAgent` and returns structured results through `ReleaseAgentResult`, including success status, tier used, findings, and cost tracking.

### State management

Agents support Redis-based state persistence through `AgentStateStore`, enabling recovery from failures and maintaining execution history via `AgentExecutionRecord`. The `AgentRecoveryManager` handles automatic retry logic with exponential backoff.

## Framework adapters

The system provides adapters for popular AI frameworks through lazy-loaded functions:

- `get_langchain_adapter()` — LangChain integration
- `get_langgraph_adapter()` — LangGraph workflows
- `get_autogen_adapter()` — AutoGen multi-agent systems
- `get_haystack_adapter()` — Haystack NLP pipelines

The `wrap_wizard()` helper quickly converts wizard instances into agents, while the `WizardAdapter` provides native integration.

## Quality gates and reporting

Release readiness is determined by configurable quality gates defined in `QualityGate` objects. The `ReleaseReadinessReport` aggregates all agent results into an approval decision with confidence metrics, blockers, warnings, and cost summaries.

## Source files

- `src/attune/agents/**`
- `src/attune/agent_factory/**`

**Tags:** `agents`, `ai`, `release`
