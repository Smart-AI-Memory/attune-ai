---
feature: release-prep
depth: task
generated_at: 2026-06-01T11:59:09.433154+00:00
source_hash: 4c7a32841bb910c6bfc8e67572024ffed2759925aeba9ce59b7fbfb6fda20b18
status: generated
---

# Work with release prep

Use release prep when you need to pre-release quality gate — health checks, security audit, changelog, version bumps.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/release_prep.py

## Steps

1. **Understand the class hierarchy.**
   Read the interfaces to see how release prep
   is structured before extending or modifying.
   The key classes are:
   - `ReleasePreparationWorkflow` in `src/attune/workflows/release_prep.py` — Pre-release quality gate workflow powered by Agent SDK subagents.
   - `ReleaseAgent` in `src/attune/agents/release/base_agent.py` — Base agent with CHEAP -> CAPABLE -> PREMIUM escalation.
   - `TestCoverageAgent` in `src/attune/agents/release/coverage_agent.py` — Runs pytest --cov and parses coverage report.
   - `DocumentationAgent` in `src/attune/agents/release/documentation_agent.py` — Checks docstring coverage, README currency, and CHANGELOG presence.
   - `CodeQualityAgent` in `src/attune/agents/release/quality_agent.py` — Runs ruff, checks type hints and complexity.
2. **Decide whether to extend or modify.**
   If the class has subclasses, extend with a new one
   rather than changing the base. If it stands alone,
   modify directly.

3. **Make your change.**
   Follow existing patterns — naming, error handling,
   and logging style.

4. **Run the related tests.**
   Target with `pytest -k "release-prep"`.

## Key files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

## Common modifications

Classes you are most likely to extend:

- `ReleasePreparationWorkflow` in `src/attune/workflows/release_prep.py`
- `ReleaseAgent` in `src/attune/agents/release/base_agent.py`
- `TestCoverageAgent` in `src/attune/agents/release/coverage_agent.py`
- `DocumentationAgent` in `src/attune/agents/release/documentation_agent.py`
- `CodeQualityAgent` in `src/attune/agents/release/quality_agent.py`
- `Tier` in `src/attune/agents/release/release_models.py`
- `ReleaseAgentResult` in `src/attune/agents/release/release_models.py`
- `QualityGate` in `src/attune/agents/release/release_models.py`
