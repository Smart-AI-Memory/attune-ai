---
type: task
name: spec-engine-task
feature: spec-engine
depth: task
generated_at: 2026-08-02T18:06:04.708343+00:00
source_hash: ff80de2977562e5449b3d6a205f8f4f41d9c25948b7dc1477e103a101ac092bb
status: generated
---

# Spec Ladders — goal-driven spec development with approval loops

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
