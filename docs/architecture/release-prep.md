# Release Prep architecture

Pre-release quality gate — health checks, security audit, changelog, version bumps.

## Purpose

The release-prep subsystem coordinates a team of specialized agents that collectively assess whether a codebase is safe to ship. It runs static analysis, coverage measurement, documentation checks, and security audits in parallel, then aggregates results into a single `ReleaseReadinessReport` with a go/no-go verdict and per-gate pass/fail breakdown.

This subsystem is **not** responsible for executing the release itself — tagging, building distributions, or uploading to PyPI happen outside it. It also does not own CI orchestration; it produces a `ReleaseReadinessReport` that callers consume and act on.

## Key classes

| Class | Responsibility | File |
|-------|----------------|------|
| `ReleaseAgent` | Base class that runs a single check domain with CHEAP → CAPABLE → PREMIUM tier escalation; all specialist agents inherit from it. | `release/base_agent.py` |
| `TestCoverageAgent` | Invokes `pytest --cov` and parses the resulting coverage report into a `ReleaseAgentResult`. | `release/coverage_agent.py` |
| `DocumentationAgent` | Checks docstring coverage, README currency, and CHANGELOG presence. | `release/documentation_agent.py` |
| `CodeQualityAgent` | Runs `ruff`, checks type hint coverage, and measures cyclomatic complexity. | `release/quality_agent.py` |
| `SecurityAuditorAgent` | Runs `bandit` output analysis and classifies findings by severity. | `release/security_agent.py` |
| `ReleasePrepTeam` | Coordinates parallel execution of the four specialist agents and evaluates results against configured `QualityGate` thresholds. | `release/release_prep_team.py` |
| `ReleasePrepTeamWorkflow` | Thin wrapper around `ReleasePrepTeam` that registers it with the CLI workflow registry and exposes `execute()`. | `release/release_prep_team.py` |
| `ReleasePreparationWorkflow` | Alternative workflow entry point backed by four Agent SDK subagents (`health-checker`, `security-scanner`, `changelog-generator`, `release-assessor`). | `workflows/release_prep.py` |
| `Tier` | Enum of model tiers used by `ReleaseAgent` to control escalation cost. | `release/release_models.py` |
| `ReleaseAgentResult` | Dataclass capturing one agent's outcome: `score`, `confidence`, `findings`, `cost`, `escalated`, and `tier_used`. | `release/release_models.py` |
| `QualityGate` | Dataclass pairing a named threshold against the agent's `actual` score; `critical=True` gates block the release. | `release/release_models.py` |
| `ReleaseReadinessReport` | Aggregated verdict: `approved`, `confidence`, all `quality_gates`, all `agent_results`, `blockers`, `warnings`, and cumulative cost/duration. Serializes via `to_dict()` and `format_console_output()`. | `release/release_models.py` |

## Data flow

```
caller (CLI / workflow registry)
        |
        v
ReleasePrepTeamWorkflow.execute(path, context)
        |
        v
  ReleasePrepTeam.assess_readiness(codebase_path)
        |
        +--parallel--> TestCoverageAgent.process()     --> ReleaseAgentResult
        +--parallel--> DocumentationAgent.process()    --> ReleaseAgentResult
        +--parallel--> CodeQualityAgent.process()      --> ReleaseAgentResult
        +--parallel--> SecurityAuditorAgent.process()  --> ReleaseAgentResult
        |
        v
  evaluate each ReleaseAgentResult against QualityGate thresholds
        |
        v
  ReleaseReadinessReport
    .approved        (all critical gates passed)
    .quality_gates   (list[QualityGate] with .passed, .actual, .threshold)
    .agent_results   (list[ReleaseAgentResult])
    .blockers        (gates where critical=True and passed=False)
    .warnings        (gates where critical=False and passed=False)
    .total_cost      (sum of ReleaseAgentResult.cost)
        |
        v
caller receives ReleaseReadinessReport
  .to_dict()              -- machine-readable output
  .format_console_output() -- human-readable terminal report
```

`ReleasePreparationWorkflow` (in `workflows/release_prep.py`) is a parallel entry point that drives the same assessment through four Agent SDK subagents (`health-checker`, `security-scanner`, `changelog-generator`, `release-assessor`) rather than the direct Python agent classes. Both paths produce a `ReleaseReadinessReport`.

## Design decisions

- **Progressive tier escalation over fixed model selection.** Each `ReleaseAgent` starts at the cheapest model tier and escalates to CAPABLE or PREMIUM only when confidence is insufficient. This keeps routine checks fast and cheap while still reaching for more capable models on ambiguous findings. `ReleaseAgentResult.escalated` records whether a given run needed to escalate, which is useful for cost auditing.

- **`QualityGate` separates threshold configuration from agent logic.** Thresholds are injected into `ReleasePrepTeam.__init__` as a `dict[str, Any]` rather than hardcoded inside each agent. This means you can tighten or loosen gates per project without subclassing any agent. The `critical` field on `QualityGate` lets you distinguish blocking failures from advisory warnings without encoding that distinction in agent code.

- **Two workflow entry points with the same output type.** `ReleasePrepTeamWorkflow` calls the Python agent classes directly; `ReleasePreparationWorkflow` calls Agent SDK subagents. Both return `ReleaseReadinessReport`. The duplication is intentional: the SDK-backed workflow supports richer natural-language synthesis (guided by `_TASK_PROMPT_TEMPLATE`) while the direct workflow is faster and more deterministic for CI use.

## Extension points

- **Add a new check domain** by subclassing `ReleaseAgent` (from `release.base_agent`), implementing `process()` to return a `ReleaseAgentResult`, and registering an instance in `ReleasePrepTeam`. You get tier escalation and state-store wiring from the base class at no extra cost.

- **Adjust quality thresholds** without touching any agent code by passing a `quality_gates` dict to `ReleasePrepTeam.__init__` or `ReleasePrepTeamWorkflow.__init__`. Keys are gate names; values are threshold floats. Set `critical=False` on a `QualityGate` to demote a failure from blocker to warning.

- **Consume results programmatically** via `ReleaseReadinessReport.to_dict()` for JSON serialization or `format_console_output()` for terminal display. Both are stable public API (`release.__init__` exports `ReleaseReadinessReport` directly).

- **Track cumulative spend** across an assessment run by calling `ReleasePrepTeam.get_total_cost()` after `assess_readiness()` returns. Each `ReleaseAgentResult.cost` field records the per-agent share.

For usage questions, see `tasks/use-release-prep.md`.
