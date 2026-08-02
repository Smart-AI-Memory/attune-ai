---
name: spec-engine
source: content/features/spec-engine.md
tags:
- spec
- planning
type: note
---

# Spec Ladders — goal-driven spec development with approval loops

## Overview

The spec engine powers **Spec Ladders** — goal-driven development
you approve rung by rung. It turns a plan file — an XML task list stored in
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

## Notes & tips

- **Depend only on the public API.** `pipeline` exports
  `PipelineOrchestrator`, `PipelineResult`, `TaskResult`, and
  `read_spec`. `spec` exports `SpecState`, `clear_state`,
  `find_resumable_plans`, `format_progress_bar`, `get_pending_tasks`,
  `load_state`, `present_task_detail`, `present_task_result`,
  `present_tasks`, and `save_state`. `execute_with_approval` lives in
  `attune.spec.runner`. Private helpers can change without notice.
- **Presenter functions are pure.** `present_tasks`,
  `present_task_detail`, `present_task_result`, and
  `format_progress_bar` accept `pipeline` data types, hold no state,
  and have no coupling to the pipeline layer — safe to call anywhere.
- **Prefer `skip_task_ids` over `clear_state` for re-runs.** Clearing
  state is irreversible mid-run; skipping completed tasks preserves
  your `completed` list and keeps `total_cost` / `duration_ms`
  accurate.
