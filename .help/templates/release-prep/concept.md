---
feature: release-prep
depth: concept
generated_at: 2026-06-03T02:40:23.491828+00:00
source_hash: 9679637cf4b036b0008d2a617c88f123b0b717c30fe4698e89a4a098e1edc251
status: generated
---

# Release Prep

## How it works

Pre-release quality gate — health checks, security audit, changelog, version bumps.

The main building blocks are:

- **`ReleasePreparationWorkflow`** — Pre-release quality gate workflow powered by Agent SDK subagents.
- **`ReleaseAgent`** — Base agent with CHEAP -> CAPABLE -> PREMIUM escalation.
- **`TestCoverageAgent`** — Runs pytest --cov and parses coverage report.
- **`DocumentationAgent`** — Checks docstring coverage, README currency, and CHANGELOG presence.
- **`CodeQualityAgent`** — Runs ruff, checks type hints and complexity.

Under the hood, this feature spans 11 source
files covering:

- Release Preparation Agent Team.
- Base release agent with progressive tier escalation.
- Test coverage agent for Release Preparation Agent Team.

## What connects to it

This feature relates to: release, publishing, quality.

Other parts of the codebase interact with
release prep through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ReleasePreparationWorkflow` | Pre-release quality gate workflow powered by Agent SDK subagents. | `src/attune/workflows/release_prep.py` |
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. | `src/attune/agents/release/quality_agent.py` |
