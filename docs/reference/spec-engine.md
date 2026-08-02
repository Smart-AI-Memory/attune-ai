# Spec Engine

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

<!-- attune-generated: source_hash=0a9f094d0c1cb1edca272a7412ba50c3a59e4336596eb0a901aff5e6fc3b2d4b feature=spec-engine kind=reference generated_at=2026-08-02 -->
