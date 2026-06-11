---
type: concept
name: release-prep-concept
feature: release-prep
depth: concept
generated_at: 2026-06-11T04:39:32.868111+00:00
source_hash: b484e3b8f8e27e1e37d71dd39e93de2e14c056d5969f51d404e9b11858bd81b7
status: generated
scaffold_hash: 358b98c551538d98776b2cdd99b8b946240628c170cf8b124e5c5918e6e3e960
---

# Release Prep

Release prep is a multi-agent pipeline that fans four specialist agents out across your codebase in parallel, then synthesizes their findings into a single go/no-go `ReleaseReadinessReport`.

## Agent coordination model

`ReleasePrepTeam` orchestrates the pipeline. When you call `assess_readiness(codebase_path='.')`, it dispatches four agents simultaneously:

- **`TestCoverageAgent`** — runs `pytest --cov` and parses the coverage report.
- **`DocumentationAgent`** — checks docstring coverage, README currency, and CHANGELOG presence.
- **`CodeQualityAgent`** — runs `ruff`, checks type hints, and measures complexity.
- **`SecurityAuditorAgent`** — scans for vulnerabilities, outdated dependencies, and secret leaks.

All four extend `ReleaseAgent`, which handles *progressive tier escalation*: each check begins at the `CHEAP` model tier. If the agent's `confidence` falls below an internal threshold, it re-runs at `CAPABLE`, then `PREMIUM` if confidence is still insufficient. The resulting `ReleaseAgentResult` records `tier_used`, `escalated`, `score`, `confidence`, and `execution_time_ms`, so you can see exactly how each agent reached its conclusion.

Each agent result is then evaluated against a `QualityGate`. A gate compares a named `threshold` against the agent's measured `actual` value. Gates where `critical` is `True` become blockers if they fail; non-critical gates produce warnings instead. You configure thresholds by passing a `quality_gates` dict to `ReleasePrepTeam(quality_gates={...})`.

## Release readiness report

`assess_readiness()` returns a `ReleaseReadinessReport` that aggregates every agent's findings:

| Field | What it tells you |
|-------|-------------------|
| `approved` | `True` if all critical quality gates passed |
| `confidence` | Overall confidence level string |
| `quality_gates` | Each gate's `threshold`, `actual`, and `passed` values |
| `blockers` | Issues that must be resolved before release |
| `warnings` | Non-blocking issues worth addressing |
| `total_cost` | Cumulative model spend across all agents |

Call `report.format_console_output()` for a human-readable summary, or `report.to_dict()` to serialize the report for CI artifacts or downstream tooling.

## Integration points

Three entry points expose release prep depending on your context:

| Entry point | When to use it |
|-------------|----------------|
| `ReleasePrepTeam.assess_readiness(codebase_path='.')` | Direct Python — use this when scripting release automation |
| `ReleasePrepTeamWorkflow.execute(path='.')` | Workflow runner — integrates with the CLI registry; `run_stage` lets you control the model tier per stage |
| `ReleasePreparationWorkflow.execute(**kwargs)` | Standalone workflow registered under `workflows.release_prep` |

After `assess_readiness()` returns, `ReleasePrepTeam.get_total_cost()` gives you the aggregate model cost independently of the report if you need it separately.
