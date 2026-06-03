---
feature: agents
depth: concept
generated_at: 2026-06-03T02:40:23.573964+00:00
source_hash: bf303cb6343cd2a2e035f09d7021c5950e3aeca3a8891276134183794ba30235
status: generated
---

# Agents

## How it works

Release agents, state persistence, and recovery.

The main building blocks are:

- **`ReleaseAgent`** — Base agent with CHEAP -> CAPABLE -> PREMIUM escalation.
- **`TestCoverageAgent`** — Runs pytest --cov and parses coverage report.
- **`DocumentationAgent`** — Checks docstring coverage, README currency, and CHANGELOG presence.
- **`CodeQualityAgent`** — Runs ruff, checks type hints and complexity.
- **`Tier`** — Model tier for progressive escalation.

Under the hood, this feature spans 29 source
files covering:

- Release Preparation Agent Team.
- Base release agent with progressive tier escalation.
- Test coverage agent for Release Preparation Agent Team.

## What connects to it

This feature relates to: agents, ai, release.

Other parts of the codebase interact with
agents through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Model tier for progressive escalation. | `src/attune/agents/release/release_models.py` |
