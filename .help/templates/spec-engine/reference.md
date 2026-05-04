---
type: reference
feature: spec-engine
depth: reference
generated_at: 2026-05-04T02:39:26.921119+00:00
source_hash: dfb05ee79541939dac0529f016b44e21b04ef77d58372da1d6d5b857d97ef4d0
status: generated
---

# Spec Engine reference

Execute spec-driven development workflows with task orchestration, quality gates, and state persistence.

## Classes

| Class | Description |
|-------|-------------|
| `TaskResult` | Result of executing a single pipeline task |
| `PipelineResult` | Aggregated result from a full pipeline run |
| `PipelineOrchestrator` | Executes tasks from an XML spec with quality gates |
| `SpecState` | Execution state for a spec plan |

### TaskResult

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `task_id` | `str` | | Task identifier |
| `task_name` | `str` | | Task display name |
| `executed` | `bool` | `False` | Whether the task ran |
| `quality_gate_passed` | `bool | None` | `None` | Quality gate result |
| `tests_passed` | `bool | None` | `None` | Test validation result |
| `simplified` | `bool` | `False` | Whether task was simplified |
| `gate_details` | `dict | None` | `None` | Quality gate diagnostic data |
| `gate_score` | `float | None` | `None` | Quality gate numeric score |
| `error` | `str | None` | `None` | Error message if task failed |
| `cost` | `float` | `0.0` | Execution cost |

| Property | Type | Description |
|----------|------|-------------|
| `severity` | `str` | Classify gate result severity |

### PipelineResult

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `spec_path` | `str` | | Path to the executed plan file |
| `tasks` | `list[TaskResult]` | `[]` | Results from each executed task |
| `total_cost` | `float` | `0.0` | Total execution cost |
| `duration_ms` | `int` | `0` | Total execution time in milliseconds |

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Whether all tasks executed and passed gates |
| `summary` | `str` | Human-readable summary of the pipeline run |

### PipelineOrchestrator

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `spec_path: str, *, skip_gates: bool = False, skip_tests: bool = False, skip_simplify: bool = False` | `None` | Initialize orchestrator with plan file |
| `run_all` | `*, on_task_complete: TaskCallback | None = None, skip_task_ids: set[str] | None = None` | `PipelineResult` | Execute all tasks in the spec |
| `run_gates_for_task` | `task: DecomposedTask` | `TaskResult` | Run quality gates for a single task |

### SpecState

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `plan_path` | `str` | | Path to the plan file |
| `completed` | `list[str]` | `[]` | Task IDs that have completed |
| `current` | `str | None` | `None` | Currently executing task ID |
| `auto_run` | `bool` | `False` | Whether to auto-approve remaining tasks |
| `last_updated` | `str` | `datetime.now(timezone.utc).isoformat()` | ISO timestamp of last state change |

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | | `dict` | Convert state to dictionary representation |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `read_spec` | `plan_path: str` | `list[DecomposedTask]` | Read a plan file and extract XML task blocks |
| `present_tasks` | `tasks: list[DecomposedTask], state: SpecState | None = None` | `str` | Format all tasks as a human-readable markdown table |
| `present_task_detail` | `task: DecomposedTask` | `str` | Format a single task with full details |
| `present_task_result` | `task: DecomposedTask, gate_result: TaskResult` | `str` | Format a task's execution result with quality gate status |
| `format_progress_bar` | `completed: int, total: int` | `str` | Visual progress indicator for task execution |
| `get_pending_tasks` | `tasks: list[DecomposedTask], state: SpecState` | `list[DecomposedTask]` | Filter tasks to only those not yet completed |
| `execute_with_approval` | `spec_path: str, on_task_complete: object, *, skip_gates: bool = False, skip_tests: bool = False, skip_simplify: bool = False` | `PipelineResult` | Execute a spec with per-task approval |
| `load_state` | `plan_path: str` | `SpecState | None` | Read spec-state from an HTML comment in a plan file |
| `save_state` | `state: SpecState` | `None` | Write or update the spec-state comment in a plan file |
| `clear_state` | `plan_path: str` | `None` | Remove the spec-state comment from a plan file |
| `find_resumable_plans` | | | Find plan files with incomplete execution state |

### Raises

| Function | Exception | Message |
|----------|-----------|---------|
| `read_spec` | `ValueError` | `'plan_path must be a non-empty string'` |
| `read_spec` | `FileNotFoundError` | `'Plan file not found: {...}'` |
