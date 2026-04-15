---
type: concept
feature: release-prep
depth: concept
generated_at: 2026-04-14T14:49:23.856543+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release Prep

Release prep is an automated quality gate system that validates code readiness before publication through coordinated analysis of test coverage, documentation, security, and code quality.

## Core components

**ReleasePreparationWorkflow** orchestrates four specialized subagents (health-checker, security-scanner, changelog-generator, and release-assessor) that work in parallel to assess different aspects of release readiness. Each subagent produces structured markdown findings that get synthesized into a single go/no-go recommendation.

**ReleasePrepTeam** coordinates the parallel execution of release preparation agents, applying configurable quality gates to determine if the codebase meets release standards. The team aggregates results into a `ReleaseReadinessReport` with blockers, warnings, and actionable next steps.

**Individual agents** handle specific validation domains:
- `TestCoverageAgent` runs `pytest --cov` and parses coverage reports
- `DocumentationAgent` verifies docstring coverage, README currency, and CHANGELOG presence
- `CodeQualityAgent` runs ruff checks, validates type hints, and measures code complexity
- `SecurityAuditorAgent` scans for vulnerabilities and outdated dependencies

## Progressive escalation model

All release agents inherit from `ReleaseAgent`, which implements a three-tier cost escalation strategy: CHEAP → CAPABLE → PREMIUM. When a cheaper tier fails to provide confident results, the agent automatically escalates to more powerful (and expensive) analysis capabilities.

Each `ReleaseAgentResult` tracks which tier was used, whether escalation occurred, execution time, cost, and confidence scores to help you optimize the balance between speed and thoroughness.

## Quality gates and reporting

`QualityGate` objects define specific thresholds (like minimum test coverage percentages) that must be met for release approval. The `ReleaseReadinessReport` aggregates all findings into a structured assessment with:

- Overall approval status and confidence rating
- Failed quality gates marked as blockers or warnings
- Detailed agent results with scores and execution metrics
- Prioritized suggestions for addressing issues
- Total cost and duration for the entire assessment

You can call `assess_readiness()` on a `ReleasePrepTeam` instance to get this comprehensive report for any codebase path.
