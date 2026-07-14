# Code Quality

## Quickstart

Review a directory and print the consolidated report.
`CodeReviewWorkflow.execute` is an async coroutine, so drive it
with `asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()
    result = await workflow.execute(path="src/", depth="standard")

    print(result.success)          # True on a completed review
    print(result.summary)          # short health summary
    print(result.final_output)     # the full consolidated report


asyncio.run(main())
```

`depth` defaults to `"standard"`, so `execute(path="src/")` is
equivalent. Use `"quick"` for a fast pass or `"deep"` for the
fullest review.

## Tasks

### Review a path from the CLI

**Goal:** run a one-off review over a directory without writing any
Python.

**Steps:**

```bash
# Default depth (standard) over a directory:
attune workflow run code-review --path src/

# Deep review, JSON output for a pre-merge gate:
attune workflow run code-review --path src/ --depth deep --json
```

**Verify:** the slug is `code-review` (not `code-quality`).
`--path` / `-p` defaults to the current directory; `--depth`
accepts `quick`, `standard`, or `deep`; `--json` / `-j` emits
machine-readable output. Use `attune workflow info code-review` to
confirm registration and `attune workflow list` to see it alongside
the other workflows.

### Call the review from Python

**Goal:** drive code-quality from a hook or pre-merge gate and act
on the result.

**Steps:**

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()
    result = await workflow.execute(path="src/api/", depth="deep")

    if not result.success:
        print("review failed:", result.error)
        return

    print(result.final_output)
    for action in result.suggestions:
        print(action)


asyncio.run(main())
```

**Verify:** `execute` is a coroutine — `await` it. A completed
review returns `success=True` with the report in `final_output`; a
failure returns `success=False` with a populated `error` and
`error_type`. `metadata` echoes the `path`, `depth`, and
`max_turns`.

### Scope a review to a smaller area

**Goal:** keep a run fast and cheap by narrowing what it reads.

**Steps:**

```python
import asyncio

from attune.workflows import CodeReviewWorkflow


async def main() -> None:
    workflow = CodeReviewWorkflow()

    # A single subsystem, quick pass:
    result = await workflow.execute(path="src/auth/", depth="quick")
    print(result.final_output)


asyncio.run(main())
```

**Verify:** code-quality has no `focus` parameter, so the only
levers are `path` (point it at a narrower directory or file) and
`depth` (`quick` trims the agent-turn budget to 10). All four passes
still run over whatever `path` covers.

## Reference

Code-quality's public surface is the `CodeReviewWorkflow` class,
re-exported from `attune.workflows`. `WorkflowResult` comes from
`attune.workflows` as well.

### `CodeReviewWorkflow` — `attune.workflows.code_review`

| Symbol | Purpose |
|--------|---------|
| `CodeReviewWorkflow()` | Construct the workflow. Takes no special constructor arguments. |
| `CodeReviewWorkflow.execute(**kwargs)` | **Async.** Run the review. Honors `path` (str, required) and `depth` (`"quick"` / `"standard"` / `"deep"`, default `"standard"`). No `focus`. Returns a `WorkflowResult`. |
| `CodeReviewWorkflow.name` | The registered slug, `"code-review"`. |
| `CodeReviewWorkflow.stages` | `["agent-review"]`; the stage runs at the `CAPABLE` model tier. |

### Depth → agent-turn budget

| Depth | Max turns | Use when |
|-------|-----------|----------|
| `quick` | 10 | A fast pass on a small path. |
| `standard` | 20 | The default — balanced coverage and cost. |
| `deep` | 40 | The fullest review of a large or critical area. |

### The four passes

| Subagent | Domain |
|----------|--------|
| `security-reviewer` | eval/exec, injection, path traversal, secrets, auth. |
| `quality-reviewer` | Complexity, error handling, naming, duplication, test-coverage gaps. |
| `perf-reviewer` | N+1, unnecessary copies, blocking I/O in async, missing caching. |
| `architect-reviewer` | Coupling, SOLID, circular deps, API design, abstraction mismatches. |

### `WorkflowResult` fields read after a review

| Field | Type | Meaning |
|-------|------|---------|
| `success` | `bool` | Whether the review completed. |
| `final_output` | `Any` | The consolidated report — a serialized report when findings parse, else the raw markdown. |
| `summary` | `str \| None` | Short health summary. |
| `suggestions` | `list[NextAction]` | Prioritized next actions. |
| `cost_report` | `CostReport` | Cost / usage for the run. |
| `provider` | `str` | The provider that served the run (`"anthropic"`). |
| `metadata` | `dict` | Echoes `path`, `depth`, `max_turns`, and `subagent_transcripts`; carries SDK error fields on failure. |
| `error` / `error_type` | `str \| None` | Failure reason and category (`"config"` / `"runtime"` / `"provider"` / `"timeout"` / `"validation"`). |

### Entry points

| Surface | Invocation |
|---------|------------|
| Skill | `/code-quality` in a Claude Code conversation — routes by depth to `code_review` (quick), `code_review` + `bug_predict` (thorough), or `deep_review` (deep). |
| CLI | `attune workflow run code-review --path <p> [--depth quick\|standard\|deep] [--json]`. |
| MCP tool | `code_review` — one required `path` argument; runs at standard depth (the handler does not pass `depth`) and validates the path against the workspace root. |
| Python | `await CodeReviewWorkflow().execute(path=<p>, depth=<d>)`. |

<!-- attune-generated: source_hash=1cda16e2ee597c3fc3187497350da0cf77783f31c42c22e4652888adb60ca679 feature=code-quality kind=how-to generated_at=2026-07-14 -->
