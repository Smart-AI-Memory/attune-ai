# How to use the spec engine

Use this guide when you need to drive a spec plan programmatically — reading task blocks from a plan file, running tasks through quality gates, tracking state across sessions, and presenting results to users.

## Quick start

```python
from attune.pipeline import PipelineOrchestrator, PipelineResult
from attune.spec import load_state, find_resumable_plans

# Run all tasks in a plan with quality gates enabled
orchestrator = PipelineOrchestrator(".claude/plans/my-feature.md")
result: PipelineResult = orchestrator.run_all()

print(result.summary)   # Human-readable run summary
print(result.success)   # True if all tasks executed and passed gates
```

Running this produces a `PipelineResult` with per-task outcomes, total cost, and duration.

## Core API

### Pipeline execution

| Symbol | Purpose |
|--------|---------|
| `PipelineOrchestrator(spec_path, *, skip_gates, skip_tests, skip_simplify)` | Load a plan file and prepare tasks for execution with optional gate overrides |
| `PipelineOrchestrator.run_all(*, on_task_complete, skip_task_ids)` | Execute all tasks, firing an optional callback after each |
| `PipelineOrchestrator.run_gates_for_task(task)` | Run quality gates for a single `DecomposedTask` and return a `TaskResult` |
| `execute_with_approval(spec_path, on_task_complete, *, skip_gates, skip_tests, skip_simplify)` | Execute a spec with an interactive per-task approval loop |
| `read_spec(plan_path)` | Parse a plan file and extract its XML task blocks into `DecomposedTask` objects |

### State management

| Symbol | Purpose |
|--------|---------|
| `load_state(plan_path)` | Read a `SpecState` from the HTML comment embedded in a plan file; returns `None` if no state exists |
| `save_state(state)` | Write or update the spec-state comment in a plan file |
| `clear_state(plan_path)` | Remove the spec-state comment from a plan file |
| `find_resumable_plans(plans_dir)` | Return all `SpecState` objects from `.claude/plans/` that have incomplete execution |
| `get_pending_tasks(tasks, state)` | Filter a task list to those whose IDs are not in `state.completed` |

### Presentation

| Symbol | Purpose |
|--------|---------|
| `present_tasks(tasks, state)` | Format a task list as a markdown table, optionally annotated with completion state |
| `present_task_detail(task)` | Format a single task with its full acceptance criteria and metadata |
| `present_task_result(task, gate_result)` | Format execution output including quality gate status and score |
| `format_progress_bar(completed, total)` | Render a visual progress indicator for a running pipeline |

### Result fields

`TaskResult` fields you'll inspect most often:

| Field | Type | Meaning |
|-------|------|---------|
| `quality_gate_passed` | `bool \| None` | Gate outcome; `None` when gates were skipped |
| `tests_passed` | `bool \| None` | Test outcome; `None` when tests were skipped |
| `gate_score` | `float \| None` | Numeric quality score from the gate |
| `severity` | `str` (property) | Classified severity of the gate result |
| `error` | `str \| None` | Error message if the task failed to execute |
| `cost` | `float` | Cost attributed to this task |

`PipelineResult` top-level properties:

| Property | Type | Meaning |
|----------|------|---------|
| `success` | `bool` | `True` only when all tasks executed and passed gates |
| `summary` | `str` | Human-readable run summary |
| `total_cost` | `float` | Aggregated cost across all tasks |
| `duration_ms` | `int` | Wall-clock time for the full run |

## Integration patterns

### Resume an interrupted run

```python
from attune.pipeline import PipelineOrchestrator, read_spec
from attune.spec import load_state, get_pending_tasks, find_resumable_plans

# Discover plans that didn't finish
resumable = find_resumable_plans(".claude/plans")

for spec_state in resumable:
    tasks = read_spec(spec_state.plan_path)
    pending = get_pending_tasks(tasks, spec_state)

    if not pending:
        continue

    # Skip tasks already recorded in state
    completed_ids = set(spec_state.completed)
    orchestrator = PipelineOrchestrator(spec_state.plan_path)
    result = orchestrator.run_all(skip_task_ids=completed_ids)
    print(result.summary)
```

### Stream progress to a UI

```python
from attune.pipeline import PipelineOrchestrator, TaskResult
from attune.pipeline import PipelineResult
from attune.spec import present_task_result, format_progress_bar
from attune.pipeline import read_spec

plan_path = ".claude/plans/my-feature.md"
tasks = read_spec(plan_path)
total = len(tasks)
completed_count = 0

def on_task_complete(task, gate_result: TaskResult) -> None:
    global completed_count
    completed_count += 1
    print(format_progress_bar(completed_count, total))
    print(present_task_result(task, gate_result))

orchestrator = PipelineOrchestrator(plan_path)
result: PipelineResult = orchestrator.run_all(on_task_complete=on_task_complete)

if not result.success:
    failed = [t for t in result.tasks if not t.quality_gate_passed]
    for t in failed:
        print(f"FAILED [{t.severity}] {t.task_name}: {t.error}")
```

## See also

- `concepts/tool-spec.md` — the five phases of spec-driven development and what each phase produces
- `quickstarts/skill-spec.md` — interactive use via `/spec` in Claude Code

<!-- attune-generated: source_hash=f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337 feature=spec-engine kind=how-to generated_at=2026-06-02 -->
