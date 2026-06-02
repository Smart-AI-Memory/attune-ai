# Spec Engine architecture

Spec-driven development with approval loops.

## Purpose

The spec engine turns a plan file (an XML task list stored in `.claude/plans/`) into executed, gate-checked code. It owns two distinct concerns: running the pipeline (`pipeline.*`) and managing interactive, approval-gated execution with persistent state (`spec.*`). It is **not** responsible for authoring plan files, running the Socratic brainstorm/decompose/review phases, or displaying output in the Claude Code UI — those belong to the skill layer above it.

## Key classes

| Class | Responsibility | File |
|-------|---------------|------|
| `PipelineOrchestrator` | Reads a spec, executes each `DecomposedTask` in order, runs quality gates, and aggregates results into a `PipelineResult`. | `pipeline/orchestrator.py` |
| `PipelineResult` | Accumulates per-task outcomes, total cost, and wall-clock duration; exposes `success` and `summary` for callers that don't want to inspect individual tasks. | `pipeline/models.py` |
| `TaskResult` | Records everything that happened for one task: execution status, quality-gate score and details, test pass/fail, simplification, cost, and any error. Does three things (`quality_gate_passed`, `tests_passed`, `simplified`) — that breadth reflects the gate model, not a decomposition gap. | `pipeline/models.py` |
| `SpecState` | Persists the in-progress plan state (completed task IDs, current task, `auto_run` flag, schema version) as an HTML comment inside the plan file itself. | `spec/state.py` |

## Data flow

```
plan file (.claude/plans/*.md)
        │
        ▼
   read_spec()                         [pipeline.spec_reader]
        │  list[DecomposedTask]
        ▼
PipelineOrchestrator.run_all()         [pipeline.orchestrator]
  │                    │
  │  per task:         │  skip already-completed?
  │                    ▼
  │           get_pending_tasks()      [spec.runner / spec.state]
  │                    │
  │  for each pending task:
  │                    ▼
  │      run_gates_for_task()          [pipeline.orchestrator]
  │           │           │
  │     quality gate   tests / simplify
  │           └─────┬─────┘
  │                 ▼
  │            TaskResult
  │       (gate_score, tests_passed,
  │        simplified, cost, error)
  │                 │
  │    on_task_complete callback ──►  present_task_result()  [spec.presenter]
  │                 │
  │           save_state()            [spec.state]
  │                 │
  ▼ (all tasks done)
PipelineResult
(tasks[], total_cost, duration_ms)
        │
        ▼
  PipelineResult.summary()            surfaced to caller / UI layer
```

`execute_with_approval()` in `spec.runner` wraps this flow with per-task approval prompts; `auto_run: bool` on `SpecState` controls whether those prompts are skipped after the first approval.

## Design decisions

**State embedded in the plan file, not a sidecar.** `save_state()` and `load_state()` read and write `SpecState` as an HTML comment block inside the `.md` plan file rather than a separate JSON file. This keeps the plan and its progress co-located and means the plan file is the single artifact needed to resume a run. The trade-off is that plan files are mutable after authoring, so the state block must be versioned (`schema_version`) to survive format changes.

**`skip_gates`, `skip_tests`, `skip_simplify` as constructor flags, not subclasses.** `PipelineOrchestrator.__init__` accepts boolean keyword arguments rather than a strategy object or subclass hierarchy. This was chosen because the three concerns (`quality_gate_passed`, `tests_passed`, `simplified`) are tightly coupled inside a single task execution — separating them into composable strategies would add indirection without simplifying the gate logic. The flags are propagated transparently through `execute_with_approval()`.

**`SpecState.completed` is a list of task IDs, not a count.** `get_pending_tasks()` filters `list[DecomposedTask]` against `SpecState.completed` by ID, which means tasks can be skipped non-linearly via `skip_task_ids` in `run_all()` without corrupting resume behavior. A simple counter would not support this.

## Extension points

- **Add a new quality gate check:** Extend `PipelineOrchestrator.run_gates_for_task()`. The method returns a `TaskResult`; add fields to the `TaskResult` dataclass in `pipeline/models.py` if the new gate produces data that callers need to inspect.

- **Hook into task completion:** Pass an `on_task_complete: TaskCallback` to `PipelineOrchestrator.run_all()`. The callback receives a `TaskResult` after each task and is the intended integration point for custom reporting, logging, or approval UIs — without modifying the orchestrator.

- **Resume or skip tasks selectively:** Pass `skip_task_ids: set[str]` to `run_all()`. Task IDs come from the `DecomposedTask` objects returned by `read_spec()`.

- **Add a new presenter format:** Add a function alongside `present_tasks()`, `present_task_detail()`, `present_task_result()`, and `format_progress_bar()` in `spec/presenter.py`. Presenters are pure functions over `DecomposedTask` and `TaskResult`; they hold no state and have no coupling to the pipeline layer.

- **Find or restore interrupted runs:** Use `find_resumable_plans(plans_dir)` (default `'.claude/plans'`) to list `SpecState` objects for incomplete plans, then pass the `plan_path` to `execute_with_approval()` to resume.

For usage questions, see the `spec` reference documentation.

<!-- attune-generated: source_hash=f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337 feature=spec-engine kind=architecture generated_at=2026-06-02 -->
