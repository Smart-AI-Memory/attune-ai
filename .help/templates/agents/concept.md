---
feature: agents
depth: concept
generated_at: 2026-04-06T04:32:17.870269+00:00
source_hash: f4444f832b2067c6c0ece4cfebdca1ecf9eb7d5b16efcf3ba756c35f5da24167
status: generated
---

# Agents

## How it works

The Attune AI Agent System provides release preparation automation through specialized agents that validate code quality, test coverage, and documentation.

The main building blocks are:

- **`ReleaseAgent`** — Base agent with progressive cost optimization across CHEAP, CAPABLE, and PREMIUM model tiers.
- **`TestCoverageAgent`** — Executes pytest with coverage analysis and parses coverage reports.
- **`DocumentationAgent`** — Validates docstring coverage, README currency, and CHANGELOG presence.
- **`CodeQualityAgent`** — Runs ruff linting, validates type hints, and checks code complexity.
- **`ReleasePrepTeam`** — Coordinates parallel execution of multiple release preparation agents.

Under the hood, this feature spans 59 source
files covering:

- AI agent framework adapters for LangChain, LangGraph, AutoGen, and Haystack.
- Release preparation workflow with quality gate thresholds.
- Performance monitoring and cost tracking decorators.

## What connects to it

This feature relates to: agents, ai, release.

Other parts of the codebase interact with
agents through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ReleaseAgent` | Base agent with progressive cost optimization across model tiers. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Executes pytest with coverage analysis and parses coverage reports. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Validates docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff linting, validates type hints, and checks code complexity. | `src/attune/agents/release/quality_agent.py` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry. | `src/attune/agents/release/team_workflow.py` |
