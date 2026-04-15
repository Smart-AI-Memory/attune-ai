---
type: note
feature: release-prep
depth: note
generated_at: 2026-04-14T14:51:28.268851+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release preparation system

## Overview

The release preparation system automates pre-release quality gates through coordinated agent teams that assess code health, security, documentation, and test coverage. The system produces a structured release readiness report with go/no-go recommendations based on configurable quality thresholds.

## Architecture

The system uses a three-tier cost escalation strategy (CHEAP → CAPABLE → PREMIUM) where agents start with basic checks and escalate to more sophisticated analysis only when needed.

**Core workflow components:**

- `ReleasePreparationWorkflow` — Main orchestrator that coordinates four specialized subagents (health-checker, security-scanner, changelog-generator, release-assessor)
- `ReleasePrepTeam` — Manages parallel execution of release agents and aggregates results into a `ReleaseReadinessReport`

**Individual agents:**

- `ReleaseAgent` — Base class implementing tier escalation for all specialized agents
- `TestCoverageAgent` — Executes pytest with coverage reporting and parses results
- `DocumentationAgent` — Validates docstring coverage, README currency, and changelog presence
- `CodeQualityAgent` — Runs ruff linting and analyzes type hints and complexity metrics

## Quality gates

The system evaluates release readiness through configurable `QualityGate` thresholds. Each gate defines a minimum score, criticality level, and pass/fail criteria. The final `ReleaseReadinessReport` aggregates all agent findings, quality gate results, and provides structured output including blockers, warnings, cost tracking, and execution timing.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
