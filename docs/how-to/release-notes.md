# Release Notes

## Quickstart

Draft release notes for a project and print the result.
`ReleasePreparationWorkflow.execute` is an async coroutine, so drive
it with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".")

    print(result.success)          # True on a completed run
    print(result.summary)          # readiness score + go/no-go
    print(result.final_output)     # the synthesized report + changelog


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path=".")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the fullest
treatment.

## Tasks

### Draft release notes from the CLI

**Goal:** draft a changelog and get a go/no-go recommendation without
writing any Python.

**Steps:**

```bash
# Default depth (standard) at the project root:
attune workflow run release-notes --path .

# Deep advisory, JSON output:
attune workflow run release-notes --path . --depth deep --json
```

**Verify:** the slug is `release-notes`. `--path` / `-p` defaults to
the current directory; `--depth` accepts `quick`, `standard`, or
`deep`; `--json` / `-j` emits machine-readable output. Use `attune
workflow info release-notes` to confirm registration. The report
includes a readiness score, the drafted changelog, and prioritized
next steps — this is advice, not a gate.

### Draft release notes from Python

**Goal:** wire the advisory into a release hook or pipeline and act on
the result.

**Steps:**

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".", depth="deep")

    if not result.success:
        print("advisory failed:", result.error)
        return

    print(result.final_output)     # synthesized report + changelog
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed run
returns `success=True` with the report in `final_output`; a failure
returns `success=False` with a populated `error`. `metadata` echoes
the `path`, `depth`, and `max_turns`.

### Keep the advisory cheap

**Goal:** run the advisory at the lowest cost.

**Steps:**

```python
import asyncio

from attune.workflows import ReleasePreparationWorkflow


async def main() -> None:
    workflow = ReleasePreparationWorkflow()
    result = await workflow.execute(path=".", depth="quick")
    print(result.summary)


asyncio.run(main())
```

**Verify:** `quick` uses the smallest agent-turn budget (10) and the
lowest cap ($2). To let a deep pre-release run finish without a cap,
export `ATTUNE_MAX_BUDGET_USD=0`. Subscription users pay no
per-request cost regardless.

## Reference

Release-notes' public surface is the `ReleasePreparationWorkflow`
class, re-exported from `attune.workflows`. `WorkflowResult` comes
from `attune.workflows` as well.

### `ReleasePreparationWorkflow` — `attune.workflows.release_prep`

| Symbol | Purpose |
|--------|---------|
| `ReleasePreparationWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `ReleasePreparationWorkflow.execute(**kwargs)` | **Async.** Draft release notes + advisory. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). Returns a `WorkflowResult`. |
| `ReleasePreparationWorkflow.name` | The registered slug, `"release-notes"`. |
| `ReleasePreparationWorkflow.stages` | `["agent-prep"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → turns and budget

| Depth | Max turns | Budget cap | Use when |
|-------|-----------|------------|----------|
| `quick` | 10 | $2 | A fast pass for an early read. |
| `standard` | 20 | $10 | The default — balanced coverage and cost. |
| `deep` | 40 | $25 | The fullest treatment before a major release. |

### The four subagents

| Subagent | Role |
|----------|------|
| `health-checker` | Runs tests, checks dependency/lock status, verifies CI. |
| `security-scanner` | Flags vulnerabilities, secrets, eval/exec, path traversal. |
| `changelog-generator` | Drafts a Keep a Changelog section from `git log`. |
| `release-assessor` | Judges overall readiness and gives a go/no-go. |

### `WorkflowResult` fields read after a run

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the run completed. |
| `final_output` | `Any` | The synthesized report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Readiness score + go/no-go overview. |
| `suggestions` | `list[NextAction]` | Prioritized next steps, including blockers. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, and `max_turns`; carries SDK error fields on failure. |
| `error` | `str \| None` | Failure reason. (`error_type` and `transient` exist on `WorkflowResult` but this workflow's failure path leaves them unset.) |

### Entry points

| Surface | Invocation |
|---------|------------|
| MCP tool | `release_notes(path=<p>)` — changelog draft + go/no-go advisory (reached via the `/release` skill). |
| CLI | `attune workflow run release-notes --path <p> [--depth quick\|standard\|deep] [--json]`. |
| Python | `await ReleasePreparationWorkflow().execute(path=<p>, depth=<d>)`. |

<!-- attune-generated: source_hash=3bee45ea7e9bedc48f6fdc7744f2c05ff0fd177419dba9606233f53b10818ab6 feature=release-notes kind=how-to generated_at=2026-06-23 -->
