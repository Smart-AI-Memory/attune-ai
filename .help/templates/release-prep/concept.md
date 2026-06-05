---
type: concept
name: release-prep-concept
feature: release-prep
depth: concept
generated_at: 2026-06-04T23:45:26.686528+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Release Prep

Release prep is an automated preflight system that runs a team of specialized agents across your codebase and produces a single `ReleaseReadinessReport` — an `approved` verdict plus structured `blockers`, `warnings`, and `quality_gates` — before you tag or publish.

## How the agent team works

`ReleasePrepTeam` coordinates four agents in parallel, each scanning a distinct domain. When you call `assess_readiness(codebase_path)`, every agent runs independently and returns a `ReleaseAgentResult`. The team then aggregates those results into a `ReleaseReadinessReport`.

| Agent | What it checks |
|---|---|
| `TestCoverageAgent` | Runs `pytest --cov` and parses the coverage report |
| `CodeQualityAgent` | Runs `ruff`, checks type hints and cyclomatic complexity |
| `DocumentationAgent` | Verifies docstring coverage, README currency, and CHANGELOG presence |
| `SecurityAuditorAgent` | Scans for vulnerabilities, secret leaks, and unsafe patterns |

Each agent extends `ReleaseAgent`, which implements a CHEAP → CAPABLE → PREMIUM tier escalation strategy. If a lower-cost model tier produces a low-confidence result (`escalated: True` in `ReleaseAgentResult`), the agent automatically retries at the next tier. This keeps routine runs fast while reserving expensive model calls for ambiguous findings.

## The readiness report

After all agents finish, the results collapse into a `ReleaseReadinessReport`:

- **`approved`** — `True` only when every critical `QualityGate` passes.
- **`quality_gates`** — a list of `QualityGate` entries, each comparing a measured `actual` value against a configurable `threshold`. Gates marked `critical: True` are blockers.
- **`blockers`** and **`warnings`** — human-readable strings surfacing what failed and what is advisory.
- **`confidence`** — an aggregate signal from the individual agent scores.
- **`total_cost`** and **`total_duration`** — telemetry you can retrieve via `ReleasePrepTeam.get_total_cost()` or read directly from the report fields.

Call `format_console_output()` on the report to render a readable summary, or `to_dict()` to serialize it for CI artifacts.

## Entry points

There are two ways to drive release prep depending on your context:

- **`ReleasePrepTeam.assess_readiness(codebase_path)`** — direct Python API. Instantiate with optional `quality_gates` thresholds and an optional `redis_url` for shared state, then call `assess_readiness`. Returns a `ReleaseReadinessReport`.
- **`ReleasePrepTeamWorkflow.execute(path, context)`** — workflow-registry wrapper used by the CLI. Accepts the same quality-gate configuration via the constructor and returns the same `ReleaseReadinessReport`. Internally it calls `run_stage` for each named stage at the appropriate `ModelTier`.

`ReleasePreparationWorkflow` (from `workflows.release_prep`) is the outermost shell that routes CLI invocations to `ReleasePrepTeamWorkflow` and wraps the result in a `WorkflowResult`.

## When release prep matters

Use release prep whenever the cost of a bad publish outweighs the time to run a check:

- Before bumping the version and opening a release PR
- After merging a large feature branch to main
- As the final gate in CI before tagging
- When you're unsure whether coverage, lint, or documentation has drifted since the last release

A single failing critical `QualityGate` — a coverage drop, a new CVE, a missing CHANGELOG entry — sets `approved: False` and populates `blockers` with the exact issue to fix before retrying.
