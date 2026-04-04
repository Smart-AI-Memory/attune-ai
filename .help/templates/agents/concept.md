---
feature: agents
depth: concept
generated_at: 2026-04-04T02:25:50.462368+00:00
source_hash: f4444f832b2067c6c0ece4cfebdca1ecf9eb7d5b16efcf3ba756c35f5da24167
status: generated
---

# Agents

## What

Release agents, state persistence, and recovery

## Why

This feature provides agents functionality for the project.

## How

Key components:

- `ReleaseAgent` — Base agent with CHEAP -> CAPABLE -> PREMIUM escalation.

- `TestCoverageAgent` — Runs pytest --cov and parses coverage report.

- `DocumentationAgent` — Checks docstring coverage, README currency, and CHANGELOG presence.

- `CodeQualityAgent` — Runs ruff, checks type hints and complexity.

- `Tier` — Model tier for progressive escalation.
