---
type: warning
feature: release-prep
depth: warning
generated_at: 2026-04-14T14:50:23.025644+00:00
source_hash: fe9ded2c56c77207b818a4bfa424bc8ad639e250941dae59bba6027c7ec2bb75
status: generated
---

# Release Prep cautions

## What to watch for

The release prep system coordinates multiple agents to assess code quality, test coverage, security, and documentation before release. Several aspects of this orchestration can fail silently or produce misleading results.

## Risk areas

### Tier escalation costs spiral without warning

The `ReleaseAgent` base class escalates from CHEAP → CAPABLE → PREMIUM tiers when lower tiers fail. A single flaky test or malformed file can trigger expensive premium-tier analysis across multiple agents simultaneously.

**Mitigation:** Monitor the `total_cost` field in `ReleaseReadinessReport` and set budget alerts. Review `escalated` flags in `ReleaseAgentResult` to identify agents that consistently require premium processing.

### Quality gates pass with misleading scores

`QualityGate` thresholds compare actual values against fixed limits, but the scoring doesn't account for test flakiness or partial coverage reports. A 95% test coverage score may include tests that only run in specific environments.

**Mitigation:** Examine the `findings` dictionary in each `ReleaseAgentResult` for details behind the scores. Don't rely solely on `QualityGate.passed` — check `confidence` levels and `message` fields for warnings about data quality.

### Parallel agent execution masks dependency failures

`ReleasePrepTeam` runs agents concurrently, but if one agent fails to install dependencies or access required tools (pytest, ruff, etc.), other agents may continue with stale or incomplete data.

**Mitigation:** Check that all `ReleaseAgentResult.success` values are `true` before trusting the overall report. Failed agents should block release approval regardless of other passing scores.

### Redis state corruption between runs

When Redis is enabled, agent state persists between workflow executions. Corrupted cache entries or stale findings from previous codebases can contaminate current assessments.

**Mitigation:** Use unique `agent_id` values when running multiple assessments and clear Redis state between different codebases. Monitor `execution_time_ms` — unusually fast results may indicate cached data instead of fresh analysis.

## How to avoid problems

1. **Run agents individually first.** Before using `ReleasePrepTeam`, test each agent type (`TestCoverageAgent`, `DocumentationAgent`, etc.) on your codebase to identify configuration issues early.

2. **Set conservative quality gates.** Start with lower thresholds in `quality_gates` and tighten them gradually as your codebase improves. Aggressive thresholds can create false negatives that bypass real issues.

3. **Validate tool availability.** Ensure pytest, ruff, and other external tools are installed and accessible from your execution environment before starting the workflow.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
