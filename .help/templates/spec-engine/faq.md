---
type: faq
name: spec-engine-faq
feature: spec-engine
depth: faq
generated_at: 2026-06-02T10:56:02.714703+00:00
source_hash: f8ced22b02899aa25ff709636e659830c6ba856d70de6ddd1a9bf1cbe37a1337
status: generated
---

# Spec Engine FAQ

## What is the spec engine?

The spec engine executes a structured, spec-driven development workflow — decomposing a plan into tasks, running each task through quality gates, and tracking progress with per-task approval loops.

## When should I use it?

Use the spec engine when you have a plan file with XML task blocks (saved under `.claude/plans/`) and want to execute those tasks with quality gates and approval checkpoints. If you're still in the brainstorming or decomposition phase, you don't need the spec engine yet.

## What's the main entry point?

It depends on what you want to do:

- **Load and parse a plan file** — call `read_spec(plan_path)` to extract a list of `DecomposedTask` objects from the XML blocks in your plan.
- **Run the full pipeline programmatically** — instantiate `PipelineOrchestrator(spec_path)` and call `run_all()`. Use `skip_gates`, `skip_tests`, or `skip_simplify` to control which checks run.
- **Run with per-task approval** — call `execute_with_approval(spec_path, on_task_complete)`, which prompts for approval after each task instead of running automatically.

## How do quality gates work?

After each task executes, `run_gates_for_task()` evaluates the result and returns a `TaskResult`. The `TaskResult.quality_gate_passed` field tells you whether the task met its acceptance criteria; `TaskResult.gate_score` gives a numeric score; and `TaskResult.severity` classifies the outcome. If `quality_gate_passed` is `False`, the pipeline stops unless you're running in auto-run mode (`SpecState.auto_run = True`).

## How does the engine track progress?

Progress is stored in a `SpecState` object, which records the `plan_path`, a list of `completed` task IDs, and the `current` task ID. Call `load_state(plan_path)` to read existing state from the plan file, `save_state(state)` to persist it, and `clear_state(plan_path)` to reset. To find all plans that have unfinished work, call `find_resumable_plans()`, which defaults to searching `.claude/plans/`.

## Can I skip tasks or resume a partial run?

Yes. Pass a set of task IDs to `run_all(skip_task_ids=...)` to exclude specific tasks. To resume from where you left off, call `get_pending_tasks(tasks, state)` — it filters out any task IDs already in `SpecState.completed` — then pass those remaining tasks to your orchestration logic.

## How do I display task status to a user?

Use the presenter functions:

- `present_tasks(tasks, state)` — renders a markdown table of all tasks, annotated with completion status if you pass a `SpecState`.
- `present_task_detail(task)` — renders full details for a single task.
- `present_task_result(task, gate_result)` — renders the outcome of a task alongside its quality gate status.
- `format_progress_bar(completed, total)` — returns a visual progress indicator.

## How do I check whether the whole pipeline succeeded?

Inspect the `PipelineResult` returned by `run_all()` or `execute_with_approval()`. `PipelineResult.success` is `True` only when all tasks executed and passed their gates. `PipelineResult.summary` gives a human-readable summary. `PipelineResult.total_cost` and `PipelineResult.duration_ms` are available for observability.

## Where are the source files?

- `src/attune/pipeline/**` — orchestration, result models, and spec reader
- `src/attune/spec/**` — state management, presenter utilities, and approval runner

**Tags:** `spec`, `planning`
