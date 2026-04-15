---
type: error
feature: release-prep
depth: error
generated_at: 2026-04-14T14:50:08.284400+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release Prep errors

This page covers failures in the release preparation workflow, which runs automated quality gates before publishing a release. These errors typically occur during code quality checks, test coverage analysis, documentation validation, or security audits.

## Common error signatures

- `subprocess.CalledProcessError` when pytest, ruff, or other tools fail
- `FileNotFoundError` when expected files like CHANGELOG.md or README.md are missing
- `ValueError` when quality gate thresholds are not met (e.g., test coverage too low)
- `redis.ConnectionError` when agent state storage is unavailable
- `AgentExecutionError` when individual release agents exceed time limits or fail to escalate properly
- `WorkflowResult` with `success=False` when overall release readiness assessment fails

## Where errors originate

Release prep errors typically start in these components. Check the method that matches your observed symptom:

- `ReleasePreparationWorkflow.execute()` — Overall workflow orchestration and subagent coordination
- `ReleasePrepTeam.assess_readiness()` — Parallel execution of release agents and report generation
- `ReleaseAgent.process()` — Base agent processing with tier escalation (CHEAP → CAPABLE → PREMIUM)
- `TestCoverageAgent` — Running `pytest --cov` and parsing coverage reports
- `DocumentationAgent` — Validating docstring coverage, README currency, and CHANGELOG presence
- `CodeQualityAgent` — Running ruff checks and analyzing type hints/complexity

## How to diagnose

1. **Check the release readiness report.** If `ReleasePrepTeam.assess_readiness()` completes, examine the `ReleaseReadinessReport.blockers` list and failed `QualityGate` entries. These pinpoint which specific checks failed and why.

2. **Verify tool dependencies.** Most failures stem from missing or misconfigured external tools. Ensure pytest, ruff, and coverage tools are installed and accessible in your environment.

3. **Examine agent escalation.** If a `ReleaseAgent` shows `escalated=True` but still fails, the issue may be with tier configuration or model availability. Check that higher-tier models (CAPABLE, PREMIUM) are properly configured.

4. **Validate file structure.** Documentation and changelog agents expect specific files (README.md, CHANGELOG.md) in standard locations. Missing files trigger `FileNotFoundError` or cause quality gates to fail.

5. **Check Redis connectivity.** If using Redis for agent state storage, connection failures manifest as `redis.ConnectionError`. The agents fall back to in-memory storage but may lose state between runs.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
