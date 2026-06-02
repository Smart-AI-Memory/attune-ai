---
type: note
name: spec-engine-note
feature: spec-engine
depth: note
generated_at: 2026-06-02T10:56:02.723495+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Note: spec engine

## How the two packages fit together

The spec engine spans two packages: `pipeline` and `spec`. Each has a distinct role.

**`pipeline`** owns execution. `PipelineOrchestrator` reads an XML plan file, runs tasks one at a time, and evaluates quality gates after each. `read_spec()` parses a plan file into a list of `DecomposedTask` objects that the orchestrator consumes. `TaskResult` and `PipelineResult` carry the outcome data — per-task fields like `quality_gate_passed`, `gate_score`, and `cost`, and aggregate fields like `total_cost` and `duration_ms`.

**`spec`** owns state and presentation. `SpecState` tracks which task IDs are completed (`completed: list[str]`), which is currently running (`current: str | None`), and whether auto-run is active (`auto_run: bool`). State is stored as an HTML comment inside the plan file itself — `load_state()` reads it, `save_state()` writes it, and `clear_state()` removes it. `find_resumable_plans()` scans a directory (defaulting to `.claude/plans`) for plan files that have in-progress state.

The presenter functions in `spec` — `present_tasks()`, `present_task_detail()`, `present_task_result()`, and `format_progress_bar()` — accept the data types defined in `pipeline`. For example, `present_task_result()` takes a `DecomposedTask` and a `TaskResult`, and `get_pending_tasks()` filters a task list against a `SpecState`.

The entry point for interactive use is `execute_with_approval()` in `spec.runner`, which wraps `PipelineOrchestrator` with a per-task approval loop. The `PipelineOrchestrator` constructor accepts `skip_gates`, `skip_tests`, and `skip_simplify` flags; `execute_with_approval()` passes those through.

## Public API boundaries

`pipeline` exports `PipelineOrchestrator`, `PipelineResult`, `TaskResult`, and `read_spec`. `spec` exports `SpecState`, `clear_state`, `find_resumable_plans`, `format_progress_bar`, `get_pending_tasks`, `load_state`, `present_task_detail`, `present_task_result`, `present_tasks`, and `save_state`.
