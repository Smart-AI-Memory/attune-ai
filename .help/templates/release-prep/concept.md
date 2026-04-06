---
feature: release-prep
depth: concept
generated_at: 2026-04-06T04:28:47.997480+00:00
source_hash: aeb4444f7de9953a896940c7fd0a5f0ed0d108bd5650be70b3a6be46d7d1e91c
status: generated
---

# Release Prep

## How it works

Pre-release quality gate workflow that validates code quality, test coverage, and documentation before release.

The main building blocks are:

- **`ReleasePreparationWorkflow`** — Orchestrates quality gate checks using parallel agent execution.
- **`ReleaseAgent`** — Provides progressive model escalation from cheap to premium tiers based on task complexity.
- **`TestCoverageAgent`** — Executes pytest with coverage reporting and analyzes results.
- **`DocumentationAgent`** — Validates docstring coverage, README updates, and CHANGELOG entries.
- **`CodeQualityAgent`** — Performs static analysis with ruff, validates type hints, and measures complexity.

Under the hood, this feature spans 21 source
files covering:

- Agent team coordination with parallel execution capabilities.
- Progressive tier escalation system for cost-effective AI model usage.
- Specialized agents for testing, documentation, and code quality validation.

## What connects to it

This feature relates to: release, publishing, quality.

Other parts of the codebase interact with
release prep through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ReleasePreparationWorkflow` | Orchestrates quality gate checks using parallel agent execution. | `src/attune/workflows/release_prep.py` |
| `ReleaseAgent` | Provides progressive model escalation from cheap to premium tiers based on task complexity. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Executes pytest with coverage reporting and analyzes results. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Validates docstring coverage, README updates, and CHANGELOG entries. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Performs static analysis with ruff, validates type hints, and measures complexity. | `src/attune/agents/release/quality_agent.py` |
