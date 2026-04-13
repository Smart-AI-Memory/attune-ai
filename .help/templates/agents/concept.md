---
feature: agents
depth: concept
generated_at: 2026-04-13T16:58:56.239585+00:00
source_hash: dee340db6e093bcd99d9c92c2873020de79933812d17cc3e14cb5331294ac993
status: generated
---

# Agents

## How it works

AI agents that automate release preparation tasks with progressive cost escalation and multi-framework integration.

The main building blocks are:

- **`ReleaseAgent`** — Escalates from cheap to premium models based on task complexity.
- **`TestCoverageAgent`** — Analyzes pytest coverage reports to assess code quality.
- **`DocumentationAgent`** — Validates docstring coverage, README freshness, and CHANGELOG completeness.
- **`CodeQualityAgent`** — Evaluates code quality using ruff linting, type hints, and complexity metrics.
- **`Tier`** — Defines cost and capability tiers for model escalation strategies.

Under the hood, this feature spans 29 source
files covering:

- Release Preparation Agent Team coordination and parallel execution.
- Progressive tier escalation from cheap to premium AI models.
- Integration adapters for LangChain, LangGraph, AutoGen, and Haystack frameworks.

## What connects to it

This feature relates to: agents, ai, release.

Other parts of the codebase interact with
agents through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ReleaseAgent` | Escalates from cheap to premium models based on task complexity. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Analyzes pytest coverage reports to assess code quality. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Validates docstring coverage, README freshness, and CHANGELOG completeness. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Evaluates code quality using ruff linting, type hints, and complexity metrics. | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Defines cost and capability tiers for model escalation strategies. | `src/attune/agents/release/release_models.py` |
