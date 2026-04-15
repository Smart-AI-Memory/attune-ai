---
type: reference
feature: spec-engine
depth: reference
generated_at: 2026-04-14T15:24:54.530967+00:00
source_hash: da2776f0fd9a91d42dcf9bea5dec82a4fb9b85009623c3ae56e9db9136c29d2e
status: generated
---

# Spec Engine reference

## Classes

### SpecState [dataclass]

Execution state for a spec plan.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `plan_path` | `str` | |
| `completed` | `list[str]` | `field(default_factory=list)` |
| `current` | `str \| None` | `None` |
| `auto_run` | `bool` | `False` |
| `last_updated` | `str` | `field(default_factory=lambda : datetime.now(timezone.utc).isoformat())` |

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `to_dict()` | `dict` | Convert state to dictionary format |

### TaskResult [dataclass]

Result of executing a single pipeline task.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `task_id` | `str` | |
| `task_name` | `str` | |
| `executed` | `bool` | `False` |
| `quality_gate_passed` | `bool \| None` | `None` |
| `tests_passed` | `bool \| None` | `None` |
| `simplified` | `bool` | `False` |
| `gate_details` | `dict \| None` | `None` |
| `gate_score` | `float \| None` | `None` |
| `error` | `str \| None` | `None` |
| `cost` | `float` | `0.0` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `severity` | `str` | Classify gate result severity |

### PipelineResult [dataclass]

Aggregated result from a full pipeline run.

#### Fields

| Field | Type | Default |
|-------|------|---------|
| `spec_path` | `str` | |
| `tasks` | `list[TaskResult]` | `field(default_factory=list)` |
| `total_cost` | `float` | `0.0` |
| `duration_ms` | `int` | `0` |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `success` | `bool` | Whether all tasks executed and passed gates |
| `summary` | `str` | Human-readable summary of the pipeline run |

### PipelineOrchestrator

Executes tasks from an XML spec with quality gates.

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | `spec_path: str, *, skip_gates: bool = False, skip_tests: bool = False, skip_simplify: bool = False` | `None` | Initialize orchestrator with spec configuration |
| `run_all` | `*, on_task_complete: TaskCallback \| None = None, skip_task_ids: set[str] \| None = None` | `PipelineResult` | Execute all tasks in the pipeline |
| `run_gates_for_task` | `task: DecomposedTask` | `TaskResult` | Run quality gates for a single task |

## Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `present_tasks` | `tasks: list[DecomposedTask], state: SpecState \| None = None` | `str` | Format all tasks as a human-readable markdown table |
| `present_task_detail` | `task: DecomposedTask` | `str` | Format a single task with full details |
| `present_task_result` | `task: DecomposedTask, gate_result: TaskResult` | `str` | Format a task's execution result with quality gate status |
| `format_progress_bar` | `completed: int, total: int` | `str` | Visual progress indicator for task execution |
| `get_pending_tasks` | `tasks: list[DecomposedTask], state: SpecState` | `list[DecomposedTask]` | Filter tasks to only those not yet completed |
| `execute_with_approval` | `spec_path: str, on_task_complete: object, *, skip_gates: bool = False, skip_tests: bool = False, skip_simplify: bool = False` | `PipelineResult` | Execute a spec with per-task approval |
| `load_state` | `plan_path: str` | `SpecState \| None` | Read spec-state from an HTML comment in a plan file |
| `save_state` | `state: SpecState` | `None` | Write or update the spec-state comment in a plan file |
| `clear_state` | `plan_path: str` | `None` | Remove the spec-state comment from a plan file |
| `find_resumable_plans` | `plans_dir: str = '.claude/plans'` | `list[SpecState]` | Find plan files with incomplete execution state |
