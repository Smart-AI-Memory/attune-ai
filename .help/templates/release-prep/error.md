---
type: error
name: release-prep-error
feature: release-prep
depth: error
generated_at: 2026-06-22T10:13:38.223145+00:00
source_hash: 2e9628fb196173f4048d6aab29c024a2318abaeea4420bd4865253bdc1d46702
status: generated
---

# Release Prep errors

Release prep errors fall into two categories: failures during agent execution (a subagent like `TestCoverageAgent` or `CodeQualityAgent` cannot complete its check) and quality gate failures (an agent completes successfully but `ReleaseReadinessReport.approved` is `False` because one or more `QualityGate` thresholds were not met). The sections below help you tell them apart.

## Common error signatures

| Symptom | Likely cause |
|---------|--------------|
| `ReleaseAgentResult.success` is `False` for a specific agent | The agent raised an exception internally; inspect `ReleaseAgentResult.findings` for the error detail |
| `ReleaseReadinessReport.approved` is `False` with entries in `blockers` | At least one `QualityGate` with `critical=True` has `passed=False` — `QualityGate.actual` is below `QualityGate.threshold` |
| `ReleasePrepTeam.assess_readiness()` raises during startup | `redis_url` is set but Redis is unreachable, or `quality_gates` contains a key that no agent recognises |
| `ReleasePrepTeamWorkflow.execute()` raises before any agent runs | `path` does not point to a valid codebase directory |
| `TestCoverageAgent` fails | `pytest --cov` is not installed or no test files are found at `codebase_path` |
| `CodeQualityAgent` fails | `ruff` is not installed or the project has no Python source files at `codebase_path` |
| `DocumentationAgent` fails | `CHANGELOG` file is absent and the agent cannot locate a README at `codebase_path` |
| `ReleaseAgent.process()` returns with `escalated=True` and `success=False` | All three tiers (CHEAP → CAPABLE → PREMIUM) were tried and none produced a confident result |

## Where errors originate

Different failure modes surface in different classes. Match the symptom to the class before walking the call stack further.

- **`ReleasePrepTeam.assess_readiness()`** — top-level entry point; collects `ReleaseAgentResult` objects from all subagents and assembles the `ReleaseReadinessReport`. If this raises, check connectivity (Redis) and whether `codebase_path` is readable.
- **`ReleasePrepTeamWorkflow.execute()`** — workflow wrapper around `ReleasePrepTeam`; validates `path` and `quality_gates` before delegating. Errors here usually mean a misconfigured `quality_gates` dict or an invalid `path` argument.
- **`ReleaseAgent.process()`** — base agent that drives tier escalation (CHEAP → CAPABLE → PREMIUM). When `escalated=True` in the returned `ReleaseAgentResult`, the agent exhausted all tiers.
- **`TestCoverageAgent`** — calls `pytest --cov` as a subprocess; fails if pytest or the coverage plugin is missing.
- **`CodeQualityAgent`** — calls `ruff` as a subprocess; fails if ruff is not on `PATH`.
- **`DocumentationAgent`** — inspects docstring coverage, README currency, and CHANGELOG presence; fails if expected files are missing.
- **`SecurityAuditorAgent`** — scans for vulnerabilities and secret leaks; may fail if required scanning tools are unavailable.

## How to diagnose

1. **Check `ReleaseReadinessReport` fields first.** Call `report.format_console_output()` or `report.to_dict()` to see the full picture: `approved`, `blockers`, `warnings`, each `QualityGate.passed` / `QualityGate.actual` / `QualityGate.threshold`, and each `ReleaseAgentResult.success`. This tells you whether an agent crashed or simply found a failing gate.

2. **Distinguish a gate failure from an agent failure.** If `ReleaseReadinessReport.approved` is `False` but every `ReleaseAgentResult.success` is `True`, the problem is a quality gate threshold, not a code error — look at `QualityGate.actual` vs `QualityGate.threshold` for each gate where `passed=False`. If any `ReleaseAgentResult.success` is `False`, an agent itself failed; check that result's `findings` dict for the underlying exception or subprocess error.

3. **Identify which agent failed.** Match `ReleaseAgentResult.agent_id` and `ReleaseAgentResult.agent_role` to the agent class (`TestCoverageAgent`, `CodeQualityAgent`, `DocumentationAgent`, `SecurityAuditorAgent`). Each agent runs a specific external tool — confirm that tool is installed and accessible from the working directory.

4. **Check for tier escalation.** If `ReleaseAgentResult.escalated` is `True`, `ReleaseAgent.process()` tried every model tier without reaching sufficient confidence. This usually indicates an ambiguous or incomplete codebase state rather than a tool failure.

5. **Verify `quality_gates` configuration.** `ReleasePrepTeam` and `ReleasePrepTeamWorkflow` both accept a `quality_gates` dict. A threshold of `0.0` means the gate always passes; a threshold higher than any achievable `actual` value means it always blocks. Print your `quality_gates` dict and compare each key against the `QualityGate.name` values in the report.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
