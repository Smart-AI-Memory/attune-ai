---
name: refactor-plan
source: content/features/refactor-plan.md
tags:
- refactor
- tech-debt
- complexity
type: reference
---

# Prioritize tech debt — scan for code smells and generate a refactoring roadmap

## Reference

Refactor-plan's public surface is the `RefactorPlanWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `RefactorPlanWorkflow` — `attune.workflows.refactor_plan`

| Symbol | Purpose |
|--------|---------|
| `RefactorPlanWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `RefactorPlanWorkflow.execute(**kwargs)` | **Async.** Run the analysis. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `RefactorPlanWorkflow.name` | The registered slug, `"refactor-plan"`. |
| `RefactorPlanWorkflow.stages` | `["agent-plan"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest roadmap of a large or legacy area. |

### The three passes

| Subagent | Domain |
|----------|--------|
| `debt-scanner` | Code smells, duplication, complex conditionals, dead code, long functions, deep nesting. |
| `impact-analyzer` | Test coverage, dependency chains, API-surface changes, downstream consumers. |
| `plan-generator` | Prioritized plan: effort (small/medium/large), risk (low/medium/high), benefit, order. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the analysis completed. |
| `final_output` | `Any` | The roadmap — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short tech-debt summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/refactor` in a Claude Code conversation — full analysis routes to refactor-plan; a complexity-only pass routes to simplify-code. |
| CLI | `attune workflow run refactor-plan --path <p> [--depth quick\|standard\|deep] [--json]`. |
| MCP tool | `refactor_plan` — optional `path` (defaults to the current directory), validated against the workspace root. |
| Python | `await RefactorPlanWorkflow().execute(path=<p>, depth=<d>)`. |
