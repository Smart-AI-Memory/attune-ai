---
feature: release-prep
depth: reference
generated_at: 2026-06-03T02:40:23.503322+00:00
source_hash: 9679637cf4b036b0008d2a617c88f123b0b717c30fe4698e89a4a098e1edc251
status: generated
---

# Release Prep reference

## Classes

| Class | Description | File |
|-------|-------------|------|
| `ReleasePreparationWorkflow` | Pre-release quality gate workflow powered by Agent SDK subagents. | `src/attune/workflows/release_prep.py` |
| `ReleaseAgent` | Base agent with CHEAP -> CAPABLE -> PREMIUM escalation. | `src/attune/agents/release/base_agent.py` |
| `TestCoverageAgent` | Runs pytest --cov and parses coverage report. | `src/attune/agents/release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `src/attune/agents/release/documentation_agent.py` |
| `CodeQualityAgent` | Runs ruff, checks type hints and complexity. | `src/attune/agents/release/quality_agent.py` |
| `Tier` | Model tier for progressive escalation. | `src/attune/agents/release/release_models.py` |
| `ReleaseAgentResult` | Result from an individual release agent. | `src/attune/agents/release/release_models.py` |
| `QualityGate` | Quality gate threshold for release readiness. | `src/attune/agents/release/release_models.py` |
| `ReleaseReadinessReport` | Aggregated release readiness assessment. | `src/attune/agents/release/release_models.py` |
| `ReleasePrepTeam` | Coordinates parallel execution of release preparation agents. | `src/attune/agents/release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Workflow wrapper that integrates ReleasePrepTeam with the CLI registry. | `src/attune/agents/release/release_prep_team.py` |
| `SecurityAuditorAgent` | Analyzes bandit output and classifies vulnerabilities by severity. | `src/attune/agents/release/security_agent.py` |



## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

## Tags

`release`, `publishing`, `quality`
