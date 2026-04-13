---
feature: release-prep
depth: concept
generated_at: 2026-04-13T16:55:22.391502+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release Prep

## How it works

Automated pre-release quality gates that assess code coverage, documentation completeness, and code quality before you ship a release.

The main building blocks are:

- **`ReleasePreparationWorkflow`** — Orchestrates quality gate checks using specialized agent teams with progressive cost escalation.
- **`ReleaseAgent`** — Base agent that escalates from cheap to premium models based on task complexity and previous failures.
- **`TestCoverageAgent`** — Executes pytest with coverage reporting and parses results to assess test completeness.
- **`DocumentationAgent`** — Validates docstring coverage, README file currency, and CHANGELOG file presence.
- **`CodeQualityAgent`** — Runs ruff linting, validates type hints, and measures code complexity.

Under the hood, this feature spans 11 source
files covering:

- Progressive tier escalation system with cost-optimized model selection.
- Parallel agent execution coordination through ReleasePrepTeam.
- Quality gate thresholds and release readiness scoring.

## What connects to it

This feature relates to: release, publishing, quality.

Other parts of the codebase interact with
release prep through these interfaces:

| Interface | Purpose | File |
|-----------|---------|------|
| `ReleasePreparationWorkflow` | Orchestrates quality gate checks using specialized agent teams with progressive cost escalation. | `src/attune/workflows/release_prep.py` |
| `ReleaseAgent` | Base agent that escalates from cheap to premium models based on task complexity and previous failures. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Executes pytest with coverage reporting and parses results to assess test completeness. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Validates docstring coverage, README file currency, and CHANGELOG file presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff linting, validates type hints, and measures code complexity. | `src/attune/agents/release/quality_agent.py` |
