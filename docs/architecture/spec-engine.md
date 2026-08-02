# Spec Engine

## Overview

The spec engine powers **Spec Ladders** (`/spec`) — goal-driven
development you approve rung by rung. It turns a plan file — an XML task list stored in
`.claude/plans/` — into executed, gate-checked code. It owns two
distinct concerns: running the pipeline (`pipeline.*`) and managing
interactive, approval-gated execution with persistent state
(`spec.*`).

It is **not** responsible for authoring plan files, running the
Socratic brainstorm / decompose / review phases, or displaying output
in the Claude Code UI — those belong to the skill layer above it.

The engine matters whenever you need to understand why a run stopped,
how to resume it, or how quality-gate outcomes map to the `severity`
and `gate_score` fields on a `TaskResult`. If you are writing code
that hooks into execution — an `on_task_complete` callback or a custom
presenter — these are the types and functions you work with directly.

## Concepts

A spec plan is an XML file under `.claude/plans/`. When you trigger
execution, the engine works through four concerns in sequence:

1. **Reading** — `read_spec(plan_path)` parses the plan file and
   returns a list of `DecomposedTask` objects.
2. **Orchestrating** — `PipelineOrchestrator` iterates those tasks,
   calls quality gates after each via `run_gates_for_task`, and
   collects results into a `PipelineResult`.
3. **Gating** — each task produces a `TaskResult` with fields like
   `quality_gate_passed`, `tests_passed`, `gate_score`, and the
   `severity` property. The orchestrator stops the run when
   `quality_gate_passed` is `False`; otherwise it consults the
   `on_task_complete` callback's returned decision (continue, redo,
   auto, or stop). `tests_passed`, `gate_score`, and `severity` are
   recorded for you to inspect — they don't drive the loop themselves.
4. **State tracking** — `SpecState` records which task IDs are
   `completed` and which is `current`. `save_state` writes this back
   into an HTML comment inside the plan file itself, so the file is
   the single source of truth. `get_pending_tasks` filters the full
   task list down to whatever hasn't finished, enabling resumption
   mid-run.

### Core data structures

| Type | What it represents |
|------|--------------------|
| `TaskResult` | The outcome of one task: whether it executed, whether `quality_gate_passed` and `tests_passed` are satisfied, the `gate_score` (float), and any `error` string. The `severity` property classifies the gate result for display. |
| `PipelineResult` | The rolled-up outcome across all tasks: `spec_path`, every `TaskResult` in `tasks`, `total_cost`, `duration_ms`, and `success` (true only when all tasks executed and passed gates). |
| `SpecState` | Durable progress record: `plan_path`, the list of `completed` task IDs, the `current` task ID, and an `auto_run` flag that controls whether the engine prompts for approval between tasks. |

### How the two packages fit together

The engine spans two packages, each with a distinct role:

- **`pipeline`** owns execution. `PipelineOrchestrator` reads an XML
  plan file, runs tasks one at a time, and evaluates quality gates
  after each. `read_spec()` parses a plan file into `DecomposedTask`
  objects. `TaskResult` and `PipelineResult` carry the outcome data.
- **`spec`** owns state and presentation. `SpecState` tracks progress;
  `load_state` / `save_state` / `clear_state` manage the embedded
  state comment; the presenter functions render engine output for
  display; and `execute_with_approval` (in `spec.runner`) wraps the
  orchestrator with a per-task approval loop.

### State lifecycle

```text
load_state(plan_path)             # returns SpecState | None
    │
    ▼
get_pending_tasks(tasks, state)   # filters out completed IDs
    │
    ▼
[execute tasks, update state.completed after each]
    │
    ├─ save_state(state)          # persists progress into the plan file
    │
    └─ clear_state(plan_path)     # removes state when the run finishes
```

`find_resumable_plans(plans_dir)` scans `.claude/plans/` (the default)
for any plan file that still carries a `SpecState` comment, giving you
a list of interrupted runs you can pick back up.

## Design & extension

### Design decisions

- **State embedded in the plan file, not a sidecar.** `save_state` and
  `load_state` read and write `SpecState` as an HTML comment block
  inside the `.md` plan file rather than a separate JSON file. This
  keeps the plan and its progress co-located — the plan file is the
  single artifact needed to resume. The trade-off is that plan files
  are mutable after authoring, so the state block is versioned
  (`schema_version`) to survive format changes.
- **`skip_gates`, `skip_tests`, `skip_simplify` as constructor flags,
  not subclasses.** The three concerns are tightly coupled inside a
  single task execution; separating them into composable strategies
  would add indirection without simplifying the gate logic. The flags
  propagate transparently through `execute_with_approval`.
- **`SpecState.completed` is a list of task IDs, not a count.**
  `get_pending_tasks` filters by ID, so tasks can be skipped
  non-linearly via `skip_task_ids` in `run_all` without corrupting
  resume behavior. A simple counter could not support this.

### Extension points

- **Add a new quality-gate check:** extend
  `PipelineOrchestrator.run_gates_for_task()`. It returns a
  `TaskResult`; add fields to the `TaskResult` dataclass in
  `pipeline/models.py` if the new gate produces data callers must
  inspect.
- **Hook into task completion:** pass an async `on_task_complete`
  callback to `run_all()`. It is awaited with `(task, result)` after
  each task and may return a decision string (`"redo"`, `"auto"`,
  `"stop"`) — the intended integration point for custom reporting,
  logging, or approval UIs, without modifying the orchestrator.
- **Resume or skip tasks selectively:** pass `skip_task_ids: set[str]`
  to `run_all()`. Task IDs come from the `DecomposedTask` objects
  returned by `read_spec()`.
- **Add a new presenter format:** add a function alongside the
  existing presenters in `spec/presenter.py`. Presenters are pure
  functions over `DecomposedTask` and `TaskResult`.
- **Find or restore interrupted runs:** use
  `find_resumable_plans(plans_dir)` to list `SpecState` objects for
  incomplete plans, then pass `plan_path` to `execute_with_approval()`
  to resume.

<!-- attune-generated: source_hash=0a9f094d0c1cb1edca272a7412ba50c3a59e4336596eb0a901aff5e6fc3b2d4b feature=spec-engine kind=architecture generated_at=2026-08-02 -->
