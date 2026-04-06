---
feature: release-prep
depth: task
generated_at: 2026-04-06T04:28:55.719027+00:00
source_hash: aeb4444f7de9953a896940c7fd0a5f0ed0d108bd5650be70b3a6be46d7d1e91c
status: generated
---

# Work with release prep

Use release prep when you need to validate code quality, test coverage, and documentation completeness before releasing a new version.

## Prerequisites

- Access to the project source code
- Familiarity with the files under src/attune/workflows/release_prep.py

## Steps

1. **Understand the class hierarchy.**
   Read the interfaces to see how release prep
   is structured before extending or modifying.
   The key classes are:
   - `ReleasePreparationWorkflow` in `src/attune/workflows/release_prep.py` — coordinates pre-release quality gates using Agent SDK subagents
   - `ReleaseAgent` in `src/attune/agents/release/base_agent.py` — provides progressive tier escalation from CHEAP to CAPABLE to PREMIUM models
   - `TestCoverageAgent` in `src/attune/agents/release/coverage_agent.py` — executes pytest with coverage reporting and parses results
   - `DocumentationAgent` in `src/attune/agents/release/documentation_agent.py` — validates docstring coverage, README currency, and CHANGELOG presence
   - `CodeQualityAgent` in `src/attune/agents/release/quality_agent.py` — runs ruff linting and checks type hints and code complexity
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
