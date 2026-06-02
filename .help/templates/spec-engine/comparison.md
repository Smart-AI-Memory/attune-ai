---
type: comparison
name: spec-engine-comparison
feature: spec-engine
depth: comparison
generated_at: 2026-06-02T10:56:02.727008+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Comparison: Spec Engine vs alternatives

## Context

The spec engine exposes two distinct layers for running spec-driven workflows: a **high-level interactive layer** (`spec.*`) and a **low-level pipeline layer** (`pipeline.*`). Both execute the same underlying tasks with quality gates, but they differ significantly in who controls the approval loop, what state they manage, and how much flexibility you get over execution.

## Feature comparison

| Capability | `spec` layer (`execute_with_approval`) | `pipeline` layer (`PipelineOrchestrator`) |
|---|---|---|
| **Import path** | `from spec.runner import execute_with_approval` | `from pipeline import PipelineOrchestrator` |
| **Approval loop** | Per-task, interactive — pauses after each task for user sign-off | Batch — runs all tasks unless you pass `skip_task_ids` |
| **Resume support** | Yes — `load_state` / `save_state` / `find_resumable_plans` persist `SpecState` between sessions | No built-in state persistence; caller owns resumability |
| **Progress feedback** | `format_progress_bar`, `present_task_result`, `present_tasks` render live output | Callback only — wire `on_task_complete: TaskCallback` yourself |
| **Skip gates / tests / simplify** | `skip_gates`, `skip_tests`, `skip_simplify` keyword args | Same flags on `PipelineOrchestrator.__init__` |
| **Task filtering** | `get_pending_tasks` filters against persisted `SpecState.completed` | Pass `skip_task_ids: set[str]` to `run_all` directly |
| **Result model** | `PipelineResult` (shared) — `success`, `summary`, `total_cost`, `duration_ms` | `PipelineResult` (shared) |
| **Per-task result** | `present_task_result(task, gate_result)` formats for display | `run_gates_for_task(task)` returns raw `TaskResult` |
| **State file format** | HTML comment embedded in the plan file, managed by `save_state` / `clear_state` | Not managed |
| **Typical caller** | Conversational CLI / interactive session | Automated scripts, CI pipelines |

## Key tradeoffs

### `spec` layer: structured interaction, built-in state

`execute_with_approval` is the right entry point when you want the engine to handle the approval ceremony for you. It persists a `SpecState` (tracking `completed`, `current`, and `auto_run` fields) directly in the plan file, so an interrupted run is always resumable via `find_resumable_plans`. The presenter functions — `present_tasks`, `present_task_detail`, `present_task_result`, and `format_progress_bar` — are wired in automatically, so you get human-readable output without extra plumbing.

The tradeoff: the approval loop is opinionated. You accept the per-task pause-and-confirm pattern or you set `SpecState.auto_run = True` to skip it. If you need finer-grained control over which tasks run or in what order, you are working against the layer, not with it.

### `pipeline` layer: explicit control, no ceremony

`PipelineOrchestrator` gives you the same quality-gate execution but none of the interactive scaffolding. You call `run_all` with an optional `skip_task_ids` set and an `on_task_complete` callback, and you receive a `PipelineResult`. State, display, and approval are entirely your responsibility. `run_gates_for_task` lets you evaluate a single `DecomposedTask` in isolation, which is useful for testing gate logic without running the full plan.

The tradeoff: you write more glue code. If you need to resume a run, you must track completed task IDs yourself.

## Decision guide

**Use `execute_with_approval` (`spec` layer) when:**
- You are building a conversational or CLI workflow where a human approves each task before the next one runs.
- You want automatic resume support — `find_resumable_plans` scanning `.claude/plans/` and `load_state` / `save_state` handling persistence.
- You want formatted output without writing your own presenter logic.
- You are running a multi-session workflow where `SpecState.last_updated` and `SpecState.completed` need to survive process restarts.

**Use `PipelineOrchestrator` (`pipeline` layer) when:**
- You are running in CI or an automated context with no interactive approval step.
- You need to skip specific tasks by ID at call time via `skip_task_ids`.
- You want to evaluate gate results programmatically — inspecting `TaskResult.gate_score`, `TaskResult.quality_gate_passed`, or `TaskResult.tests_passed` — without any display logic in the way.
- You are testing gate behavior for a single task with `run_gates_for_task`.

When in doubt, start with the `spec` layer. The `pipeline` layer is the better fit only when you are certain you do not need state persistence or interactive approval — and are prepared to manage both yourself.

## Source files

- `src/attune/spec/**`
- `src/attune/pipeline/**`

**Tags:** `spec`, `planning`
