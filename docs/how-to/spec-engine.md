# Spec Engine

## Quickstart

Run a spec plan end-to-end with quality gates from Python.
`PipelineOrchestrator.run_all` is an async coroutine, so drive it with
`asyncio.run` (or `await` it inside an existing event loop):

```python
import asyncio

from attune.pipeline import PipelineOrchestrator, PipelineResult


async def main() -> None:
    orchestrator = PipelineOrchestrator(".claude/plans/my-feature.md")
    result: PipelineResult = await orchestrator.run_all()
    print(result.summary)   # human-readable run summary
    print(result.success)   # True if all tasks executed and passed gates


asyncio.run(main())
```

`summary` and `success` are properties — read them, don't call them.
Running this produces a `PipelineResult` with per-task outcomes, total
cost, and duration.

To skip quality gates during a quick smoke test, pass
`skip_gates=True` to the constructor.

## Tasks

### Run a plan programmatically with progress output

**Goal:** read a plan, run every task through quality gates, print a
progress bar after each task, and exit non-zero if any gate failed.

**Steps:**

```python
import asyncio

from attune.pipeline import (
    PipelineOrchestrator,
    PipelineResult,
    TaskResult,
    read_spec,
)
from attune.spec import present_tasks, present_task_result, format_progress_bar, load_state

PLAN_PATH = ".claude/plans/my-feature.md"

tasks = read_spec(PLAN_PATH)
state = load_state(PLAN_PATH)          # None if no prior run exists
print(present_tasks(tasks, state))     # inspect the plan before running

completed_count = 0


async def on_task_complete(task, task_result: TaskResult) -> None:
    global completed_count
    completed_count += 1
    print(format_progress_bar(completed_count, len(tasks)))
    print(present_task_result(task, task_result))


async def main() -> None:
    orchestrator = PipelineOrchestrator(PLAN_PATH)
    result: PipelineResult = await orchestrator.run_all(
        on_task_complete=on_task_complete,
    )
    print(result.summary)
    if not result.success:
        raise SystemExit(1)


asyncio.run(main())
```

**Verify:** a fully passing run prints the summary and exits `0`.
`on_task_complete` is **awaited** after each task, so define it `async`
(`run_all` awaits it). The separation between reading (`read_spec`,
`present_tasks`) and running (`run_all`) is intentional — you can
inspect the full plan before committing to a run.

### Resume an interrupted run

**Goal:** find plans that didn't finish and continue them from where
they stopped.

**Steps:**

```python
import asyncio

from attune.pipeline import PipelineOrchestrator, read_spec
from attune.spec import get_pending_tasks, find_resumable_plans


async def main() -> None:
    resumable = find_resumable_plans(".claude/plans")
    for spec_state in resumable:
        tasks = read_spec(spec_state.plan_path)
        pending = get_pending_tasks(tasks, spec_state)
        if not pending:
            continue
        completed_ids = set(spec_state.completed)
        orchestrator = PipelineOrchestrator(spec_state.plan_path)
        result = await orchestrator.run_all(skip_task_ids=completed_ids)
        print(result.summary)


asyncio.run(main())
```

**Verify:** `get_pending_tasks` returns only the tasks whose IDs are
not in `SpecState.completed`. Passing those IDs as `skip_task_ids`
prevents re-running completed work.

### Run with per-task approval

**Goal:** pause after each task for human sign-off instead of running
the whole plan unattended.

**Steps:**

```python
import asyncio
from attune.spec.runner import execute_with_approval

async def main():
    result = await execute_with_approval(
        ".claude/plans/my-feature.md",
        on_task_complete,
        skip_gates=False,
        skip_tests=False,
        skip_simplify=False,
    )
    print(result.summary)

asyncio.run(main())
```

`execute_with_approval` is an async coroutine — `await` it (or drive
it with `asyncio.run`). It accepts the same `skip_gates`,
`skip_tests`, and `skip_simplify` flags as `PipelineOrchestrator`, and
returns the same `PipelineResult`. Flip `SpecState.auto_run = True` to
skip the per-task pause for the rest of the run.

**Verify:** the loop pauses after each task. An interrupted approval
run leaves a resumable `SpecState` in the plan file.

### Re-run a subset of tasks without restarting

**Goal:** re-run specific tasks without clearing state and reprocessing
the whole plan.

**Steps:** pass a `set[str]` of already-completed task IDs to
`run_all(skip_task_ids=...)` (inside an async context — `run_all` is a
coroutine):

```python
result = await orchestrator.run_all(skip_task_ids={"task-1", "task-2"})
```

**Verify:** skipping completed tasks preserves `SpecState.completed`
and keeps `total_cost` and `duration_ms` accurate in the final
`PipelineResult`. You are responsible for knowing which IDs to skip —
if a skipped task produced an artifact a later task depends on, check
`TaskResult.quality_gate_passed` and `gate_score` on the result before
assuming success.

## Reference

The spec engine exposes its public API through two packages:
`attune.pipeline` (execution) and `attune.spec` (state and
presentation). `execute_with_approval` lives in `attune.spec.runner`.

### Pipeline execution

| Symbol | Purpose |
|--------|---------|
| `PipelineOrchestrator(spec_path, *, skip_gates=False, skip_tests=False, skip_simplify=False)` | Load a plan file and prepare tasks for execution with optional gate overrides. |
| `PipelineOrchestrator.run_all(*, on_task_complete=None, skip_task_ids=None)` | **Async.** Execute all tasks, awaiting an optional async callback after each; returns a `PipelineResult`. The callback receives `(task, result)` and may return `"redo"` / `"auto"` / `"stop"` (or `None`/`"approve"` to continue). |
| `PipelineOrchestrator.run_gates_for_task(task)` | Run quality gates for a single `DecomposedTask` and return a `TaskResult`. |
| `read_spec(plan_path)` | Parse a plan file and extract its XML task blocks into `DecomposedTask` objects. Raises `FileNotFoundError` (missing file) or `ValueError` (empty path). |
| `execute_with_approval(spec_path, on_task_complete, *, skip_gates=False, skip_tests=False, skip_simplify=False)` | **Async.** Execute a spec with an interactive per-task approval loop. Import from `attune.spec.runner`. |

### State management

| Symbol | Purpose |
|--------|---------|
| `load_state(plan_path)` | Read a `SpecState` from the HTML comment embedded in a plan file; returns `None` if no state exists. |
| `save_state(state)` | Write or update the spec-state comment in a plan file. |
| `clear_state(plan_path)` | Remove the spec-state comment from a plan file. |
| `find_resumable_plans(plans_dir='.claude/plans')` | Return all `SpecState` objects whose plans have incomplete execution. |
| `get_pending_tasks(tasks, state)` | Filter a task list to those whose IDs are not in `state.completed`. |

### Presentation

| Symbol | Purpose |
|--------|---------|
| `present_tasks(tasks, state)` | Format a task list as a markdown table, optionally annotated with completion state. |
| `present_task_detail(task)` | Format a single task with its full acceptance criteria and metadata. |
| `present_task_result(task, gate_result)` | Format execution output including quality-gate status and score. |
| `format_progress_bar(completed, total)` | Render a visual progress indicator for a running pipeline. |

### Result fields

`TaskResult` fields you'll inspect most often:

| Field | Type | Meaning |
|-------|------|---------|
| `quality_gate_passed` | `bool \| None` | Gate outcome; `None` when gates were skipped. |
| `tests_passed` | `bool \| None` | Test outcome; `None` when tests were skipped. |
| `gate_score` | `float \| None` | Numeric quality score from the gate. |
| `severity` | `str` (property) | Classified severity of the gate result. |
| `error` | `str \| None` | Error message if the task failed to execute. |
| `cost` | `float` | Cost attributed to this task. |

`PipelineResult` top-level members:

| Member | Type | Meaning |
|--------|------|---------|
| `success` | `bool` (property) | `True` only when all tasks executed and passed gates. |
| `summary` | `str` (property) | Human-readable run summary. |
| `tasks` | `list[TaskResult]` | Per-task outcomes. |
| `total_cost` | `float` | Aggregated cost across all tasks. |
| `duration_ms` | `int` | Wall-clock time for the full run. |

### Example output

An approval run prints a progress bar, per-task gate results, and a
final summary:

```text
[========--] 4/5 tasks

✔ task-1  add-jwt-config          gate: passed  score: 92.0  cost: $0.003
✔ task-2  token-service           gate: passed  score: 87.5  cost: $0.004
✔ task-3  auth-middleware         gate: passed  score: 81.0  cost: $0.005
✔ task-4  wire-routes             gate: passed  score: 78.3  cost: $0.004
  task-5  integration-tests       pending

Pipeline complete: 4/5 tasks executed  total_cost: $0.016  duration: 18402ms
```

<!-- attune-generated: source_hash=ff80de2977562e5449b3d6a205f8f4f41d9c25948b7dc1477e103a101ac092bb feature=spec-engine kind=how-to generated_at=2026-08-02 -->
