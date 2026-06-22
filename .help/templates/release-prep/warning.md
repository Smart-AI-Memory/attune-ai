---
type: warning
name: release-prep-warning
feature: release-prep
depth: warning
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 2e9628fb196173f4048d6aab29c024a2318abaeea4420bd4865253bdc1d46702
status: generated
---

# Release Prep: What to Watch For

## Critical quality gates can block a release silently

`ReleasePrepTeam.assess_readiness()` evaluates each `QualityGate` against a `threshold` value. If `QualityGate.critical` is `True` and `QualityGate.passed` is `False`, the gate contributes a blocker to `ReleaseReadinessReport.blockers` and sets `ReleaseReadinessReport.approved` to `False`. If you pass custom `quality_gates` to `ReleasePrepTeam.__init__()` with thresholds that don't match your project's actual metrics, you can get a false GO or an unexplained NO-GO with no clear message in `ReleaseReadinessReport.warnings`.

**Mitigation:** After calling `assess_readiness()`, inspect `report.quality_gates` directly — check both `QualityGate.actual` and `QualityGate.threshold` for each gate before trusting the top-level `report.approved` field. Use `ReleaseReadinessReport.format_console_output()` to surface the full picture, not just the verdict.

## Tier escalation adds cost and latency you may not expect

`ReleaseAgent` escalates automatically through CHEAP → CAPABLE → PREMIUM tiers when confidence is low. Each `ReleaseAgentResult` records `tier_used`, `escalated`, `cost`, and `execution_time_ms`. Because `ReleasePrepTeam` runs agents in parallel, a single low-confidence result from `SecurityAuditorAgent` or `TestCoverageAgent` can trigger escalation on that agent without affecting others — but the cumulative cost across agents can be higher than expected for a routine check run.

**Mitigation:** Call `ReleasePrepTeam.get_total_cost()` after `assess_readiness()` completes. If cost is a concern, review `report.agent_results` and check `escalated` on each `ReleaseAgentResult` to identify which agents triggered escalation.

## `_run_command` output is consumed by agents, not returned to callers

`CodeQualityAgent` (runs `ruff`, checks type hints and complexity) and `TestCoverageAgent` (runs `pytest --cov`) both rely on `_run_command` internally. This helper is exported in `release.release_agents.__all__` but is a private implementation detail — its interface can change without notice. If you call it directly in tests or custom agents, a refactor can break your code without breaking the published API.

**Mitigation:** Depend only on the classes and functions listed in `release.__init__.__all__`: `ReleaseAgent`, `ReleasePrepTeam`, `ReleasePrepTeamWorkflow`, and `ReleaseReadinessReport`. Use `ReleaseAgent.process()` to run an individual agent rather than invoking `_run_command` directly.

## `DocumentationAgent` checks the CHANGELOG at assessment time

`DocumentationAgent` verifies docstring coverage, README currency, and CHANGELOG presence during the `assess_readiness()` call. If your CHANGELOG is updated after assessment starts — for example, by a parallel CI step — the result recorded in `ReleaseAgentResult.findings` reflects the file state at the moment the agent ran. Re-running `assess_readiness()` after all file changes are committed is the only way to get an accurate result.

**Mitigation:** Commit all documentation and CHANGELOG updates before calling `assess_readiness()`. Do not rely on a cached `ReleaseReadinessReport` across commits — the `timestamp` field shows when the report was generated.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
