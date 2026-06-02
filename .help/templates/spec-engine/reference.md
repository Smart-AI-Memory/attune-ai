---
type: reference
name: spec-engine-reference
feature: spec-engine
depth: reference
generated_at: 2026-06-02T10:56:02.692805+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Spec Engine reference

Run spec-driven development pipelines with per-task approval loops and quality gates.

## Classes

| Class | Description |
|-------|-------------|
| `TaskResult` | Result of executing a single pipeline task. |
| `PipelineResult` | Aggregated result from a full pipeline run. |
| `PipelineOrchestrator` | Executes tasks from an XML spec with quality gates. |
| `SpecState` | Execution state for a spec plan. |

### TaskResult

`pipeline.models` · [dataclass]

Holds the outcome of a single task after execution and gate evaluation.

| Field | Type | Default |
|-------|------|---------|
| `task_id` | `str` | — |
| `task_name` | `str` | — |
| `executed` | `bool` | `False` |
| `quality_gate_passed` | `bool | None` | `None` |
| `tests_passed` | `bool | None` | `None` |
| `simplified` | `bool` | `False` |
| `gate_details` | `dict | None` | `None` |
| `gate_score` | `float | None` | `None` |
| `error` | `str | None` | `None` |
| `cost` | `float` | `0.0` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `severity` | `str` | Classify gate result severity. |

---

### PipelineResult

`pipeline.models` · [dataclass]

Aggregates task results, cost, and duration after a full pipeline run.

| Field | Type | Default |
|-------|------|---------|
| `spec_path` | `str` | — |
| `tasks` | `list[TaskResult]` | `field(default_factory=list)` |
| `total_cost` | `float` | `0.0` |
| `duration_ms` | `int` | `0` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Whether all tasks executed and passed gates. |
| `summary` | `str` | Human-readable summary of the pipeline run. |

---

### PipelineOrchestrator

`pipeline.orchestrator`

Loads a spec file and runs its tasks in order, enforcing quality gates between steps.

#### Constructor

| Parameter | Type | Default |
|-----------|------|---------|
| `spec_path` | `str` | — |
| `skip_gates` | `bool` | `False` |
| `skip_tests` | `bool` | `False` |
| `skip_simplify` | `bool` | `False` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run_all` | `on_task_complete: TaskCallback | None = None, skip_task_ids: set[str] | None = None` | `PipelineResult` | Execute every task in the spec, optionally skipping a set of task IDs. |
| `run_gates_for_task` | `task: DecomposedTask` | `TaskResult` | Run quality gates for a single task and return the result. |

---

### SpecState

`spec.state` · [dataclass]

Tracks which tasks have completed, which is active, and whether auto-run is enabled for a plan.

| Field | Type | Default |
|-------|------|---------|
| `plan_path` | `str` | — |
| `completed` | `list[str]` | `field(default_factory=list)` |
| `current` | `str | None` | `None` |
| `auto_run` | `bool` | `False` |
| `last_updated` | `str` | `field(default_factory=lambda: datetime.now(timezone.utc).isoformat())` |
| `schema_version` | `int` | `_CURRENT_SCHEMA_VERSION` |

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `to_dict` | — | `dict[str, object]` | Serialize the state to a plain dictionary. |

---

## Functions

### pipeline.spec\_reader

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `read_spec` | `plan_path: str` | `list[DecomposedTask]` | Read a plan file and extract XML task blocks. |

#### Raises — `read_spec`

| Exception | Message |
|-----------|---------|
| `ValueError` | `'plan_path must be a non-empty string'` |
| `FileNotFoundError` | `'Plan file not found: {...}'` |

---

### spec.presenter

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `present_tasks` | `tasks: list[DecomposedTask], state: SpecState | None = None` | `str` | Format all tasks as a human-readable markdown table. |
| `present_task_detail` | `task: DecomposedTask` | `str` | Format a single task with full details. |
| `present_task_result` | `task: DecomposedTask, gate_result: TaskResult` | `str` | Format a task's execution result with quality gate status. |
| `format_progress_bar` | `completed: int, total: int` | `str` | Visual progress indicator for task execution. |

---

### spec.runner

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_pending_tasks` | `tasks: list[DecomposedTask], state: SpecState` | `list[DecomposedTask]` | Filter tasks to only those not yet completed. |
| `execute_with_approval` | `spec_path: str, on_task_complete: object, *, skip_gates: bool = False, skip_tests: bool = False, skip_simplify: bool = False` | `PipelineResult` | Execute a spec with per-task approval. |

---

### spec.state

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `load_state` | `plan_path: str` | `SpecState | None` | Read spec-state from an HTML comment in a plan file. |
| `save_state` | `state: SpecState` | `None` | Write or update the spec-state comment in a plan file. |
| `clear_state` | `plan_path: str` | `None` | Remove the spec-state comment from a plan file. |
| `find_resumable_plans` | `plans_dir: str = '.claude/plans'` | `list[SpecState]` | Find plan files with incomplete execution state. |

---

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

## Tags

`spec`, `planning`
