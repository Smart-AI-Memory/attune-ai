---
type: troubleshooting
feature: release-prep
depth: troubleshooting
generated_at: 2026-04-14T14:50:41.046311+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Troubleshoot release prep

## Before you start

The release preparation workflow runs quality gates through specialized agents that check test coverage, documentation, code quality, and security. Issues typically stem from agent failures, quality gate threshold mismatches, or Redis connectivity problems.

## Symptom table

| If you observe | Check |
|----------------|-------|
| `ReleaseReadinessReport.approved = False` | Quality gate thresholds in the failing `QualityGate` objects |
| Agent timeout or Redis connection errors | Redis connectivity and the `redis_url` parameter |
| `TestCoverageAgent` fails with "No coverage data" | Whether `pytest --cov` runs successfully in your codebase |
| `DocumentationAgent` reports missing files | Presence of README.md and CHANGELOG files in the project root |
| `CodeQualityAgent` exits with non-zero status | Ruff configuration and whether code passes `ruff check` |

## Step-by-step diagnosis

1. **Run a single agent in isolation.**
   Test individual agents before diagnosing the full workflow. Create a minimal reproduction:
   ```python
   from attune.agents.release.coverage_agent import TestCoverageAgent
   agent = TestCoverageAgent()
   result = agent.process('.')
   print(f"Success: {result.success}, Findings: {result.findings}")
   ```

2. **Check quality gate configuration.**
   Examine the thresholds passed to `ReleasePrepTeam`. Default gates may be too strict for your project:
   ```python
   team = ReleasePrepTeam(quality_gates={
       'test_coverage': {'threshold': 80.0},  # Lower if needed
       'documentation': {'threshold': 90.0}
   })
   ```

3. **Verify external tool dependencies.**
   Each agent depends on external tools that must work independently:
   - `TestCoverageAgent`: Run `pytest --cov=. --cov-report=term` manually
   - `CodeQualityAgent`: Run `ruff check .` and confirm it exits cleanly
   - `DocumentationAgent`: Verify README.md and CHANGELOG files exist

4. **Enable Redis state inspection.**
   If using Redis for agent state, connect directly to examine stored data:
   ```python
   import redis
   client = redis.from_url("your_redis_url")
   keys = client.keys("release_agent:*")
   ```

5. **Check agent tier escalation.**
   Agents escalate from CHEAP to CAPABLE to PREMIUM tiers. Verify the escalation logic in `ReleaseAgent.process()` if agents seem stuck or skip tiers unexpectedly.

## Common fixes

- **Lower quality gate thresholds.** If `ReleaseReadinessReport.approved = False` due to marginally failing gates, adjust thresholds when initializing `ReleasePrepTeam`:
  ```python
  gates = {'test_coverage': {'threshold': 75.0}}  # Down from default 90%
  team = ReleasePrepTeam(quality_gates=gates)
  ```

- **Install missing test dependencies.** `TestCoverageAgent` requires pytest and coverage:
  ```bash
  pip install pytest pytest-cov
  ```

- **Fix Ruff configuration conflicts.** If `CodeQualityAgent` fails, check for conflicting ruff settings:
  ```bash
  ruff check --show-files  # See which config files ruff uses
  ```

- **Create missing documentation files.** `DocumentationAgent` expects standard files:
  ```bash
  touch README.md CHANGELOG.md
  ```

- **Configure Redis connection.** For distributed agent execution, ensure Redis is accessible:
  ```python
  team = ReleasePrepTeam(redis_url="redis://localhost:6379/0")
  ```

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
