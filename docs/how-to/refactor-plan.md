# Refactor Plan

## Quickstart

Analyze a directory and print the refactoring roadmap.
`RefactorPlanWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed analysis
    print(result.summary)          # short tech-debt summary
    print(result.final_output)     # the full roadmap


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest roadmap.

## Tasks

### Generate a roadmap from the CLI

**Goal:** produce a prioritized refactoring plan for a directory
without writing any Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run refactor-plan --path src/

# Deep analysis, JSON output for a report:
attune workflow run refactor-plan --path src/ --depth deep --json
```

**Verify:** the slug is `refactor-plan`. `--path` / `-p` defaults
to the current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use
`attune workflow info refactor-plan` to confirm registration.

### Call the planner from Python

**Goal:** drive refactor-plan from a hook or scheduled report and
act on the result.

**Steps:**

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/legacy/", depth="deep")

    if not result.success:
        print("analysis failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the roadmap in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope the analysis to a smaller area

**Goal:** keep a run fast and focused on the module you care about.

**Steps:**

```python
import asyncio

from attune.workflows import RefactorPlanWorkflow


async def main() -> None:
    workflow = RefactorPlanWorkflow()
    result = await workflow.execute(path="src/attune/config.py", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** refactor-plan has no `focus` parameter, so the levers
are `path` (point it at a narrower directory or file) and `depth`
(`quick` trims the agent-turn budget to 10). All three passes run
over whatever `path` covers.

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

<!-- attune-generated: source_hash=198d821e7ba1dffdfe00c207be171d13fcf198bedb8c0fd84f251e83f8015fbb feature=refactor-plan kind=how-to generated_at=2026-06-23 -->
