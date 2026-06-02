---
type: comparison
name: release-prep-comparison
feature: release-prep
depth: comparison
generated_at: 2026-06-02T10:56:02.730335+00:00
source_hash: 154aea0206f2809204a60d671b6411b36f1e98b1dd2cd5158175147523b39cc2
status: generated
---

# Comparison: Release Prep Entry Points

## Context

Release prep exposes three distinct entry points for running a pre-release quality gate across health, security, changelog, and code quality checks. Choosing the wrong one adds unnecessary complexity or costs you control over quality gate thresholds. This page helps you pick the right one.

## The three options at a glance

| | `ReleasePrepTeam` | `ReleasePrepTeamWorkflow` | `ReleasePreparationWorkflow` |
|---|---|---|---|
| **Import from** | `release` | `release` | `workflows.release_prep` |
| **Primary method** | `assess_readiness(codebase_path)` | `execute(path, context)` | `execute(**kwargs)` |
| **Custom quality gates** | `dict[str, Any]` via `__init__` | `dict[str, float]` via `__init__` | Not exposed |
| **Stage-level control** | No | `run_stage(stage_name, tier, input_data)` | No |
| **Cost tracking** | `get_total_cost() -> float` | Via `ReleaseReadinessReport.total_cost` | Via `WorkflowResult` |
| **Redis state store** | Optional `redis_url` | Inherited via `**kwargs` | Not exposed |
| **Returns** | `ReleaseReadinessReport` | `ReleaseReadinessReport` | `WorkflowResult` |
| **Best for** | Direct programmatic use | CLI registry integration | One-shot workflow invocation |

## Feature-by-feature breakdown

### Quality gate configuration

`ReleasePrepTeam` and `ReleasePrepTeamWorkflow` both accept custom quality gates at construction time. `ReleasePrepTeam` accepts `dict[str, Any]`, giving you the most flexibility — you can pass full `QualityGate` objects with `name`, `threshold`, `critical`, and `message` fields. `ReleasePrepTeamWorkflow` narrows this to `dict[str, float]`, which is enough for threshold-only overrides but won't let you mark a gate as non-critical or attach a custom message.

`ReleasePreparationWorkflow` does not expose quality gate configuration at all. It runs with whatever defaults are baked in.

### Output format

All three paths ultimately produce data that maps to `ReleaseReadinessReport`, which carries `approved`, `confidence`, `quality_gates`, `agent_results`, `blockers`, `warnings`, `summary`, `total_duration`, and `total_cost`. When you use `ReleasePrepTeam` or `ReleasePrepTeamWorkflow` directly, you get a `ReleaseReadinessReport` back and can call `format_console_output()` or `to_dict()` on it immediately.

`ReleasePreparationWorkflow` wraps results in a `WorkflowResult`, so you go through an extra layer before reaching the same data.

### Agent visibility

Each entry point runs the same four specialized agents — `CodeQualityAgent`, `TestCoverageAgent`, `DocumentationAgent`, and `SecurityAuditorAgent` — but only `ReleasePrepTeamWorkflow` lets you interact with the execution model directly via `run_stage(stage_name, tier, input_data)`. This matters if you need to re-run a single stage at a different `Tier` without re-running the full assessment, or if you want to inject custom input data for a specific stage.

### Cost tracking

`ReleasePrepTeam` exposes `get_total_cost() -> float` as a dedicated method, making it easy to check spend after `assess_readiness()` returns. `ReleasePrepTeamWorkflow` surfaces the same figure through `ReleaseReadinessReport.total_cost`. `ReleasePreparationWorkflow` folds cost into the broader `WorkflowResult` — accessible, but not as direct.

## When NOT to use release prep directly

- **Exploratory or one-off checks**: Running `/release-prep check` from the skill is faster than wiring up any of these classes for a single assessment.
- **You only need one agent's output**: Instantiate `CodeQualityAgent`, `TestCoverageAgent`, `DocumentationAgent`, or `SecurityAuditorAgent` directly via `ReleaseAgent.process(codebase_path)`. Invoking the full team for a single domain check adds unnecessary cost and latency.
- **You need a check type the public API does not cover**: None of these entry points expose extension hooks for custom agent types. If your release gate requires domain logic outside the four built-in agents, file a feature request rather than patching internals.

## Use X when...

**Use `ReleasePrepTeam`** when you are writing application code that drives release gating directly. It gives you the cleanest interface (`assess_readiness()` in, `ReleaseReadinessReport` out), full quality gate control via `dict[str, Any]`, and an explicit `get_total_cost()` call for spend tracking. This is the right default for new integrations.

**Use `ReleasePrepTeamWorkflow`** when you need stage-level control — specifically, the ability to call `run_stage(stage_name, tier, input_data)` to re-run or customize individual stages — or when your code integrates with the CLI registry that expects the workflow interface. The `dict[str, float]` gate format is a minor constraint; if you need full `QualityGate` objects, prefer `ReleasePrepTeam`.

**Use `ReleasePreparationWorkflow`** only when the rest of your pipeline already expects a `WorkflowResult` and you have no need to customize quality gates or inspect per-stage execution. It is the least flexible of the three but requires the least setup.

## Source files

- `src/attune/workflows/release_prep.py`
- `src/attune/agents/release/**`

**Tags:** `release`, `publishing`, `quality`
